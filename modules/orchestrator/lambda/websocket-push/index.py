"""
WebSocket Push Handler

Processes DynamoDB Stream events and pushes session status updates
to connected WebSocket clients.
"""

import json
import logging
import os
import sys
import boto3

# Add common layer to path
sys.path.insert(0, "/opt/python")

from utils import DynamoDBClient

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
CONNECTIONS_TABLE = os.environ.get("CONNECTIONS_TABLE")
WEBSOCKET_API_ENDPOINT = os.environ.get("WEBSOCKET_API_ENDPOINT")
WEBSOCKET_API_ID = os.environ.get("WEBSOCKET_API_ID")

# Initialize API Gateway Management API client
# The endpoint URL should be the WebSocket API endpoint (wss:// -> https://)
def get_apigw_client():
    """Get API Gateway Management API client with proper endpoint."""
    if WEBSOCKET_API_ENDPOINT:
        # Convert wss:// to https:// for Management API
        endpoint = WEBSOCKET_API_ENDPOINT.replace("wss://", "https://").replace("ws://", "http://")
        return boto3.client(
            "apigatewaymanagementapi",
            endpoint_url=endpoint
        )
    elif WEBSOCKET_API_ID:
        # Fallback: construct endpoint from API ID and region
        region = os.environ.get("AWS_REGION", "us-east-1")
        endpoint = f"https://{WEBSOCKET_API_ID}.execute-api.{region}.amazonaws.com/{os.environ.get('API_STAGE_NAME', 'v1')}"
        return boto3.client(
            "apigatewaymanagementapi",
            endpoint_url=endpoint
        )
    else:
        raise ValueError("WEBSOCKET_API_ENDPOINT or WEBSOCKET_API_ID environment variable must be set")


def send_to_connection(connection_id, message):
    """Send message to a WebSocket connection."""
    try:
        apigw_client = get_apigw_client()
        apigw_client.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps(message)
        )
        return True
    except apigw_client.exceptions.ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        if error_code == "GoneException":
            logger.warning(f"Connection {connection_id} is gone, will be cleaned up")
        else:
            logger.error(f"Error sending to connection {connection_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"Error sending to connection {connection_id}: {e}")
        return False


def handler(event, context):
    """
    Process DynamoDB Stream events and push updates to WebSocket connections.
    """
    logger.info(f"Processing {len(event['Records'])} DynamoDB stream records")
    
    connections_db = DynamoDBClient(CONNECTIONS_TABLE)
    pushed_count = 0
    error_count = 0
    
    for record in event["Records"]:
        try:
            # Only process MODIFY events
            if record["eventName"] != "MODIFY":
                continue
            
            # Extract session data from DynamoDB stream
            new_image = record["dynamodb"]["NewImage"]
            old_image = record["dynamodb"].get("OldImage", {})
            
            # Convert DynamoDB format to regular dict
            session = {}
            for key, value in new_image.items():
                if "S" in value:
                    session[key] = value["S"]
                elif "N" in value:
                    session[key] = int(value["N"])
                elif "BOOL" in value:
                    session[key] = value["BOOL"]
                elif "M" in value:
                    session[key] = {k: list(v.values())[0] for k, v in value["M"].items()}
            
            session_id = session.get("session_id")
            status = session.get("status")
            student_id = session.get("student_id")
            
            if not session_id:
                continue
            
            logger.info(f"Session {session_id} status changed to {status}")
            
            # Find all connections subscribed to this session
            connections = []
            
            # Query by session_id
            if session_id:
                session_connections = connections_db.query_by_index(
                    "SessionIndex",
                    "session_id",
                    session_id
                )
                connections.extend(session_connections)
            
            # Query by user_id (student_id)
            if student_id:
                user_connections = connections_db.query_by_index(
                    "UserIndex",
                    "user_id",
                    student_id
                )
                # Filter to avoid duplicates
                existing_ids = {c["connection_id"] for c in connections}
                connections.extend([
                    c for c in user_connections
                    if c["connection_id"] not in existing_ids
                ])
            
            # Prepare update message
            update_message = {
                "type": "session_update",
                "session_id": session_id,
                "status": status,
                "data": {
                    "session_id": session_id,
                    "status": status,
                    "student_id": student_id,
                    "instance_id": session.get("instance_id"),
                    "instance_ip": session.get("instance_ip"),
                    "direct_url": session.get("direct_url"),
                    "connection_info": session.get("connection_info"),
                    "progress": session.get("progress"),
                    "stage": session.get("stage"),
                    "stage_message": session.get("stage_message"),
                }
            }
            
            # Send update to all connected clients
            for connection in connections:
                connection_id = connection["connection_id"]
                if send_to_connection(connection_id, update_message):
                    pushed_count += 1
                    logger.debug(f"Pushed update to connection {connection_id}")
                else:
                    error_count += 1
            
        except Exception as e:
            logger.error(f"Error processing stream record: {e}")
            error_count += 1
            continue
    
    logger.info(f"Pushed {pushed_count} updates, {error_count} errors")
    
    return {
        "statusCode": 200,
        "body": json.dumps({
            "pushed": pushed_count,
            "errors": error_count
        })
    }

