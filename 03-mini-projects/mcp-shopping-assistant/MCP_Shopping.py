# shop_tools_server.py
import datetime
import sys
import pytz
from mcp.server.fastmcp import FastMCP

#create MCP server
mcp = FastMCP("shop_tools_server")

#Map the tools
@mcp.tool()
def ShopOpeningHours() -> str:
    """Provides the daily opening hours of the shop."""
    schedule = (
        "Monday: 10:00am to 8:00pm\n"
        "Tuesday: 10:00am to 8:00pm\n"
        "Wednesday: 10:00am to 8:00pm\n"
        "Thursday: 10:00am to 8:00pm\n"
        "Friday: 10:00am to 8:00pm\n"
        "Saturday: 10:00am to 02:30pm\n"
        "Sunday: 10:00am to 6:00pm"
    )
    return schedule

#Map the tools
@mcp.tool()
def CurrentTime() -> str:
    """Provides the current date and time in IST."""
    ist = pytz.timezone("Asia/Kolkata")
    return datetime.datetime.now(ist).strftime("%Y-%m-%d %H:%M:%S")

if __name__ == "__main__":
    print("✅ MCP server is running... Waiting for requests.", file=sys.stderr)
    mcp.run()
