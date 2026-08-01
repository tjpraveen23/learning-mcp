#!/usr/bin/env python3
"""
MCP Client with configurable LLM model integration
"""

import json
import asyncio
import openai
import anthropic
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
import re

# Import the MCP Server
from mcp_server import MCPServer, ServiceResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"

@dataclass
class LLMConfig:
    provider: LLMProvider
    model: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None  # For local models
    temperature: float = 0.1

class MCPClient:
    def __init__(self, llm_config: LLMConfig, system_prompt: str):
        self.llm_config = llm_config
        self.system_prompt = system_prompt
        self.mcp_server = MCPServer()
        
        # Initialize LLM client based on provider
        if llm_config.provider == LLMProvider.OPENAI:
            self.llm_client = openai.OpenAI(api_key=llm_config.api_key)
        elif llm_config.provider == LLMProvider.ANTHROPIC:
            self.llm_client = anthropic.Anthropic(api_key=llm_config.api_key)
        elif llm_config.provider == LLMProvider.LOCAL:
            self.llm_client = openai.OpenAI(
                base_url=llm_config.base_url or "http://localhost:1234/v1",
                api_key=llm_config.api_key or "not-needed"
            )

    async def process_user_request(self, user_input: str) -> Dict[str, Any]:
        """Process user request through LLM and execute MCP tool calls"""
        try:
            # Get available tools context
            tools_context = self._get_tools_context()
            
            # Prepare the prompt for LLM
            full_prompt = f"""
{self.system_prompt}

Available Tools and Request Types:
{tools_context}

User Request: {user_input}

Analyze the user request and determine:
1. Which tool should be used (ToolA, ToolB, or ToolC)
2. What request type should be invoked
3. What input parameters are needed

Respond ONLY in this JSON format:
{{
    "tool_name": "ToolA|ToolB|ToolC",
    "request_type": "specific_request_type",
    "parameters": {{
        "param1": "value1",
        "param2": "value2"
    }},
    "reasoning": "Brief explanation of why this tool and request type were chosen"
}}
"""

            # Get LLM response
            llm_response = await self._call_llm(full_prompt)
            
            # Parse LLM response
            tool_call = self._parse_llm_response(llm_response)
            
            if not tool_call:
                return {
                    "status": "error",
                    "message": "Failed to parse LLM response",
                    "llm_response": llm_response
                }
            
            # Execute the MCP tool call
            mcp_response = await self.mcp_server.process_request(
                tool_call["tool_name"],
                tool_call["request_type"],
                tool_call["parameters"]
            )
            
            return {
                "status": "success",
                "tool_analysis": tool_call,
                "mcp_response": {
                    "status": mcp_response.status.value,
                    "message": mcp_response.message,
                    "details": mcp_response.details
                }
            }
            
        except Exception as e:
            logger.error(f"Error processing user request: {e}")
            return {
                "status": "error",
                "message": f"Client error: {str(e)}"
            }

    def _get_tools_context(self) -> str:
        """Get formatted context about available tools"""
        tools_info = self.mcp_server.get_available_tools()
        context = ""
        
        for tool_name, tool_info in tools_info.items():
            context += f"\n{tool_name}: {tool_info['description']}\n"
            context += "Request Types:\n"
            for req_type in tool_info['request_types']:
                context += f"  - {req_type}\n"
            context += "\n"
        
        return context

    async def _call_llm(self, prompt: str) -> str:
        """Call the configured LLM with the prompt"""
        try:
            if self.llm_config.provider == LLMProvider.OPENAI or self.llm_config.provider == LLMProvider.LOCAL:
                response = self.llm_client.chat.completions.create(
                    model=self.llm_config.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=self.llm_config.temperature,
                    max_tokens=1000
                )
                return response.choices[0].message.content
                
            elif self.llm_config.provider == LLMProvider.ANTHROPIC:
                response = self.llm_client.messages.create(
                    model=self.llm_config.model,
                    max_tokens=1000,
                    temperature=self.llm_config.temperature,
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.content[0].text
            
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise

    def _parse_llm_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse LLM response to extract tool call information"""
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                tool_call = json.loads(json_str)
                
                # Validate required fields
                required_fields = ["tool_name", "request_type", "parameters"]
                if all(field in tool_call for field in required_fields):
                    return tool_call
                    
            return None
            
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON from LLM response: {response}")
            return None

    async def get_conversation_response(self, user_input: str) -> str:
        """Get a formatted response for the conversation interface"""
        result = await self.process_user_request(user_input)
        
        if result["status"] == "error":
            return f"❌ Error: {result['message']}"
        
        tool_analysis = result["tool_analysis"]
        mcp_response = result["mcp_response"]
        
        response = f"🔧 **Tool Selected:** {tool_analysis['tool_name']}\n"
        response += f"📋 **Request Type:** {tool_analysis['request_type']}\n"
        response += f"⚙️ **Parameters:** {json.dumps(tool_analysis['parameters'], indent=2)}\n"
        response += f"💭 **Reasoning:** {tool_analysis['reasoning']}\n\n"
        
        if mcp_response["status"] == "success":
            response += f"✅ **Result:** {mcp_response['message']}\n"
            if mcp_response["details"]:
                response += f"📊 **Details:** {json.dumps(mcp_response['details'], indent=2)}\n"
        else:
            response += f"❌ **Error:** {mcp_response['message']}\n"
        
        return response

# Configuration examples
def get_openai_config(api_key: str, model: str = "gpt-4") -> LLMConfig:
    return LLMConfig(
        provider=LLMProvider.OPENAI,
        model=model,
        api_key=api_key,
        temperature=0.1
    )

def get_anthropic_config(api_key: str, model: str = "claude-3-sonnet-20240229") -> LLMConfig:
    return LLMConfig(
        provider=LLMProvider.ANTHROPIC,
        model=model,
        api_key=api_key,
        temperature=0.1
    )

def get_local_config(model: str = "gpt-3.5-turbo", base_url: str = "http://localhost:1234/v1") -> LLMConfig:
    return LLMConfig(
        provider=LLMProvider.LOCAL,
        model=model,
        base_url=base_url,
        temperature=0.1
    )

# Example usage
async def main():
    # Configure LLM (choose one)
    # llm_config = get_openai_config("your-api-key", "gpt-4")
    # llm_config = get_anthropic_config("your-api-key", "claude-3-sonnet-20240229")
    llm_config = get_local_config()  # For local LLM
    
    # System prompt (will be defined in separate artifact)
    system_prompt = """
You are an IT Service Request Assistant. Your role is to analyze user requests and determine which tool and request type should be used to fulfill their needs.

You must be precise and only use the available tools and request types. Do not make assumptions about parameters that are not clearly specified in the user request.

Always respond in the exact JSON format requested with no additional text.
"""
    
    client = MCPClient(llm_config, system_prompt)
    
    # Test requests
    test_requests = [
        "Add user john.doe to the IT_Support group",
        "I need RDP access to SERVER001 for user jane.smith",
        "Create a database service account for our new web application connecting to the production database",
        "What entitlements does user001 have?",
        "I need temporary admin access to WORKSTATION001 for user bob.wilson"
    ]
    
    for request in test_requests:
        print(f"\n{'='*60}")
        print(f"User Request: {request}")
        print(f"{'='*60}")
        
        response = await client.get_conversation_response(request)
        print(response)

if __name__ == "__main__":
    asyncio.run(main())