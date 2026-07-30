from mcp.server.fastmcp import FastMCP
import uvicorn


# Initialize FastMCP app - HTTP Server with MCP Protocol
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

if __name__ == "__main__":
    print("Starting MCP HTTP Confluence Server on http://127.0.0.1:8000")
    
    # Run with SSE transport for HTTP
    uvicorn.run(
        mcp.sse_app(),
        host="127.0.0.1",
        port=8000
    )