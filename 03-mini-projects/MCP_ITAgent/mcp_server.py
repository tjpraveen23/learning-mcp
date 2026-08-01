#!/usr/bin/env python3
"""
Simplified MCP Server with HTTP interface
"""

import json
import asyncio
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
from aiohttp import web
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RequestStatus(Enum):
    SUCCESS = "success"
    ERROR = "error"

@dataclass
class ServiceResponse:
    status: RequestStatus
    message: str
    details: Optional[Dict[str, Any]] = None

class MCPServer:
    def __init__(self):
        # Mock data storage
        self.ad_groups = {
            "IT_Support": ["user001", "user002"],
            "Finance_Team": ["user003", "user004"],
            "HR_Department": ["user005"],
            "Admin_Access": ["user001"]
        }
        
        self.user_entitlements = {
            "user001": ["IT_Support", "Admin_Access", "Email_Access"],
            "user002": ["IT_Support", "File_Share_Access"],
            "user003": ["Finance_Team", "Reports_Access"],
            "user004": ["Finance_Team", "Audit_Access"],
            "user005": ["HR_Department", "Payroll_Access"]
        }
        
        self.machine_access = {
            "SERVER001": {"rdp_enabled": True, "temp_admin": []},
            "SERVER002": {"rdp_enabled": False, "temp_admin": ["user001"]},
            "WORKSTATION001": {"rdp_enabled": True, "temp_admin": []}
        }

    async def process_request(self, tool_name: str, request_type: str, parameters: Dict[str, Any]) -> ServiceResponse:
        """Process incoming requests"""
        try:
            if tool_name == "ToolA":
                return await self._handle_tool_a(request_type, parameters)
            elif tool_name == "ToolB":
                return await self._handle_tool_b(request_type, parameters)
            elif tool_name == "ToolC":
                return await self._handle_tool_c(request_type, parameters)
            else:
                return ServiceResponse(
                    status=RequestStatus.ERROR,
                    message=f"Unknown tool: {tool_name}"
                )
        except Exception as e:
            logger.error(f"Error processing request: {e}")
            return ServiceResponse(
                status=RequestStatus.ERROR,
                message=f"Server error: {str(e)}"
            )

    async def _handle_tool_a(self, request_type: str, params: Dict[str, Any]) -> ServiceResponse:
        """Handle AD Group and Entitlement Management"""
        
        if request_type == "add_user_to_group":
            userid = params.get("userid")
            ad_group = params.get("ad_group")
            
            if not userid or not ad_group:
                return ServiceResponse(
                    status=RequestStatus.ERROR,
                    message="Missing required parameters: userid, ad_group"
                )
            
            if ad_group not in self.ad_groups:
                self.ad_groups[ad_group] = []
            
            if userid not in self.ad_groups[ad_group]:
                self.ad_groups[ad_group].append(userid)
                if userid not in self.user_entitlements:
                    self.user_entitlements[userid] = []
                if ad_group not in self.user_entitlements[userid]:
                    self.user_entitlements[userid].append(ad_group)
            
            return ServiceResponse(
                status=RequestStatus.SUCCESS,
                message=f"User {userid} added to AD group {ad_group}",
                details={"userid": userid, "ad_group": ad_group}
            )
        
        elif request_type == "search_entitlements":
            userid = params.get("userid")
            if not userid:
                return ServiceResponse(
                    status=RequestStatus.ERROR,
                    message="Missing required parameter: userid"
                )
            
            entitlements = self.user_entitlements.get(userid, [])
            return ServiceResponse(
                status=RequestStatus.SUCCESS,
                message=f"Found {len(entitlements)} entitlements for user {userid}",
                details={"userid": userid, "entitlements": entitlements}
            )
        
        elif request_type == "remove_entitlement":
            userid = params.get("userid")
            entitlement_name = params.get("entitlement_name")
            
            if not userid or not entitlement_name:
                return ServiceResponse(
                    status=RequestStatus.ERROR,
                    message="Missing required parameters: userid, entitlement_name"
                )
            
            if userid in self.user_entitlements and entitlement_name in self.user_entitlements[userid]:
                self.user_entitlements[userid].remove(entitlement_name)
                if entitlement_name in self.ad_groups and userid in self.ad_groups[entitlement_name]:
                    self.ad_groups[entitlement_name].remove(userid)
                
                return ServiceResponse(
                    status=RequestStatus.SUCCESS,
                    message=f"Removed entitlement {entitlement_name} from user {userid}",
                    details={"userid": userid, "removed_entitlement": entitlement_name}
                )
            else:
                return ServiceResponse(
                    status=RequestStatus.ERROR,
                    message=f"User {userid} does not have entitlement {entitlement_name}"
                )
        
        return ServiceResponse(
            status=RequestStatus.ERROR,
            message=f"Unknown request type for ToolA: {request_type}"
        )

    async def _handle_tool_b(self, request_type: str, params: Dict[str, Any]) -> ServiceResponse:
        """Handle Machine Access Management"""
        
        if request_type == "rdp_access":
            machine = params.get("machine")
            userid = params.get("userid")
            
            if not machine or not userid:
                return ServiceResponse(
                    status=RequestStatus.ERROR,
                    message="Missing required parameters: machine, userid"
                )
            
            if machine not in self.machine_access:
                self.machine_access[machine] = {"rdp_enabled": False, "temp_admin": []}
            
            self.machine_access[machine]["rdp_enabled"] = True
            
            return ServiceResponse(
                status=RequestStatus.SUCCESS,
                message=f"RDP access enabled for user {userid} on machine {machine}",
                details={"machine": machine, "userid": userid, "rdp_enabled": True}
            )
        
        elif request_type == "temp_admin_access":
            machine = params.get("machine")
            userid = params.get("userid")
            
            if not machine or not userid:
                return ServiceResponse(
                    status=RequestStatus.ERROR,
                    message="Missing required parameters: machine, userid"
                )
            
            if machine not in self.machine_access:
                self.machine_access[machine] = {"rdp_enabled": False, "temp_admin": []}
            
            if userid not in self.machine_access[machine]["temp_admin"]:
                self.machine_access[machine]["temp_admin"].append(userid)
            
            return ServiceResponse(
                status=RequestStatus.SUCCESS,
                message=f"Temporary admin access granted to user {userid} on machine {machine}",
                details={"machine": machine, "userid": userid}
            )
        
        return ServiceResponse(
            status=RequestStatus.ERROR,
            message=f"Unknown request type for ToolB: {request_type}"
        )

    async def _handle_tool_c(self, request_type: str, params: Dict[str, Any]) -> ServiceResponse:
        """Handle Service Account and Infrastructure Management"""
        
        if request_type == "create_db_service_account":
            service_name = params.get("service_name")
            database_name = params.get("database_name")
            
            if not service_name or not database_name:
                return ServiceResponse(
                    status=RequestStatus.ERROR,
                    message="Missing required parameters: service_name, database_name"
                )
            
            account_name = f"svc_{service_name}_{database_name}"
            return ServiceResponse(
                status=RequestStatus.SUCCESS,
                message=f"Database service account {account_name} created successfully",
                details={"account_name": account_name, "database": database_name}
            )
        
        elif request_type == "create_user_account":
            username = params.get("username")
            full_name = params.get("full_name")
            
            if not username or not full_name:
                return ServiceResponse(
                    status=RequestStatus.ERROR,
                    message="Missing required parameters: username, full_name"
                )
            
            return ServiceResponse(
                status=RequestStatus.SUCCESS,
                message=f"User account {username} created successfully",
                details={"username": username, "full_name": full_name}
            )
        
        elif request_type == "request_software_hardware":
            item_name = params.get("item_name")
            requestor = params.get("requestor")
            
            if not item_name or not requestor:
                return ServiceResponse(
                    status=RequestStatus.ERROR,
                    message="Missing required parameters: item_name, requestor"
                )
            
            request_id = f"REQ_{item_name.upper().replace(' ', '_')}"
            return ServiceResponse(
                status=RequestStatus.SUCCESS,
                message=f"Software/Hardware request {request_id} submitted successfully",
                details={"request_id": request_id, "item_name": item_name, "requestor": requestor}
            )
        
        return ServiceResponse(
            status=RequestStatus.ERROR,
            message=f"Unknown request type for ToolC: {request_type}"
        )

