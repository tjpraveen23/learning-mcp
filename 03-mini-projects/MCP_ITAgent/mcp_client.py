#!/usr/bin/env python3
"""
Simplified MCP Client with LLM integration
"""

import json
import asyncio
import aiohttp
import openai
import re
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
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
            response = self.llm_client.chat.completions.create(
                model=self.llm_config.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.llm_config.temperature,
                max_tokens=500
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
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

# Configuration helper
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

async def main():
    """Test the MCP client"""
    import os
    
    # Configure LLM - uncomment one of these
    # llm_config = get_openai_config(os.getenv("OPENAI_API_KEY", "your-api-key"))
    llm_config = get_local_config()  # For local LLM
    
    client = MCPClient(llm_config)
    
    # Test requests
    test_requests = [
        "Add user john.doe to IT_Support group",
        "I need RDP access to SERVER001 for user jane.smith", 
        "What entitlements does user001 have?",
        "Create a database service account for webapp connecting to production",
        "Add user to group",  # Missing parameters test
        "I need some access"   # Vague request test
    ]
    
    print("🤖 MCP Client Testing")
    print("=" * 50)
    
    for request in test_requests:
        print(f"\n📝 User Request: {request}")
        print("-" * 40)
        
        result = await client.process_user_request(request)
        
        print(f"🔧 Tool Name: {result['tool_name']}")
        print(f"📋 Response: {result['response']}")
        
        if result['missing_arguments']:
            print(f"❌ Missing Arguments: {', '.join(result['missing_arguments'])}")

if __name__ == "__main__":
    asyncio.run(main())