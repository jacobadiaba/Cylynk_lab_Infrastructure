"""
Common utilities for CyberLab Orchestrator Lambda functions.
"""

import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional

import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
PROJECT_NAME = os.environ.get("PROJECT_NAME", "cyberlab")
ENVIRONMENT = os.environ.get("ENVIRONMENT", "dev")
AWS_REGION = os.environ.get("AWS_REGION_NAME", "us-east-1")
DEFAULT_PLAN_LIMITS = {
    "freemium": 300,  # 5 hours
    "starter": 900,   # 15 hours
    "pro": -1,        # unlimited
}

# Session statuses
class SessionStatus:
    PENDING = "pending"
    PROVISIONING = "provisioning"
    READY = "ready"
    ACTIVE = "active"
    TERMINATING = "terminating"
    TERMINATED = "terminated"
    ERROR = "error"

# Instance pool statuses
class InstanceStatus:
    AVAILABLE = "available"
    ASSIGNED = "assigned"
    STARTING = "starting"
    STOPPING = "stopping"
    UNHEALTHY = "unhealthy"


# Plan tiers with instance type mapping
class PlanTier:
    FREEMIUM = "freemium"
    STARTER = "starter"
    PRO = "pro"
    
    # Instance types for each tier (cost-optimized)
    INSTANCE_TYPES = {
        "freemium": "t3.micro",   # 2 vCPU, 1GB - basic labs
        "starter": "t3.small",    # 2 vCPU, 2GB - standard labs
        "pro": "t3.medium",       # 2 vCPU, 4GB - advanced labs
    }
    
    @classmethod
    def get_instance_type(cls, plan: str) -> str:
        """Get the instance type for a plan tier."""
        return cls.INSTANCE_TYPES.get(plan, cls.INSTANCE_TYPES["freemium"])


def generate_session_id() -> str:
    """Generate a unique session ID."""
    return f"sess-{uuid.uuid4().hex[:12]}"


def get_current_timestamp() -> int:
    """Get current Unix timestamp."""
    return int(time.time())


def get_iso_timestamp() -> str:
    """Get current ISO 8601 timestamp."""
    return datetime.now(timezone.utc).isoformat()


def calculate_expiry(ttl_hours: int) -> int:
    """Calculate expiry timestamp for DynamoDB TTL."""
    return get_current_timestamp() + (ttl_hours * 3600)


class DecimalEncoder(json.JSONEncoder):
    """JSON encoder that handles Decimal types from DynamoDB."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super().default(obj)


def json_response(status_code: int, body: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Create a standardized API Gateway response."""
    default_headers = {
        "Content-Type": "application/json",
        "X-Request-Id": str(uuid.uuid4()),
    }
    if headers:
        default_headers.update(headers)
    
    return {
        "statusCode": status_code,
        "headers": default_headers,
        "body": json.dumps(body, cls=DecimalEncoder),
    }


def success_response(data: Dict[str, Any], message: str = "Success") -> Dict[str, Any]:
    """Create a success response."""
    return json_response(200, {
        "success": True,
        "message": message,
        "data": data,
        "timestamp": get_iso_timestamp(),
    })


def error_response(status_code: int, error: str, details: Optional[str] = None) -> Dict[str, Any]:
    """Create an error response."""
    body = {
        "success": False,
        "error": error,
        "timestamp": get_iso_timestamp(),
    }
    if details:
        body["details"] = details
    return json_response(status_code, body)


def parse_request_body(event: Dict[str, Any]) -> Dict[str, Any]:
    """Parse request body from API Gateway event."""
    body = event.get("body", "{}")
    if not body:
        return {}
    
    if isinstance(body, str):
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return {}
    return body


def get_path_parameter(event: Dict[str, Any], param_name: str) -> Optional[str]:
    """Get a path parameter from API Gateway event."""
    path_params = event.get("pathParameters") or {}
    return path_params.get(param_name)


def get_query_parameter(event: Dict[str, Any], param_name: str, default: Optional[str] = None) -> Optional[str]:
    """Get a query parameter from API Gateway event."""
    query_params = event.get("queryStringParameters") or {}
    return query_params.get(param_name, default)