# HTTP Server handlers
mcp_server = MCPServer()

async def handle_request(request):
    """Handle HTTP requests to MCP server"""
    try:
        data = await request.json()
        tool_name = data.get("tool_name")
        request_type = data.get("request_type")
        parameters = data.get("parameters", {})
        
        response = await mcp_server.process_request(tool_name, request_type, parameters)
        
        return web.json_response({
            "status": response.status.value,
            "message": response.message,
            "details": response.details
        })
        
    except Exception as e:
        return web.json_response({
            "status": "error",
            "message": f"Request handling error: {str(e)}"
        }, status=500)

async def handle_health(request):
    """Health check endpoint"""
    return web.json_response({"status": "healthy", "message": "MCP server is running"})

def create_app():
    """Create web application"""
    app = web.Application()
    app.router.add_post('/mcp', handle_request)
    app.router.add_get('/health', handle_health)
    return app

async def main():
    """Start the MCP server"""
    app = create_app()
    
    # Start server
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 8080)
    await site.start()
    
    print("🚀 MCP server started on http://localhost:8080")
    print("📋 Available endpoints:")
    print("   - POST /mcp - Process MCP requests")
    print("   - GET /health - Health check")
    
    # Keep server running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("🛑 MCP server stopped")

if __name__ == "__main__":
    asyncio.run(main())