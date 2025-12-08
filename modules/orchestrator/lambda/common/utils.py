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


class EC2Client:
    """Helper class for EC2 operations."""
    
    def __init__(self):
        self.ec2 = boto3.client("ec2", region_name=AWS_REGION)
        self.ec2_resource = boto3.resource("ec2", region_name=AWS_REGION)
    
    def get_instance_status(self, instance_id: str) -> Optional[Dict[str, Any]]:
        """Get EC2 instance status."""
        try:
            response = self.ec2.describe_instances(InstanceIds=[instance_id])
            reservations = response.get("Reservations", [])
            if reservations and reservations[0].get("Instances"):
                return reservations[0]["Instances"][0]
            return None
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
    
    def __init__(self, base_url: str, username: str = "guacadmin", password: str = "guacadmin"):
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
            
            with self.urllib_request.urlopen(request, context=self.ssl_context, timeout=10) as response:
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
            
            with self.urllib_request.urlopen(request, context=self.ssl_context, timeout=10) as response:
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
        """
        if not self.token:
            if not self.authenticate():
                return self.get_connection_url(connection_id)
        
        conn_url = self.get_connection_url(connection_id)
        if self.token:
            return f"{conn_url}?token={self.token}"
        return conn_url
    
    def create_user(self, username: str, password: str) -> bool:
        """
        Create a new Guacamole user.
        
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
        
        result = self._make_request(
            "POST",
            f"/session/data/{self.data_source}/users",
            data=user_data
        )
        
        if result is not None:
            logger.info(f"Created Guacamole user: {username}")
            return True
        return False
    
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
        
        # Authenticate as the new user and get their token
        user_token = self.authenticate_user(username, password)
        if not user_token:
            logger.error(f"Failed to authenticate as session user {username}")
            self.delete_user(username)
            return None
        
        # Generate the URL with the user's token
        conn_url = self.get_connection_url(connection_id)
        return f"{conn_url}?token={user_token}"


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
