#!/usr/bin/env python3
"""
Simple MCP Server with IT Service Request Tools
"""

import json
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RequestStatus(Enum):
    SUCCESS = "success"
    ERROR = "error"
    PENDING = "pending"

@dataclass
class ServiceResponse:
    status: RequestStatus
    message: str
    details: Optional[Dict[str, Any]] = None

class MCPServer:
    def __init__(self):
        self.tools = {
            "ToolA": self._handle_tool_a,
            "ToolB": self._handle_tool_b,
            "ToolC": self._handle_tool_c
        }
        
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
        """Process incoming MCP requests"""
        try:
            if tool_name not in self.tools:
                return ServiceResponse(
                    status=RequestStatus.ERROR,
                    message=f"Unknown tool: {tool_name}"
                )
            
            handler = self.tools[tool_name]
            return await handler(request_type, parameters)
            
        except Exception as e:
            logger.error(f"Error processing request: {e}")
            return ServiceResponse(
                status=RequestStatus.ERROR,
                message=f"Server error: {str(e)}"
            )

    async def _handle_tool_a(self, request_type: str, params: Dict[str, Any]) -> ServiceResponse:
        """Handle AD Group and Entitlement Management requests"""
        
        if request_type == "add_user_to_group":
            userid = params.get("userid")
            ad_group = params.get("ad_group")
            
            if not userid or not ad_group:
                return ServiceResponse(
                    status=RequestStatus.ERROR,
                    message="Missing required parameters: userid and ad_group"
                )
            
            if ad_group not in self.ad_groups:
                self.ad_groups[ad_group] = []
            
            if userid not in self.ad_groups[ad_group]:
                self.ad_groups[ad_group].append(userid)
                
                # Update user entitlements
                if userid not in self.user_entitlements:
                    self.user_entitlements[userid] = []
                if ad_group not in self.user_entitlements[userid]:
                    self.user_entitlements[userid].append(ad_group)
                
                return ServiceResponse(
                    status=RequestStatus.SUCCESS,
                    message=f"User {userid} added to AD group {ad_group}",
                    details={"userid": userid, "ad_group": ad_group}
                )
            else:
                return ServiceResponse(
                    status=RequestStatus.SUCCESS,
                    message=f"User {userid} is already in AD group {ad_group}"
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
                    message="Missing required parameters: userid and entitlement_name"
                )
            
            if userid in self.user_entitlements and entitlement_name in self.user_entitlements[userid]:
                self.user_entitlements[userid].remove(entitlement_name)
                
                # Also remove from AD group
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
        
        else:
            return ServiceResponse(
                status=RequestStatus.ERROR,
                message=f"Unknown request type for ToolA: {request_type}"
            )

    async def _handle_tool_b(self, request_type: str, params: Dict[str, Any]) -> ServiceResponse:
        """Handle Machine Access requests"""
        
        machine = params.get("machine")
        if not machine:
            return ServiceResponse(
                status=RequestStatus.ERROR,
                message="Missing required parameter: machine"
            )
        
        if request_type == "rdp_access":
            userid = params.get("userid")
            enable = params.get("enable", True)
            
            if not userid:
                return ServiceResponse(
                    status=RequestStatus.ERROR,
                    message="Missing required parameter: userid"
                )
            
            if machine not in self.machine_access:
                self.machine_access[machine] = {"rdp_enabled": False, "temp_admin": []}
            
            self.machine_access[machine]["rdp_enabled"] = enable
            
            action = "enabled" if enable else "disabled"
            return ServiceResponse(
                status=RequestStatus.SUCCESS,
                message=f"RDP access {action} for user {userid} on machine {machine}",
                details={"machine": machine, "userid": userid, "rdp_enabled": enable}
            )
        
        elif request_type == "temp_admin_access":
            userid = params.get("userid")
            duration = params.get("duration", "4 hours")  # default duration
            
            if not userid:
                return ServiceResponse(
                    status=RequestStatus.ERROR,
                    message="Missing required parameter: userid"
                )
            
            if machine not in self.machine_access:
                self.machine_access[machine] = {"rdp_enabled": False, "temp_admin": []}
            
            if userid not in self.machine_access[machine]["temp_admin"]:
                self.machine_access[machine]["temp_admin"].append(userid)
            
            return ServiceResponse(
                status=RequestStatus.SUCCESS,
                message=f"Temporary admin access granted to user {userid} on machine {machine} for {duration}",
                details={"machine": machine, "userid": userid, "duration": duration}
            )
        
        elif request_type == "external_email_access":
            userid = params.get("userid")
            domains = params.get("domains", [])
            
            if not userid:
                return ServiceResponse(
                    status=RequestStatus.ERROR,
                    message="Missing required parameter: userid"
                )
            
            return ServiceResponse(
                status=RequestStatus.SUCCESS,
                message=f"External email access configured for user {userid} on machine {machine}",
                details={"machine": machine, "userid": userid, "allowed_domains": domains}
            )
        
        else:
            return ServiceResponse(
                status=RequestStatus.ERROR,
                message=f"Unknown request type for ToolB: {request_type}"
            )

    async def _handle_tool_c(self, request_type: str, params: Dict[str, Any]) -> ServiceResponse:
        """Handle Service Account and Infrastructure requests"""
        
        if request_type == "create_db_service_account":
            service_name = params.get("service_name")
            database_name = params.get("database_name")
            permissions = params.get("permissions", ["READ"])
            
            if not service_name or not database_name:
                return ServiceResponse(
                    status=RequestStatus.ERROR,
                    message="Missing required parameters: service_name and database_name"
                )
            
            account_name = f"svc_{service_name}_{database_name}"
            return ServiceResponse(
                status=RequestStatus.SUCCESS,
                message=f"Database service account {account_name} created successfully",
                details={
                    "account_name": account_name,
                    "database": database_name,
                    "permissions": permissions
                }
            )
        
        elif request_type == "create_active_directory":
            ou_name = params.get("ou_name")
            description = params.get("description", "")
            parent_ou = params.get("parent_ou", "")
            
            if not ou_name:
                return ServiceResponse(
                    status=RequestStatus.ERROR,
                    message="Missing required parameter: ou_name"
                )
            
            return ServiceResponse(
                status=RequestStatus.SUCCESS,
                message=f"Active Directory OU {ou_name} created successfully",
                details={
                    "ou_name": ou_name,
                    "description": description,
                    "parent_ou": parent_ou
                }
            )
        
        elif request_type == "create_project_request":
            project_name = params.get("project_name")
            requestor = params.get("requestor")
            resources = params.get("resources", [])
            timeline = params.get("timeline", "30 days")
            
            if not project_name or not requestor:
                return ServiceResponse(
                    status=RequestStatus.ERROR,
                    message="Missing required parameters: project_name and requestor"
                )
            
            project_id = f"PRJ_{project_name.upper().replace(' ', '_')}"
            return ServiceResponse(
                status=RequestStatus.SUCCESS,
                message=f"Project request {project_id} created successfully",
                details={
                    "project_id": project_id,
                    "project_name": project_name,
                    "requestor": requestor,
                    "resources": resources,
                    "timeline": timeline
                }
            )
        
        elif request_type == "create_user_account":
            username = params.get("username")
            full_name = params.get("full_name")
            department = params.get("department")
            manager = params.get("manager")
            
            if not username or not full_name:
                return ServiceResponse(
                    status=RequestStatus.ERROR,
                    message="Missing required parameters: username and full_name"
                )
            
            return ServiceResponse(
                status=RequestStatus.SUCCESS,
                message=f"User account {username} created successfully",
                details={
                    "username": username,
                    "full_name": full_name,
                    "department": department,
                    "manager": manager
                }
            )
        
        elif request_type == "request_software_hardware":
            item_type = params.get("item_type")  # "software" or "hardware"
            item_name = params.get("item_name")
            requestor = params.get("requestor")
            justification = params.get("justification", "")
            
            if not item_type or not item_name or not requestor:
                return ServiceResponse(
                    status=RequestStatus.ERROR,
                    message="Missing required parameters: item_type, item_name, and requestor"
                )
            
            request_id = f"REQ_{item_type.upper()}_{len(item_name)}"
            return ServiceResponse(
                status=RequestStatus.SUCCESS,
                message=f"{item_type.capitalize()} request {request_id} submitted successfully",
                details={
                    "request_id": request_id,
                    "item_type": item_type,
                    "item_name": item_name,
                    "requestor": requestor,
                    "justification": justification
                }
            )
        
        else:
            return ServiceResponse(
                status=RequestStatus.ERROR,
                message=f"Unknown request type for ToolC: {request_type}"
            )

    def get_available_tools(self) -> Dict[str, Dict[str, List[str]]]:
        """Return available tools and their request types"""
        return {
            "ToolA": {
                "description": "AD Group and Entitlement Management",
                "request_types": [
                    "add_user_to_group",
                    "search_entitlements", 
                    "remove_entitlement"
                ]
            },
            "ToolB": {
                "description": "Machine Access Management",
                "request_types": [
                    "rdp_access",
                    "temp_admin_access",
                    "external_email_access"
                ]
            },
            "ToolC": {
                "description": "Service Account and Infrastructure Management",
                "request_types": [
                    "create_db_service_account",
                    "create_active_directory",
                    "create_project_request",
                    "create_user_account",
                    "request_software_hardware"
                ]
            }
        }

# Example usage
async def main():
    server = MCPServer()
    
    # Test ToolA
    response = await server.process_request(
        "ToolA", 
        "add_user_to_group", 
        {"userid": "user006", "ad_group": "IT_Support"}
    )
    print(f"ToolA Response: {response}")
    
    # Test ToolB
    response = await server.process_request(
        "ToolB",
        "rdp_access",
        {"machine": "SERVER003", "userid": "user006", "enable": True}
    )
    print(f"ToolB Response: {response}")
    
    # Test ToolC
    response = await server.process_request(
        "ToolC",
        "create_db_service_account",
        {"service_name": "webapp", "database_name": "production", "permissions": ["READ", "WRITE"]}
    )
    print(f"ToolC Response: {response}")

if __name__ == "__main__":
    asyncio.run(main())