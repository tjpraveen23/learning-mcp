#!/usr/bin/env python3
"""
Simplified Streamlit UI for MCP Client
"""

import streamlit as st
import asyncio
import json
import aiohttp
import openai
import re
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMProvider(Enum):
    OPENAI = "openai"
    LOCAL = "local"

@dataclass
class LLMConfig:
    provider: LLMProvider
    model: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.1

class MCPClient:
    def __init__(self, llm_config: LLMConfig, server_url: str = "http://localhost:8080/mcp"):
        self.llm_config = llm_config
        self.server_url = server_url
        llm_config.api_key = os.getenv("OPENAI_API_KEY")
        
        # Initialize LLM client
        if llm_config.provider == LLMProvider.OPENAI:
            self.llm_client = openai.OpenAI(api_key=llm_config.api_key)
        elif llm_config.provider == LLMProvider.LOCAL:
            self.llm_client = openai.OpenAI(
                base_url=llm_config.base_url or "http://localhost:1234/v1",
                api_key=llm_config.api_key or "not-needed"
            )

    async def process_user_request(self, user_input: str) -> Dict[str, Any]:
        """Process user request through LLM and execute MCP call"""
        try:
            # Get LLM analysis
            llm_response = await self._analyze_request(user_input)
            
            # Parse LLM response
            tool_call = self._parse_llm_response(llm_response)
            
            if not tool_call:
                return {
                    "tool_name": "None",
                    "response": f"❌ Failed to understand request: {user_input}",
                    "missing_arguments": []
                }
            
            # Check for missing arguments
            missing_args = self._check_missing_arguments(tool_call)
            if missing_args:
                return {
                    "tool_name": tool_call.get("tool_name", "Unknown"),
                    "response": "Request not processed due to missing arguments",
                    "missing_arguments": missing_args
                }
            
            # Execute MCP request
            mcp_response = await self._call_mcp_server(tool_call)
            
            return {
                "tool_name": tool_call["tool_name"],
                "response": mcp_response.get("message", "No response message"),
                "missing_arguments": []
            }
            
        except Exception as e:
            logger.error(f"Error processing request: {e}")
            return {
                "tool_name": "Error",
                "response": f"Client error: {str(e)}",
                "missing_arguments": []
            }

    async def _analyze_request(self, user_input: str) -> str:
        """Analyze user request using LLM"""
        prompt = f"""
You are an IT Service Request Assistant. Analyze the user request and determine which tool and parameters to use.
Check for missing required arguments

AVAILABLE TOOLS:
- ToolA (AD Group Management): add_user_to_group, search_entitlements, remove_entitlement
- ToolB (Machine Access): rdp_access, temp_admin_access
- ToolC (Infrastructure): create_db_service_account, create_user_account, request_software_hardware

REQUIRED PARAMETERS:
- ToolA add_user_to_group: userid, ad_group
- ToolA search_entitlements: userid
- ToolA remove_entitlement: userid, entitlement_name
- ToolB rdp_access: machine, userid
- ToolB temp_admin_access: machine, userid
- ToolC create_db_service_account: service_name, database_name
- ToolC create_user_account: username, full_name
- ToolC request_software_hardware: item_name, requestor

User Request: {user_input}

Respond ONLY in JSON format:
{{
    "tool_name": "ToolA|ToolB|ToolC",
    "request_type": "specific_request_type",
    "parameters": {{
        "param1": "value1",
        "param2": "value2"
    }}
}}
"""

        try:
            print(f"Invoke LLM started")  # Debugging output
            self.llm_client.api_key = os.getenv("OPENAI_API_KEY")
            response = self.llm_client.chat.completions.create(
                model=self.llm_config.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.llm_config.temperature,
                max_tokens=500
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM call failed with error: {e}")
            raise

    def _parse_llm_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse LLM response to extract tool call information"""
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                tool_call = json.loads(json_str)
                
                # Validate required fields
                if all(field in tool_call for field in ["tool_name", "request_type", "parameters"]):
                    return tool_call
            
            return None
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON from LLM response: {response}")
            return None

    def _check_missing_arguments(self, tool_call: Dict[str, Any]) -> list:
        """Check for missing required arguments"""
        required_params = {
            "ToolA": {
                "add_user_to_group": ["userid", "ad_group"],
                "search_entitlements": ["userid"],
                "remove_entitlement": ["userid", "entitlement_name"]
            },
            "ToolB": {
                "rdp_access": ["machine", "userid"],
                "temp_admin_access": ["machine", "userid"]
            },
            "ToolC": {
                "create_db_service_account": ["service_name", "database_name"],
                "create_user_account": ["username", "full_name"],
                "request_software_hardware": ["item_name", "requestor"]
            }
        }
        
        tool_name = tool_call.get("tool_name")
        request_type = tool_call.get("request_type")
        parameters = tool_call.get("parameters", {})
        
        if tool_name not in required_params:
            return [f"Unknown tool: {tool_name}"]
        
        if request_type not in required_params[tool_name]:
            return [f"Unknown request type: {request_type}"]
        
        required = required_params[tool_name][request_type]
        missing = []
        
        for param in required:
            if not parameters.get(param):
                missing.append(param)
        
        return missing

    async def _call_mcp_server(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """Call MCP server via HTTP"""
        async with aiohttp.ClientSession() as session:
            async with session.post(self.server_url, json=tool_call) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"MCP server error: {error_text}")

# Configuration helpers
def get_openai_config(api_key: str, model: str = "gpt-4o-mini") -> LLMConfig:
    return LLMConfig(
        provider=LLMProvider.OPENAI,
        model=model,
        api_key=api_key
    )

def get_local_config(model: str = "gpt-3.5-turbo", base_url: str = "http://localhost:1234/v1") -> LLMConfig:
    return LLMConfig(
        provider=LLMProvider.LOCAL,
        model=model,
        base_url=base_url
    )

# Streamlit app configuration
st.set_page_config(
    page_title="IT Service Request Assistant",
    page_icon="🔧",
    layout="wide"
)

# Custom CSS for clean styling
st.markdown("""
<style>
    .result-container {
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 8px;
        border: 1px solid #ddd;
    }
    
    .tool-name {
        font-size: 1.2em;
        font-weight: bold;
        color: #2196F3;
        margin-bottom: 0.5rem;
    }
    
    .response-text {
        font-size: 1em;
        color: #333;
        margin-bottom: 0.5rem;
    }
    
    .missing-args {
        color: #f44336;
        font-weight: bold;
    }
    
    .success {
        border-left: 4px solid #4caf50;
        background-color: #f8fff8;
    }
    
    .error {
        border-left: 4px solid #f44336;
        background-color: #fff8f8;
    }
    
    .missing-params {
        border-left: 4px solid #ff9800;
        background-color: #fff9f0;
    }
</style>
""", unsafe_allow_html=True)

def run_async_function(coro):
    """Run async function in Streamlit"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(coro)

def initialize_session_state():
    """Initialize session state variables"""
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'mcp_client' not in st.session_state:
        st.session_state.mcp_client = None
    if 'llm_configured' not in st.session_state:
        st.session_state.llm_configured = False

def display_result(result: Dict[str, Any], timestamp: str):
    """Display result with clean formatting"""
    tool_name = result.get('tool_name', 'Unknown')
    response = result.get('response', 'No response')
    missing_args = result.get('missing_arguments', [])
    
    # Determine container class based on result type
    if missing_args:
        container_class = "missing-params"
    elif "error" in response.lower() or tool_name == "Error":
        container_class = "error"
    else:
        container_class = "success"
    
    st.markdown(f"""
    <div class="result-container {container_class}">
        <div class="tool-name">🔧 Tool: {tool_name}</div>
        <div class="response-text">📋 Response: {response}</div>
        {f'<div class="missing-args">❌ Missing Arguments: {", ".join(missing_args)}</div>' if missing_args else ''}
       
    </div>
    """, unsafe_allow_html=True)

def main():
    """Main Streamlit application"""
    initialize_session_state()
    
    # Header
    st.title("🔧 IT Service Request Assistant")
    st.markdown("Your intelligent assistant for IT service requests")
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # MCP Server Status Check
        server_url = "http://localhost:8080"
        
        try:
            import requests
            health_response = requests.get(f"{server_url}/health", timeout=2)
            if health_response.status_code == 200:
                st.success("✅ MCP Server Connected")
            else:
                st.error("❌ MCP Server Error")
        except:
            st.error("❌ MCP Server Not Running")
            st.info("Please start the MCP server first:\n```bash\npython mcp_server_simplified.py\n```")
        
        st.divider()
        
        # LLM Configuration
        provider = st.selectbox(
            "LLM Provider",
            options=["Local LLM", "OpenAI"],
            help="Choose your preferred LLM provider"
        )
        
        if provider == "OpenAI":
            #api_key = st.text_input("OpenAI API Key", type="password")
            api_key = os.getenv("OPENAI_API_KEY")
            model = st.selectbox("Model", ["gpt-4o-mini", "gpt-4", "gpt-3.5-turbo"])
            
            if api_key:
                try:
                    llm_config = get_openai_config(api_key, model)
                    st.session_state.mcp_client = MCPClient(llm_config)
                    st.session_state.llm_configured = True
                    st.success("✅ OpenAI Configured")
                except Exception as e:
                    st.error(f"❌ Configuration error: {str(e)}")
                    st.session_state.llm_configured = False
        
        else:  # Local LLM
            base_url = st.text_input("Base URL", value="http://localhost:1234/v1")
            model = st.text_input("Model Name", value="gpt-3.5-turbo")
            
            try:
                llm_config = get_local_config(model, base_url)
                st.session_state.mcp_client = MCPClient(llm_config)
                st.session_state.llm_configured = True
                st.success("✅ Local LLM Configured")
            except Exception as e:
                st.error(f"❌ Configuration error: {str(e)}")
                st.session_state.llm_configured = False
        
        st.divider()
        
        # Available Tools Info
        st.header("🛠️ Available Tools")
        st.markdown("""
        **ToolA - AD Management**
        - Add user to group
        - Search entitlements
        - Remove entitlement
        
        **ToolB - Machine Access**
        - RDP access
        - Temporary admin access
        
        **ToolC - Infrastructure**
        - Create service accounts
        - Create user accounts
        - Request software/hardware
        """)
        
        # Clear History
        if st.button("🗑️ Clear History"):
            st.session_state.messages = []
            st.rerun()
    
    # Main interface
    if not st.session_state.llm_configured:
        st.warning("⚠️ Please configure your LLM provider in the sidebar.")
        st.info("💡 **Quick Start:** Select 'Local LLM' if you have a local model running, or configure OpenAI with your API key.")
        return
    
    # Chat input
    st.subheader("💬 Submit Request")
    
    col1, col2 = st.columns([5, 1])
    
    with col1:
        user_input = st.text_input(
            "Enter your IT service request:",
            placeholder="e.g., Add user john.doe to IT_Support group",
            key="user_input"
        )
    
    with col2:
        send_button = st.button("Send", type="primary")
    
    # Quick Actions
    st.subheader("⚡ Quick Actions")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("👥 Add User to Group", key="quick1"):
            st.session_state.user_input = "Add user john.doe to IT_Support group"
            st.rerun()
        if st.button("🔍 Check Entitlements", key="quick2"):
            st.session_state.user_input = "What entitlements does user001 have?"
            st.rerun()
    
    with col2:
        if st.button("🖥️ RDP Access", key="quick3"):
            st.session_state.user_input = "I need RDP access to SERVER001 for user jane.smith"
            st.rerun()
        if st.button("⚡ Admin Access", key="quick4"):
            st.session_state.user_input = "I need temporary admin access to WORKSTATION001 for user bob"
            st.rerun()
    
    with col3:
        if st.button("🗃️ Service Account", key="quick5"):
            st.session_state.user_input = "Create database service account for webapp connecting to production"
            st.rerun()
        if st.button("📦 Request Software", key="quick6"):
            st.session_state.user_input = "I need Adobe Photoshop installed for john.doe"
            st.rerun()
    
    # Process request
    if send_button and user_input.strip():
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Add user message
        st.session_state.messages.append({
            "type": "user",
            "content": user_input,
            "timestamp": timestamp
        })
        
        # Process request
        with st.spinner("🤔 Processing request..."):
            try:
                result = run_async_function(
                    st.session_state.mcp_client.process_user_request(user_input)
                )
                
                # Add result to messages
                st.session_state.messages.append({
                    "type": "result",
                    "content": result,
                    "timestamp": datetime.now().strftime("%H:%M:%S")
                })
                
            except Exception as e:
                error_result = {
                    "tool_name": "Error",
                    "response": f"Processing error: {str(e)}",
                    "missing_arguments": []
                }
                st.session_state.messages.append({
                    "type": "result",
                    "content": error_result,
                    "timestamp": datetime.now().strftime("%H:%M:%S")
                })
        
        st.rerun()
    
    # Display conversation history
    if st.session_state.messages:
        st.subheader("📋 Request History")
        
        # Reverse order to show latest first
        for message in reversed(st.session_state.messages):
            if message["type"] == "user":
                st.markdown(f"""
                <div style="padding: 0.5rem; margin: 0.25rem 0; background-color: border-radius: 8px;">
                    <strong>🙋 You:</strong> {message['content']}
                </div>
                """, unsafe_allow_html=True)
            elif message["type"] == "result":
                display_result(message["content"], message["timestamp"])

if __name__ == "__main__":
    main()