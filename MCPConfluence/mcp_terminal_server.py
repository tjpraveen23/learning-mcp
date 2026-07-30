from mcp.server.fastmcp import FastMCP
import asyncio


# Initialize FastMCP app - Local Terminal Server for MCP Confluence Tool
mcp = FastMCP(name="MCP Confluence Server")

@mcp.tool()
async def read_confluence(page_id: str) -> dict:
    """Read a confluence page by ID"""
    return {
        "status": "success",
        "message": f"Read request received for page_id = {page_id}",
        "data": "This is sample content from the confluence page."
    }


@mcp.tool()
async def write_confluence(page_title: str, content: str) -> dict:
    """Write a new confluence page with title and content"""
    return {
        "status": "success",
        "message": f"Write request received for page_title = {page_title}",
        "data": f"Page saved successfully with Content written: {content}"
    }

async def main():
    print("Starting MCP Terminal Confluence Server")
    await mcp.run_stdio_async()

if __name__ == "__main__":
    asyncio.run(main())