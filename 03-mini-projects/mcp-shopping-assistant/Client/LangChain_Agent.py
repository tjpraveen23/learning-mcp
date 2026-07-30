# simple.py
# Simple MCP client to connect to shop_tools_server.py and use with LLM

import os
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage

# MCP imports
from mcp.client.sse import sse_client
from mcp import ClientSession

# Initialize LLM
llm = ChatOpenAI(
    api_key=api_key,    
    model="gpt-4o-mini"
)

# MCP session
session = None

async def connect_to_mcp():
    """Connect to MCP server"""
    global session
    read_stream, write_stream = await sse_client("http://localhost:8000/sse").__aenter__()
    session = ClientSession(read_stream, write_stream)
    await session.initialize()

# Create tool wrappers for your MCP tools
@tool
def get_shop_hours() -> str:
    """Get the shop's daily opening hours"""
    async def call_mcp():
        result = await session.call_tool("ShopOpeningHours", {})
        return result.result
    return asyncio.run(call_mcp())

@tool  
def get_current_time() -> str:
    """Get current date and time in IST"""
    async def call_mcp():
        result = await session.call_tool("CurrentTime", {})
        return result.result
    return asyncio.run(call_mcp())

async def main():
    """Main execution function"""
    # Connect to MCP server
    print("Connecting to MCP server...")
    await connect_to_mcp()
    print("Connected!")

    # Bind tools to LLM
    tools = [get_shop_hours, get_current_time]
    llm_with_tools = llm.bind_tools(tools)

    # Test 1: Direct tool calls
    print("\n=== Testing Tools Directly ===")
    print("Shop Hours:", get_shop_hours())
    print("Current Time:", get_current_time())

    # Test 2: LLM with tools
    print("\n=== Testing LLM with Tools ===")
    message = HumanMessage(content="What are the shop hours and what time is it now?")
    response = llm_with_tools.invoke([message])
    print("LLM Response:", response.content)

    # Test 3: Check if shop is open
    print("\n=== Shop Status Check ===")
    status_message = HumanMessage(content="Is the shop open right now? If not, when does it open next?")
    status_response = llm_with_tools.invoke([status_message])
    print("Shop Status:", status_response.content)

if __name__ == "__main__":
    asyncio.run(main())