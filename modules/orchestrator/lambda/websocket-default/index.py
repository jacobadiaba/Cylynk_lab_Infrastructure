"""
WebSocket Default Handler

Handles incoming WebSocket messages from clients.
Currently supports ping/pong for connection keepalive.
"""

import json
import logging
import os
import sys

# Add common layer to path
sys.path.insert(0, "/opt/python")

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    """
    Handle incoming WebSocket messages.
    
    Supported actions:
    - ping: Respond with pong
    """
    connection_id = event["requestContext"]["connectionId"]
    
    try:
        body = json.loads(event.get("body", "{}"))
        action = body.get("action", "")
        
        logger.info(f"WebSocket message from {connection_id}: action={action}")
        
        if action == "ping":
            return {
                "statusCode": 200,
                "body": json.dumps({"action": "pong", "timestamp": context.aws_request_id})
            }
        else:
            logger.warning(f"Unknown action: {action}")
            return {
                "statusCode": 400,
                "body": json.dumps({"error": f"Unknown action: {action}"})
            }
            
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in message from {connection_id}")
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Invalid JSON"})
        }
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal server error"})
        }

