#!/usr/bin/env python3
"""
Streamlit UI for MCP Client - IT Service Request Chat Interface
"""

import streamlit as st
import asyncio
import json
from datetime import datetime
from typing import List, Dict, Any
import sys
import os

# Add the current directory to path to import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from mcp_client import MCPClient, LLMConfig, LLMProvider, get_openai_config, get_anthropic_config, get_local_config

# Page configuration
st.set_page_config(
    page_title="IT Service Request Assistant",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1rem;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    
    .chat-message {
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 10px;
        border-left: 4px solid;
    }
    
    .user-message {
        background-color: #e3f2fd;
        border-left-color: #2196f3;
    }
    
    .assistant-message {
        background-color: #f3e5f5;
        border-left-color: #9c27b0;
    }
    
    .error-message {
        background-color: #ffebee;
        border-left-color: #f44336;
    }
    
    .success-message {
        background-color: #e8f5e8;
        border-left-color: #4caf50;
    }
    
    .stTextInput > div > div > input {
        border-radius: 20px;
    }
    
    .stButton > button {
        border-radius: 20px;
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# System prompt for the MCP client
SYSTEM_PROMPT = """
You are an IT Service Request Assistant that helps users with various IT-related tasks. Your role is to analyze user requests and determine the appropriate tool and request type to fulfill their needs.

AVAILABLE TOOLS:
1. ToolA - AD Group and Entitlement Management
   - add_user_to_group: Add a user to an Active Directory group
   - search_entitlements: Search for a user's current entitlements/permissions
   - remove_entitlement: Remove a specific entitlement from a user

2. ToolB - Machine Access Management
   - rdp_access: Grant or configure RDP access to a machine
   - temp_admin_access: Grant temporary administrator access to a machine
   - external_email_access: Configure external email access for a user on a machine

3. ToolC - Service Account and Infrastructure Management
   - create_db_service_account: Create database service accounts for applications
   - create_active_directory: Create new Active Directory organizational units
   - create_project_request: Create new project requests with resource allocation
   - create_user_account: Create new user accounts in the system
   - request_software_hardware: Request software or hardware installations

INSTRUCTIONS:
- Analyze the user's request carefully and identify the most appropriate tool and request type
- Extract the necessary parameters from the user's request
- If parameters are missing or unclear, make reasonable assumptions based on context
- Always provide a brief reasoning for your tool selection
- Respond ONLY in JSON format with: tool_name, request_type, parameters, and reasoning
- Be precise and do not hallucinate information not provided by the user
- If a request cannot be fulfilled with available tools, explain why in the reasoning

Example user requests and their analysis:
- "Add user john.doe to IT_Support group" → ToolA, add_user_to_group
- "I need RDP access to SERVER001" → ToolB, rdp_access  
- "Create a service account for our web app database" → ToolC, create_db_service_account
- "What permissions does user123 have?" → ToolA, search_entitlements
- "Request installation of Adobe Photoshop" → ToolC, request_software_hardware
"""

def initialize_session_state():
    """Initialize session state variables"""
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'mcp_client' not in st.session_state:
        st.session_state.mcp_client = None
    if 'llm_configured' not in st.session_state:
        st.session_state.llm_configured = False

def create_mcp_client(llm_config: LLMConfig) -> MCPClient:
    """Create MCP client with the given configuration"""
    return MCPClient(llm_config, SYSTEM_PROMPT)

def display_message(message: Dict[str, Any]):
    """Display a chat message with appropriate styling"""
    role = message["role"]
    content = message["content"]
    timestamp = message.get("timestamp", "")
    
    if role == "user":
        st.markdown(f"""
        <div class="chat-message user-message">
            <strong>🙋 You</strong> <small>{timestamp}</small><br>
            {content}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="chat-message assistant-message">
            <strong>🤖 IT Assistant</strong> <small>{timestamp}</small><br>
            {content}
        </div>
        """, unsafe_allow_html=True)

def run_async_function(coro):
    """Run async function in Streamlit"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(coro)

def main():
    """Main Streamlit application"""
    initialize_session_state()
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🔧 IT Service Request Assistant</h1>
        <p>Your intelligent assistant for IT service requests, access management, and infrastructure operations</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar for LLM Configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # LLM Provider Selection
        provider = st.selectbox(
            "Select LLM Provider",
            options=["Local LLM", "OpenAI", "Anthropic"],
            help="Choose your preferred LLM provider"
        )
        
        # Model Configuration
        if provider == "OpenAI":
            api_key = st.text_input("OpenAI API Key", type="password", help="Enter your OpenAI API key")
            model = st.selectbox("Model", ["gpt-4", "gpt-3.5-turbo", "gpt-4-turbo-preview"])
            
            if api_key:
                try:
                    llm_config = get_openai_config(api_key, model)
                    st.session_state.mcp_client = create_mcp_client(llm_config)
                    st.session_state.llm_configured = True
                    st.success("✅ OpenAI configured successfully!")
                except Exception as e:
                    st.error(f"❌ Configuration error: {str(e)}")
                    st.session_state.llm_configured = False
        
        elif provider == "Anthropic":
            api_key = st.text_input("Anthropic API Key", type="password", help="Enter your Anthropic API key")
            model = st.selectbox("Model", ["claude-3-sonnet-20240229", "claude-3-haiku-20240307", "claude-3-opus-20240229"])
            
            if api_key:
                try:
                    llm_config = get_anthropic_config(api_key, model)
                    st.session_state.mcp_client = create_mcp_client(llm_config)
                    st.session_state.llm_configured = True
                    st.success("✅ Anthropic configured successfully!")
                except Exception as e:
                    st.error(f"❌ Configuration error: {str(e)}")
                    st.session_state.llm_configured = False
        
        else:  # Local LLM
            base_url = st.text_input("Base URL", value="http://localhost:1234/v1", help="Local LLM server URL")
            model = st.text_input("Model Name", value="gpt-3.5-turbo", help="Model name for local LLM")
            
            try:
                llm_config = get_local_config(model, base_url)
                st.session_state.mcp_client = create_mcp_client(llm_config)
                st.session_state.llm_configured = True
                st.success("✅ Local LLM configured!")
            except Exception as e:
                st.error(f"❌ Configuration error: {str(e)}")
                st.session_state.llm_configured = False
        
        st.divider()
        
        # Available Tools Information
        st.header("🛠️ Available Tools")
        
        with st.expander("ToolA - AD Group Management"):
            st.markdown("""
            **Capabilities:**
            - Add users to AD groups
            - Search user entitlements
            - Remove user entitlements
            
            **Example requests:**
            - "Add john.doe to IT_Support group"
            - "What entitlements does user123 have?"
            - "Remove Finance_Team access from jane.smith"
            """)
        
        with st.expander("ToolB - Machine Access"):
            st.markdown("""
            **Capabilities:**
            - Grant RDP access
            - Temporary admin access
            - External email access
            
            **Example requests:**
            - "Give RDP access to SERVER001 for user bob"
            - "I need temp admin on WORKSTATION001"
            - "Enable external email for sarah on her machine"
            """)
        
        with st.expander("ToolC - Infrastructure & Accounts"):
            st.markdown("""
            **Capabilities:**
            - Create database service accounts
            - Create Active Directory OUs
            - Create project requests
            - Create user accounts
            - Request software/hardware
            
            **Example requests:**
            - "Create DB service account for webapp"
            - "I need Adobe Photoshop installed"
            - "Create user account for new employee"
            """)
        
        # Clear Chat Button
        if st.button("🗑️ Clear Chat History"):
            st.session_state.messages = []
            st.rerun()
    
    # Main Chat Interface
    if not st.session_state.llm_configured:
        st.warning("⚠️ Please configure your LLM provider in the sidebar to start using the assistant.")
        st.info("💡 **Quick Start:** Select 'Local LLM' if you have a local model running, or configure OpenAI/Anthropic with your API key.")
        return
    
    # Display chat messages
    st.subheader("💬 Chat")
    
    # Create a container for messages
    messages_container = st.container()
    
    with messages_container:
        for message in st.session_state.messages:
            display_message(message)
    
    # Chat input
    with st.container():
        col1, col2 = st.columns([6, 1])
        
        with col1:
            user_input = st.text_input(
                "Enter your IT service request...",
                placeholder="e.g., Add user john.doe to IT_Support group",
                key="user_input"
            )
        
        with col2:
            send_button = st.button("Send 📤", key="send_button")
    
    # Process user input
    if send_button and user_input.strip():
        # Add user message to chat
        timestamp = datetime.now().strftime("%H:%M:%S")
        user_message = {
            "role": "user",
            "content": user_input,
            "timestamp": timestamp
        }
        st.session_state.messages.append(user_message)
        
        # Show thinking indicator
        with st.spinner("🤔 Analyzing your request..."):
            try:
                # Process the request
                response = run_async_function(
                    st.session_state.mcp_client.get_conversation_response(user_input)
                )
                
                # Add assistant response to chat
                assistant_message = {
                    "role": "assistant", 
                    "content": response,
                    "timestamp": datetime.now().strftime("%H:%M:%S")
                }
                st.session_state.messages.append(assistant_message)
                
            except Exception as e:
                error_message = {
                    "role": "assistant",
                    "content": f"❌ **Error:** Sorry, I encountered an error processing your request: {str(e)}",
                    "timestamp": datetime.now().strftime("%H:%M:%S")
                }
                st.session_state.messages.append(error_message)
        
        # Rerun to show new messages
        st.rerun()
    
    # Quick Actions
    st.subheader("⚡ Quick Actions")
    quick_actions_col1, quick_actions_col2, quick_actions_col3 = st.columns(3)
    
    with quick_actions_col1:
        if st.button("👥 Add User to Group"):
            st.session_state.user_input = "Add user [username] to [groupname] group"
            st.rerun()
        
        if st.button("🔍 Check User Entitlements"):
            st.session_state.user_input = "What entitlements does [username] have?"
            st.rerun()
    
    with quick_actions_col2:
        if st.button("🖥️ Request RDP Access"):
            st.session_state.user_input = "I need RDP access to [machine] for user [username]"
            st.rerun()
        
        if st.button("⚡ Temporary Admin Access"):
            st.session_state.user_input = "I need temporary admin access to [machine] for user [username]"
            st.rerun()
    
    with quick_actions_col3:
        if st.button("🗃️ Create Service Account"):
            st.session_state.user_input = "Create a database service account for [service_name] connecting to [database_name]"
            st.rerun()
        
        if st.button("📦 Request Software"):
            st.session_state.user_input = "I need [software_name] installed for user [username]"
            st.rerun()
    
    # Footer
    st.divider()
    st.markdown("""
    <div style="text-align: center; color: #666; padding: 1rem;">
        <small>
        🔧 IT Service Request Assistant | Powered by MCP Protocol<br>
        Built with Streamlit • Supports OpenAI, Anthropic, and Local LLMs
        </small>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()