class DynamoDBClient:
    """Helper class for DynamoDB operations."""
    
    def __init__(self, table_name: str):
        self.table_name = table_name
        self.dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
        self.table = self.dynamodb.Table(table_name)
    
    def get_item(self, key: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get an item from DynamoDB."""
        try:
            response = self.table.get_item(Key=key)
            return response.get("Item")
        except ClientError as e:
            logger.error(f"DynamoDB get_item error: {e}")
            return None
    
    def put_item(self, item: Dict[str, Any]) -> bool:
        """Put an item into DynamoDB."""
        try:
            self.table.put_item(Item=item)
            return True
        except ClientError as e:
            logger.error(f"DynamoDB put_item error: {e}")
            return False
    
    def update_item(self, key: Dict[str, Any], updates: Dict[str, Any]) -> bool:
        """Update an item in DynamoDB."""
        try:
            update_expression = "SET " + ", ".join(f"#{k} = :{k}" for k in updates.keys())
            expression_names = {f"#{k}": k for k in updates.keys()}
            expression_values = {f":{k}": v for k, v in updates.items()}
            
            self.table.update_item(
                Key=key,
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_names,
                ExpressionAttributeValues=expression_values,
            )
            return True
        except ClientError as e:
            logger.error(f"DynamoDB update_item error: {e}")
            return False
    
    def conditional_update(
        self, 
        key: Dict[str, Any], 
        updates: Dict[str, Any], 
        condition_expression: str,
        expression_attribute_names: Optional[Dict[str, str]] = None,
        expression_attribute_values: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update an item in DynamoDB with a condition (for pessimistic locking).
        Returns True if update succeeded, False if condition failed or error occurred.
        """
        try:
            update_expression = "SET " + ", ".join(f"#{k} = :{k}" for k in updates.keys())
            
            # Merge expression attribute names
            expr_names = {f"#{k}": k for k in updates.keys()}
            if expression_attribute_names:
                expr_names.update(expression_attribute_names)
            
            # Merge expression attribute values
            expr_values = {f":{k}": v for k, v in updates.items()}
            if expression_attribute_values:
                expr_values.update(expression_attribute_values)
            
            self.table.update_item(
                Key=key,
                UpdateExpression=update_expression,
                ConditionExpression=condition_expression,
                ExpressionAttributeNames=expr_names,
                ExpressionAttributeValues=expr_values,
            )
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                # Condition failed - this is expected in race conditions
                logger.debug(f"Conditional update failed for key {key}: condition not met")
                return False
            else:
                logger.error(f"DynamoDB conditional_update error: {e}")
                return False
    
    def delete_item(self, key: Dict[str, Any]) -> bool:
        """Delete an item from DynamoDB."""
        try:
            self.table.delete_item(Key=key)
            return True
        except ClientError as e:
            logger.error(f"DynamoDB delete_item error: {e}")
            return False
    
    def query_by_index(self, index_name: str, key_name: str, key_value: str) -> list:
        """Query items using a GSI."""
        try:
            response = self.table.query(
                IndexName=index_name,
                KeyConditionExpression=Key(key_name).eq(key_value),
            )
            return response.get("Items", [])
        except ClientError as e:
            logger.error(f"DynamoDB query error: {e}")
            return []
    
    def query_user_sessions(self, user_id: str, limit: int = 50, status_filter: Optional[str] = None) -> list:
        """
        Query all sessions for a specific user using the StudentIndex GSI.
        
        Args:
            user_id: The student/user ID to query sessions for
            limit: Maximum number of sessions to return
            status_filter: Optional status to filter by (e.g., 'terminated', 'ready')
        
        Returns:
            List of session items from DynamoDB
        """
        try:
            query_kwargs = {
                "IndexName": "StudentIndex",
                "KeyConditionExpression": Key("student_id").eq(user_id),
                "Limit": limit,
                "ScanIndexForward": False,  # Most recent first
            }
            
            # Add status filter if provided
            if status_filter:
                query_kwargs["FilterExpression"] = Attr("status").eq(status_filter)
            
            response = self.table.query(**query_kwargs)
            return response.get("Items", [])
        except ClientError as e:
            logger.error(f"DynamoDB query_user_sessions error: {e}")
            return []


class UsageTracker:
    """Tracks per-user monthly usage for AttackBox sessions."""

    def __init__(self, table_name: str):
        self.table_name = table_name
        self.dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
        self.table = self.dynamodb.Table(table_name)

    @staticmethod
    def current_month() -> str:
        """Return current month as YYYY-MM in UTC."""
        return datetime.now(timezone.utc).strftime("%Y-%m")

    def get_usage_minutes(self, user_id: str, usage_month: str) -> int:
        """Return consumed minutes for a user/month."""
        try:
            resp = self.table.get_item(Key={"user_id": user_id, "usage_month": usage_month})
            item = resp.get("Item", {}) or {}
            consumed = item.get("consumed_minutes", 0)
            try:
                return int(consumed)
            except (TypeError, ValueError):
                return 0
        except ClientError as e:
            logger.error(f"DynamoDB get usage error: {e}")
            return 0

    def add_usage_minutes(
        self,
        user_id: str,
        usage_month: str,
        minutes: int,
        plan: Optional[str] = None,
        quota_minutes: Optional[int] = None,
    ) -> Optional[int]:
        """
        Add minutes to the user's monthly usage. Returns new total or None on failure.
        """
        try:
            update_expr = "SET updated_at = :updated_at"
            expr_values = {
                ":updated_at": get_current_timestamp(),
                ":minutes": Decimal(str(minutes)),
                ":one": Decimal("1"),
            }
            expr_names = {}

            if plan:
                expr_names["#plan"] = "plan"
                expr_values[":plan"] = plan
                update_expr += ", #plan = if_not_exists(#plan, :plan)"

            if quota_minutes is not None:
                expr_names["#quota"] = "quota_minutes"
                expr_values[":quota"] = quota_minutes
                update_expr += ", #quota = if_not_exists(#quota, :quota)"

            response = self.table.update_item(
                Key={"user_id": user_id, "usage_month": usage_month},
                UpdateExpression=f"{update_expr} ADD consumed_minutes :minutes, session_count :one",
                ExpressionAttributeNames=expr_names or None,
                ExpressionAttributeValues=expr_values,
                ReturnValues="UPDATED_NEW",
            )

            attributes = response.get("Attributes", {})
            consumed = attributes.get("consumed_minutes")
            try:
                return int(consumed)
            except (TypeError, ValueError):
                return None
        except ClientError as e:
            logger.error(f"DynamoDB update usage error: {e}")
            return None

    def is_over_quota(self, user_id: str, usage_month: str, quota_minutes: int) -> Dict[str, int]:
        """Check if user has exceeded quota. Returns dict with used and remaining."""
        used = self.get_usage_minutes(user_id, usage_month)
        remaining = quota_minutes - used
        return {"used": used, "remaining": remaining}

    def check_quota(self, user_id: str, quota_minutes: int) -> Dict[str, Any]:
        """
        Check if user can start a new session based on quota.
        Returns dict with allowed, consumed_minutes, remaining_minutes, resets_at.
        """
        if quota_minutes == -1:
            # Unlimited quota
            return {
                "allowed": True,
                "consumed_minutes": 0,
                "remaining_minutes": -1,
                "resets_at": None,
            }

        usage_month = self.current_month()
        consumed = self.get_usage_minutes(user_id, usage_month)
        remaining = quota_minutes - consumed

        # Calculate reset date (first day of next month)
        now = datetime.now(timezone.utc)
        if now.month == 12:
            next_month = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            next_month = datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)

        return {
            "allowed": remaining > 0,
            "consumed_minutes": consumed,
            "remaining_minutes": max(0, remaining),
            "resets_at": next_month.isoformat(),
        }

    def record_usage(self, user_id: str, minutes: int, plan: str = "freemium", quota_minutes: int = 300) -> bool:
        """
        Record usage for a user. Returns True on success.
        """
        usage_month = self.current_month()
        result = self.add_usage_minutes(user_id, usage_month, minutes, plan, quota_minutes)
        return result is not None

    def get_usage_stats(self, user_id: str, plan: str, quota_minutes: int) -> Dict[str, Any]:
        """
        Get comprehensive usage statistics for a user.
        Returns dict with user_id, plan, quota, consumed, remaining, session_count, resets_at.
        """
        usage_month = self.current_month()
        
        # Get usage data from DynamoDB
        try:
            resp = self.table.get_item(Key={"user_id": user_id, "usage_month": usage_month})
            item = resp.get("Item", {})
            consumed = int(item.get("consumed_minutes", 0)) if item else 0
            session_count = int(item.get("session_count", 0)) if item else 0
        except (ClientError, TypeError, ValueError) as e:
            logger.error(f"Error getting usage stats: {e}")
            consumed = 0
            session_count = 0

        # Calculate remaining
        if quota_minutes == -1:
            remaining = -1
        else:
            remaining = max(0, quota_minutes - consumed)

        # Calculate reset date
        now = datetime.now(timezone.utc)
        if now.month == 12:
            next_month = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            next_month = datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)

        return {
            "user_id": user_id,
            "usage_month": usage_month,
            "plan": plan,
            "quota_minutes": quota_minutes,
            "consumed_minutes": consumed,
            "remaining_minutes": remaining,
            "session_count": session_count,
            "resets_at": next_month.isoformat(),
        }



