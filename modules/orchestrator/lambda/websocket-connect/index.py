"""
WebSocket Connect Handler

Handles new WebSocket connections:
1. Validates authentication token
2. Extracts session_id or user_id from query params
3. Stores connection in DynamoDB
"""

import json
import logging
import os
import sys
from urllib.parse import parse_qs

# Add common layer to path
sys.path.insert(0, "/opt/python")

from utils import (
    DynamoDBClient,
    get_current_timestamp,
    MoodleTokenVerifier,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
CONNECTIONS_TABLE = os.environ.get("CONNECTIONS_TABLE")
MOODLE_WEBHOOK_SECRET = os.environ.get("MOODLE_WEBHOOK_SECRET", "")
REQUIRE_MOODLE_AUTH = os.environ.get("REQUIRE_MOODLE_AUTH", "false").lower() == "true"


def handler(event, context):
    """
    Handle WebSocket connection.
    
    Query params:
    - token: Moodle authentication token (required if REQUIRE_MOODLE_AUTH=true)
    - session_id: Session ID to subscribe to (optional)
    - user_id: User ID to subscribe to (optional)
    """
    connection_id = event["requestContext"]["connectionId"]
    domain_name = event["requestContext"]["domainName"]
    stage = event["requestContext"]["stage"]
    
    logger.info(f"WebSocket connection: {connection_id}")
    
    # Parse query string parameters
    query_params = event.get("queryStringParameters") or {}
    token = query_params.get("token", "")
    session_id = query_params.get("session_id", "")
    user_id = query_params.get("user_id", "")
    connection_type = query_params.get("type", "session_status")  # session_status or admin_dashboard
    
    # Validate authentication if required
    if REQUIRE_MOODLE_AUTH:
        if not token:
            logger.warning(f"Connection {connection_id} rejected: No token provided")
            return {
                "statusCode": 401,
                "body": json.dumps({"error": "Authentication required"})
            }
        
        try:
            verifier = MoodleTokenVerifier(MOODLE_WEBHOOK_SECRET)
            token_data = verifier.verify_token(token)
            if not token_data:
                logger.warning(f"Connection {connection_id} rejected: Invalid token")
                return {
                    "statusCode": 401,
                    "body": json.dumps({"error": "Invalid authentication token"})
                }
            
            # Use user_id from token if not provided in query params
            if not user_id and token_data.get("user_id"):
                user_id = token_data["user_id"]
                
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            return {
                "statusCode": 401,
                "body": json.dumps({"error": "Token validation failed"})
            }
    
    # Validate that we have either session_id or user_id
    if not session_id and not user_id:
        logger.warning(f"Connection {connection_id} rejected: No session_id or user_id provided")
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "session_id or user_id required"})
        }
    
    # Store connection in DynamoDB
    try:
        connections_db = DynamoDBClient(CONNECTIONS_TABLE)
        now = get_current_timestamp()
        
        connection_record = {
            "connection_id": connection_id,
            "user_id": user_id or "",
            "session_id": session_id or "",
            "connection_type": connection_type,
            "connected_at": now,
            "ttl": now + 3600,  # 1 hour TTL
        }
        
        connections_db.put_item(connection_record)
        
        logger.info(f"Connection {connection_id} stored: user_id={user_id}, session_id={session_id}, type={connection_type}")
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Connected",
                "connection_id": connection_id
            })
        }
        
    except Exception as e:
        logger.error(f"Error storing connection: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Failed to establish connection"})
        }