class EC2Client:
    """Helper class for EC2 operations."""
    
    def __init__(self):
        self.ec2 = boto3.client("ec2", region_name=AWS_REGION)
        self.ec2_resource = boto3.resource("ec2", region_name=AWS_REGION)
    
    def get_instance_status(self, instance_id: str) -> Optional[Dict[str, Any]]:
        """Get EC2 instance status with health checks."""
        try:
            # Get basic instance info
            response = self.ec2.describe_instances(InstanceIds=[instance_id])
            reservations = response.get("Reservations", [])
            if not reservations or not reservations[0].get("Instances"):
                return None
            
            instance = reservations[0]["Instances"][0]
            
            # Get instance status checks (system + instance reachability)
            try:
                status_response = self.ec2.describe_instance_status(
                    InstanceIds=[instance_id],
                    IncludeAllInstances=False  # Only running instances
                )
                
                if status_response.get("InstanceStatuses"):
                    status_info = status_response["InstanceStatuses"][0]
                    
                    # Extract status check results
                    system_status_obj = status_info.get("SystemStatus", {})
                    instance_status_obj = status_info.get("InstanceStatus", {})
                    
                    system_status = system_status_obj.get("Status", "unknown")
                    instance_status = instance_status_obj.get("Status", "unknown")
                    
                    # Get detailed checks (this is what shows as 3/3 in console)
                    system_details = system_status_obj.get("Details", [])
                    instance_details = instance_status_obj.get("Details", [])
                    
                    # Count passed checks
                    total_checks = len(system_details) + len(instance_details)
                    passed_checks = sum(
                        1 for check in (system_details + instance_details)
                        if check.get("Status") == "passed"
                    )
                    
                    # Consider "insufficient-data" as acceptable (status checks may not report immediately)
                    # Only "impaired" or "failed" is a real failure
                    system_ok = system_status in ["ok", "insufficient-data", "not-applicable"]
                    instance_ok = instance_status in ["ok", "insufficient-data", "not-applicable"]
                    
                    # All passed if both statuses OK or all individual checks passed
                    all_passed = (system_ok and instance_ok) or (total_checks > 0 and passed_checks == total_checks)
                    
                    # Add health check info to instance data
                    instance["HealthChecks"] = {
                        "system_status": system_status,
                        "instance_status": instance_status,
                        "passed_checks": passed_checks,
                        "total_checks": total_checks,
                        "all_passed": all_passed
                    }
                    
                    logger.info(f"Instance {instance_id} health: {passed_checks}/{total_checks} checks passed, "
                               f"system={system_status}, instance={instance_status}")
                else:
                    # Instance exists but no status checks yet (likely just started)
                    instance["HealthChecks"] = {
                        "system_status": "initializing",
                        "instance_status": "initializing",
                        "all_passed": False
                    }
            except ClientError as status_error:
                logger.warning(f"Could not get status checks for {instance_id}: {status_error}")
                # Instance might not be running yet
                instance["HealthChecks"] = {
                    "system_status": "unknown",
                    "instance_status": "unknown",
                    "all_passed": False
                }
            
            return instance
        except ClientError as e:
            logger.error(f"EC2 describe_instances error: {e}")
            return None
    
    def get_instance_private_ip(self, instance_id: str) -> Optional[str]:
        """Get the private IP of an EC2 instance."""
        instance = self.get_instance_status(instance_id)
        if instance:
            return instance.get("PrivateIpAddress")
        return None
    
    def start_instance(self, instance_id: str) -> bool:
        """Start an EC2 instance."""
        try:
            self.ec2.start_instances(InstanceIds=[instance_id])
            return True
        except ClientError as e:
            logger.error(f"EC2 start_instances error: {e}")
            return False
    
    def stop_instance(self, instance_id: str) -> bool:
        """Stop an EC2 instance."""
        try:
            self.ec2.stop_instances(InstanceIds=[instance_id])
            return True
        except ClientError as e:
            logger.error(f"EC2 stop_instances error: {e}")
            return False
    
    def tag_instance(self, instance_id: str, tags: Dict[str, str]) -> bool:
        """Add tags to an EC2 instance."""
        try:
            tag_list = [{"Key": k, "Value": v} for k, v in tags.items()]
            self.ec2.create_tags(Resources=[instance_id], Tags=tag_list)
            return True
        except ClientError as e:
            logger.error(f"EC2 create_tags error: {e}")
            return False
    
    def wait_for_instance_running(self, instance_id: str, timeout: int = 300) -> bool:
        """Wait for an instance to be in running state."""
        try:
            waiter = self.ec2.get_waiter("instance_running")
            waiter.wait(
                InstanceIds=[instance_id],
                WaiterConfig={"Delay": 10, "MaxAttempts": timeout // 10},
            )
            return True
        except Exception as e:
            logger.error(f"Wait for instance running error: {e}")
            return False


class AutoScalingClient:
    """Helper class for Auto Scaling operations."""
    
    def __init__(self):
        self.autoscaling = boto3.client("autoscaling", region_name=AWS_REGION)
    
    def get_asg_instances(self, asg_name: str) -> list:
        """Get instances in an Auto Scaling group."""
        try:
            response = self.autoscaling.describe_auto_scaling_groups(
                AutoScalingGroupNames=[asg_name]
            )
            groups = response.get("AutoScalingGroups", [])
            if groups:
                return groups[0].get("Instances", [])
            return []
        except ClientError as e:
            logger.error(f"ASG describe error: {e}")
            return []
    
    def get_asg_capacity(self, asg_name: str) -> Dict[str, int]:
        """Get ASG capacity settings."""
        try:
            response = self.autoscaling.describe_auto_scaling_groups(
                AutoScalingGroupNames=[asg_name]
            )
            groups = response.get("AutoScalingGroups", [])
            if groups:
                asg = groups[0]
                return {
                    "min": asg.get("MinSize", 0),
                    "max": asg.get("MaxSize", 0),
                    "desired": asg.get("DesiredCapacity", 0),
                }
            return {"min": 0, "max": 0, "desired": 0}
        except ClientError as e:
            logger.error(f"ASG describe error: {e}")
            return {"min": 0, "max": 0, "desired": 0}
    
    def set_desired_capacity(self, asg_name: str, capacity: int) -> bool:
        """Set the desired capacity of an ASG."""
        try:
            self.autoscaling.set_desired_capacity(
                AutoScalingGroupName=asg_name,
                DesiredCapacity=capacity,
            )
            return True
        except ClientError as e:
            logger.error(f"ASG set_desired_capacity error: {e}")
            return False


class GuacamoleClient:
    """
    Helper class for Guacamole REST API operations.
    Creates RDP connections and generates client URLs.
    """
    
    def __init__(
        self,
        base_url: str,
        username: str = "guacadmin",
        password: str = "guacadmin",
        timeout: int = 10,
    ):
        """
        Initialize Guacamole client.
        
        Args:
            base_url: Guacamole base URL (e.g., https://guac.example.com/guacamole)
            username: Admin username
            password: Admin password
        """
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.token = None
        self.data_source = "postgresql"  # Default data source
        # Per-request timeout in seconds for HTTP calls to Guacamole
        # This can be overridden (e.g. shorter timeout for termination path)
        self.timeout = timeout
        
        # Import here to avoid issues if not needed
        try:
            import urllib.request
            import urllib.parse
            import ssl
            self.urllib_request = urllib.request
            self.urllib_parse = urllib.parse
            # Create SSL context that doesn't verify (for self-signed certs)
            self.ssl_context = ssl.create_default_context()
            self.ssl_context.check_hostname = False
            self.ssl_context.verify_mode = ssl.CERT_NONE
        except ImportError as e:
            logger.error(f"Failed to import urllib: {e}")
            raise
    
    def _make_request(self, method: str, endpoint: str, data: dict = None, 
                      headers: dict = None, include_token: bool = True) -> Optional[dict]:
        """Make HTTP request to Guacamole API."""
        url = f"{self.base_url}/api{endpoint}"
        
        req_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if headers:
            req_headers.update(headers)
        
        if include_token and self.token:
            url = f"{url}{'&' if '?' in url else '?'}token={self.token}"
        
        body = None
        if data:
            body = json.dumps(data).encode("utf-8")
        
        try:
            request = self.urllib_request.Request(
                url, 
                data=body, 
                headers=req_headers,
                method=method
            )
            
            with self.urllib_request.urlopen(
                request,
                context=self.ssl_context,
                timeout=self.timeout,
            ) as response:
                response_body = response.read().decode("utf-8")
                if response_body:
                    return json.loads(response_body)
                return {}
        except Exception as e:
            logger.error(f"Guacamole API request failed: {method} {url} - {e}")
            return None
    
    def authenticate(self) -> bool:
        """Authenticate with Guacamole and get auth token."""
        try:
            # Guacamole uses form-encoded auth
            auth_data = self.urllib_parse.urlencode({
                "username": self.username,
                "password": self.password,
            }).encode("utf-8")
            
            request = self.urllib_request.Request(
                f"{self.base_url}/api/tokens",
                data=auth_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                method="POST"
            )
            
            with self.urllib_request.urlopen(request, context=self.ssl_context, timeout=self.timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
                self.token = result.get("authToken")
                self.data_source = result.get("dataSource", "postgresql")
                logger.info(f"Guacamole auth successful, data source: {self.data_source}")
                return self.token is not None
        except Exception as e:
            logger.error(f"Guacamole authentication failed: {e}")
            return False
    
    def create_rdp_connection(
        self,
        name: str,
        hostname: str,
        port: int = 3389,
        username: str = "",
        password: str = "",
        domain: str = "",
        security: str = "any",
        ignore_cert: bool = True,
        parent_identifier: str = "ROOT",
    ) -> Optional[str]:
        """
        Create an RDP connection in Guacamole.
        
        Args:
            name: Connection name (e.g., "AttackBox - student001")
            hostname: Target host IP or hostname
            port: RDP port (default 3389)
            username: RDP username (optional, can prompt user)
            password: RDP password (optional)
            domain: Windows domain (optional)
            security: Security mode (any, nla, tls, rdp)
            ignore_cert: Ignore certificate errors
            parent_identifier: Parent connection group (ROOT for top level)
            
        Returns:
            Connection identifier if successful, None otherwise
        """
        if not self.token:
            if not self.authenticate():
                return None
        
        connection_data = {
            "parentIdentifier": parent_identifier,
            "name": name,
            "protocol": "rdp",
            "parameters": {
                "hostname": hostname,
                "port": str(port),
                "security": security,
                "ignore-cert": "true" if ignore_cert else "false",
                "resize-method": "display-update",
                "enable-wallpaper": "false",
                "enable-theming": "false",
                "enable-font-smoothing": "true",
                "enable-full-window-drag": "false",
                "enable-desktop-composition": "false",
                "enable-menu-animations": "false",
                "disable-bitmap-caching": "false",
                "disable-offscreen-caching": "false",
                "color-depth": "24",
            },
            "attributes": {
                "max-connections": "1",
                "max-connections-per-user": "1",
            }
        }
        
        # Add credentials if provided
        if username:
            connection_data["parameters"]["username"] = username
        if password:
            connection_data["parameters"]["password"] = password
        if domain:
            connection_data["parameters"]["domain"] = domain
        
        result = self._make_request(
            "POST",
            f"/session/data/{self.data_source}/connections",
            data=connection_data
        )
        
        if result and "identifier" in result:
            conn_id = result["identifier"]
            logger.info(f"Created Guacamole RDP connection: {name} (ID: {conn_id})")
            return conn_id
        
        logger.error(f"Failed to create Guacamole connection: {result}")
        return None
    
    def delete_connection(self, connection_id: str) -> bool:
        """Delete a connection from Guacamole."""
        if not self.token:
            if not self.authenticate():
                return False
        
        result = self._make_request(
            "DELETE",
            f"/session/data/{self.data_source}/connections/{connection_id}"
        )
        
        # DELETE returns empty on success
        if result is not None:
            logger.info(f"Deleted Guacamole connection: {connection_id}")
            return True
        return False
    
    def get_connection_url(self, connection_id: str, connection_type: str = "c") -> str:
        """
        Generate a URL to directly access a connection.
        
        Args:
            connection_id: The connection identifier
            connection_type: 'c' for connection, 'g' for group
            
        Returns:
            Full URL to access the connection
        """
        # Encode connection identifier for URL
        import base64
        encoded_id = base64.b64encode(
            f"{connection_id}\x00{connection_type}\x00{self.data_source}".encode()
        ).decode()
        
        return f"{self.base_url}/#/client/{encoded_id}"
    
    def get_connection_with_token_url(self, connection_id: str) -> str:
        """
        Generate a URL with embedded auth token for direct access.
        The token allows bypassing the login page completely.
        
        Note: Guacamole tokens typically expire after some time (default ~60 min).
        
        IMPORTANT: Token must be BEFORE the # fragment to be sent to the server!
        Wrong:   {base_url}/#/client/{encoded_id}?token={token}  <- token not sent
        Correct: {base_url}/?token={token}#/client/{encoded_id}  <- token sent
        """
        if not self.token:
            if not self.authenticate():
                return self.get_connection_url(connection_id)
        
        if self.token:
            # Build URL with token BEFORE the fragment
            import base64
            encoded_id = base64.b64encode(
                f"{connection_id}\x00c\x00{self.data_source}".encode()
            ).decode()
            return f"{self.base_url}/?token={self.token}#/client/{encoded_id}"
        return self.get_connection_url(connection_id)
    
    def get_connection_activity(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """
        Get activity information for a specific connection.
        
        Checks if there are active sessions using this connection
        and when the last activity occurred.
        
        Args:
            connection_id: The connection identifier
            
        Returns:
            Dict with activity info:
            - active: bool - whether there are active connections
            - active_connections: int - number of active connections
            - last_activity: int - Unix timestamp of last activity (0 if unknown)
        """
        if not self.token:
            if not self.authenticate():
                return None
        
        try:
            # Get active connections from Guacamole
            result = self._make_request(
                "GET",
                f"/session/data/{self.data_source}/activeConnections"
            )
            
            if result is None:
                return None
            
            active_count = 0
            last_activity = 0
            
            # Check if our connection ID is in the active connections
            for conn_key, conn_data in result.items():
                # Connection key format varies, but usually contains the connection ID
                conn_identifier = conn_data.get("connectionIdentifier", "")
                
                if str(conn_identifier) == str(connection_id):
                    active_count += 1
                    
                    # Get start time (as proxy for activity)
                    start_date = conn_data.get("startDate")
                    if start_date:
                        # Convert milliseconds to seconds
                        try:
                            activity_ts = int(start_date) // 1000
                            if activity_ts > last_activity:
                                last_activity = activity_ts
                        except (ValueError, TypeError):
                            pass
            
            return {
                "active": active_count > 0,
                "active_connections": active_count,
                "last_activity": last_activity,
            }
            
        except Exception as e:
            logger.error(f"Error getting connection activity: {e}")
            return None
    
    def get_all_active_connections(self) -> Dict[str, Any]:
        """
        Get all active connections across the Guacamole server.
        
        Useful for checking overall activity and detecting orphaned sessions.
        
        Returns:
            Dict mapping connection identifiers to their active session info
        """
        if not self.token:
            if not self.authenticate():
                return {}
        
        try:
            result = self._make_request(
                "GET",
                f"/session/data/{self.data_source}/activeConnections"
            )
            
            if result is None:
                return {}
            
            # Group by connection identifier
            connections = {}
            for conn_key, conn_data in result.items():
                conn_id = conn_data.get("connectionIdentifier", "unknown")
                
                if conn_id not in connections:
                    connections[conn_id] = {
                        "active_sessions": [],
                        "total_connections": 0,
                    }
                
                connections[conn_id]["active_sessions"].append({
                    "key": conn_key,
                    "username": conn_data.get("username"),
                    "start_date": conn_data.get("startDate"),
                    "remote_host": conn_data.get("remoteHost"),
                })
                connections[conn_id]["total_connections"] += 1
            
            return connections
            
        except Exception as e:
            logger.error(f"Error getting all active connections: {e}")
            return {}
    
    def create_user(self, username: str, password: str) -> bool:
        """
        Create a new Guacamole user or update password if exists.
        
        Args:
            username: Username for the new user
            password: Password for the new user
            
        Returns:
            True if successful, False otherwise
        """
        if not self.token:
            if not self.authenticate():
                return False
        
        user_data = {
            "username": username,
            "password": password,
            "attributes": {
                "disabled": "",
                "expired": "",
                "access-window-start": "",
                "access-window-end": "",
                "valid-from": "",
                "valid-until": "",
                "timezone": "",
            }
        }
        
        # Try to create the user
        result = self._make_request(
            "POST",
            f"/session/data/{self.data_source}/users",
            data=user_data
        )
        
        if result is not None:
            logger.info(f"Created Guacamole user: {username}")
            return True
        
        # If POST failed, maybe user exists? Try to update password instead
        logger.info(f"User {username} might already exist, attempting to update password...")
        update_data = {
            "password": password
        }
        update_result = self._make_request(
            "PUT",
            f"/session/data/{self.data_source}/users/{username}",
            data=update_data
        )
        
        if update_result is not None:
            logger.info(f"Updated password for existing Guacamole user: {username}")
            return True
            
        return False
    
    def kill_active_sessions(self, connection_id: str) -> int:
        """
        Kill all active sessions for a specific connection.
        
        Args:
            connection_id: The connection ID to kill sessions for
            
        Returns:
            Number of sessions killed
        """
        if not self.token:
            if not self.authenticate():
                return 0
        
        try:
            # Get all active connections
            active_conns = self.get_all_active_connections()
            
            killed_count = 0
            for conn_id, conn_data in active_conns.items():
                if conn_id == connection_id:
                    # Kill each active session for this connection
                    for session in conn_data.get("active_sessions", []):
                        session_key = session.get("key")
                        if session_key:
                            result = self._make_request(
                                "DELETE",
                                f"/session/data/{self.data_source}/activeConnections/{session_key}"
                            )
                            if result is not None:
                                killed_count += 1
            
            if killed_count > 0:
                logger.info(f"Killed {killed_count} active session(s) for connection {connection_id}")
            
            return killed_count
        except Exception as e:
            logger.warning(f"Error killing active sessions for {connection_id}: {e}")
            return 0
    
    def delete_user(self, username: str) -> bool:
        """Delete a Guacamole user."""
        if not self.token:
            if not self.authenticate():
                return False
        
        result = self._make_request(
            "DELETE",
            f"/session/data/{self.data_source}/users/{username}"
        )
        
        if result is not None:
            logger.info(f"Deleted Guacamole user: {username}")
            return True
        return False
    
    def find_connections_by_hostname(self, hostname: str) -> list:
        """
        Find all connection identifiers that point to a specific hostname/IP.
        
        Args:
            hostname: The IP or hostname to search for
            
        Returns:
            List of connection identifiers
        """
        if not self.token:
            if not self.authenticate():
                return []
        
        try:
            # Get all connections
            result = self._make_request(
                "GET",
                f"/session/data/{self.data_source}/connections"
            )
            
            if not result:
                return []
            
            found_ids = []
            for conn_id, conn_data in result.items():
                params = conn_data.get("parameters", {})
                if params.get("hostname") == hostname:
                    found_ids.append(conn_id)
            
            return found_ids
        except Exception as e:
            logger.warning(f"Error finding connections by hostname: {e}")
            return []

    def grant_connection_permission(self, username: str, connection_id: str) -> bool:
        """
        Grant a user permission to access a specific connection.
        
        Args:
            username: The username to grant permission to
            connection_id: The connection ID to grant access to
            
        Returns:
            True if successful, False otherwise
        """
        if not self.token:
            if not self.authenticate():
                return False
        
        # Permission patch to add READ permission for the connection
        permission_data = [
            {
                "op": "add",
                "path": f"/connectionPermissions/{connection_id}",
                "value": "READ"
            }
        ]
        
        result = self._make_request(
            "PATCH",
            f"/session/data/{self.data_source}/users/{username}/permissions",
            data=permission_data
        )
        
        if result is not None:
            logger.info(f"Granted connection {connection_id} permission to user {username}")
            return True
        return False
    
    def authenticate_user(self, username: str, password: str) -> Optional[str]:
        """
        Authenticate as a specific user and return their token.
        
        Args:
            username: Username to authenticate as
            password: Password for the user
            
        Returns:
            Auth token if successful, None otherwise
        """
        try:
            auth_data = self.urllib_parse.urlencode({
                "username": username,
                "password": password,
            }).encode("utf-8")
            
            request = self.urllib_request.Request(
                f"{self.base_url}/api/tokens",
                data=auth_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                method="POST"
            )
            
            with self.urllib_request.urlopen(request, context=self.ssl_context, timeout=10) as response:
                result = json.loads(response.read().decode("utf-8"))
                return result.get("authToken")
        except Exception as e:
            logger.error(f"User authentication failed: {e}")
            return None
    
    def create_session_user_and_get_url(
        self,
        session_id: str,
        connection_id: str,
        student_id: str,
    ) -> Optional[str]:
        """
        Create a temporary user for the session, grant them access to the connection,
        and return a URL with their auth token for direct access.
        
        This provides secure, single-connection access without sharing admin credentials.
        
        Args:
            session_id: The session ID (used to generate unique username)
            connection_id: The connection ID to grant access to
            student_id: The student ID (for username generation)
            
        Returns:
            URL with embedded token for direct access, or None on failure
        """
        # Generate unique username and password for this session
        import hashlib
        username = f"session_{session_id[-8:]}"
        # Generate a random-ish password from session_id
        password = hashlib.sha256(f"{session_id}:{student_id}:secret".encode()).hexdigest()[:16]
        
        # Create the user
        if not self.create_user(username, password):
            logger.error(f"Failed to create session user {username}")
            return None
        
        # Grant permission to the connection
        if not self.grant_connection_permission(username, connection_id):
            logger.error(f"Failed to grant connection permission to {username}")
            # Try to clean up the user
            self.delete_user(username)
            return None
        
        # Delay to ensure Guacamole propagates user/permission changes
        # This prevents "disconnected" errors when the URL is opened immediately
        # Guacamole needs time to fully initialize the user, permissions, and connection state
        import time
        logger.info(f"Waiting for Guacamole user/permission propagation...")
        time.sleep(1.0)
        logger.info(f"Guacamole user/permission propagation delay complete")
        
        # Authenticate as the new user and get their token
        # Retry up to 3 times as Guacamole might take a moment to propagate
        user_token = None
        for i in range(3):
            user_token = self.authenticate_user(username, password)
            if user_token:
                break
            logger.info(f"Authentication attempt {i+1} for {username} failed, retrying in 1s...")
            time.sleep(1.0)
            
        if not user_token:
            logger.error(f"Failed to authenticate as session user {username} after retries")
            # Don't delete the user here, it might be useful for debugging or next attempt
            return None
        
        # Generate the URL with the user's token
        # IMPORTANT: Token must be BEFORE the # fragment to be sent to the server!
        # Wrong:   {base_url}/#/client/{encoded_id}?token={token}  <- token not sent
        # Correct: {base_url}/?token={token}#/client/{encoded_id}  <- token sent
        import base64
        encoded_id = base64.b64encode(
            f"{connection_id}\x00c\x00{self.data_source}".encode()
        ).decode()
        logger.info(f"Generated Guacamole URL for connection {connection_id}, user {username}")
        return f"{self.base_url}/?token={user_token}#/client/{encoded_id}"


# =============================================================================
# Moodle Token Verification
# =============================================================================

class MoodleTokenVerifier:
    """
    Verifies signed tokens from the Moodle AttackBox plugin.
    
    Tokens are signed using HMAC-SHA256 and contain user information,
    timestamp, expiry, and a nonce for replay attack prevention.
    """
    
    def __init__(self, secret: str):
        """
        Initialize the token verifier.
        
        Args:
            secret: The shared secret used for verifying token signatures.
        """
        self.secret = secret
        self._used_nonces: set = set()  # In production, use Redis/DynamoDB
        self._max_nonce_age = 300  # 5 minutes
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify a Moodle-signed token and return the payload if valid.
        
        Args:
            token: The signed token (base64_payload.signature)
            
        Returns:
            The decoded payload if valid, None if invalid.
        """
        if not token or not self.secret:
            logger.warning("Token verification failed: missing token or secret")
            return None
        
        try:
            # Split token into payload and signature
            parts = token.split(".")
            if len(parts) != 2:
                logger.warning("Token verification failed: invalid token format")
                return None
            
            payload_base64, signature = parts
            
            # Verify signature
            import hmac
            import hashlib
            
            expected_signature = hmac.new(
                self.secret.encode("utf-8"),
                payload_base64.encode("utf-8"),
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(signature, expected_signature):
                logger.warning("Token verification failed: invalid signature")
                return None
            
            # Decode payload
            payload_json = self._base64url_decode(payload_base64)
            payload = json.loads(payload_json)
            
            # Verify expiry
            expires = payload.get("expires", 0)
            if time.time() > expires:
                logger.warning("Token verification failed: token expired")
                return None
            
            # Verify nonce (prevent replay attacks)
            nonce = payload.get("nonce")
            if nonce:
                if nonce in self._used_nonces:
                    logger.warning("Token verification failed: nonce already used (replay attack?)")
                    return None
                self._used_nonces.add(nonce)
                # Clean up old nonces (in production, use TTL in Redis/DynamoDB)
                self._cleanup_old_nonces()
            
            logger.info(f"Token verified for user: {payload.get('user_id')}")
            return payload
            
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            return None
    
    def _base64url_decode(self, data: str) -> str:
        """Decode URL-safe base64."""
        # Add padding if needed
        remainder = len(data) % 4
        if remainder:
            data += "=" * (4 - remainder)
        
        import base64
        return base64.urlsafe_b64decode(data).decode("utf-8")
    
    def _cleanup_old_nonces(self):
        """Clean up nonces older than max age (simple in-memory implementation)."""
        # In production, this would be handled by TTL in Redis/DynamoDB
        # For Lambda, nonces are cleared on cold starts anyway
        if len(self._used_nonces) > 10000:
            self._used_nonces.clear()


def get_moodle_token_from_event(event: Dict[str, Any]) -> Optional[str]:
    """
    Extract the Moodle token from an API Gateway event.
    
    Looks for the token in:
    1. X-Moodle-Token header
    2. Authorization header (Bearer token)
    
    Args:
        event: API Gateway event
        
    Returns:
        The token string if found, None otherwise.
    """
    headers = event.get("headers") or {}
    
    # Try X-Moodle-Token header first
    token = headers.get("x-moodle-token") or headers.get("X-Moodle-Token")
    if token:
        return token
    
    # Try Authorization header
    auth_header = headers.get("authorization") or headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:]
    
    return None


def verify_moodle_request(event: Dict[str, Any], secret: str) -> Optional[Dict[str, Any]]:
    """
    Verify a Moodle-authenticated request.
    
    Convenience function that extracts and verifies the token from an event.
    
    Args:
        event: API Gateway event
        secret: The shared secret for verification
        
    Returns:
        The verified token payload if valid, None otherwise.
    """
    token = get_moodle_token_from_event(event)
    if not token:
        logger.warning("No Moodle token found in request")
        return None
    
    verifier = MoodleTokenVerifier(secret)
    return verifier.verify_token(token)
