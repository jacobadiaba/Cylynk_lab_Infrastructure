"""
WebSocket Disconnect Handler

Handles WebSocket disconnections:
1. Removes connection from DynamoDB
2. Logs disconnection event
"""

import json
import logging
import os
import sys

# Add common layer to path
sys.path.insert(0, "/opt/python")

from utils import DynamoDBClient

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
CONNECTIONS_TABLE = os.environ.get("CONNECTIONS_TABLE")


def handler(event, context):
    """
    Handle WebSocket disconnection.
    """
    connection_id = event["requestContext"]["connectionId"]
    
    logger.info(f"WebSocket disconnection: {connection_id}")
    
    try:
        connections_db = DynamoDBClient(CONNECTIONS_TABLE)
        
        # Delete connection record
        connections_db.delete_item({"connection_id": connection_id})
        
        logger.info(f"Connection {connection_id} removed from database")
        
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Disconnected"})
        }
        
    except Exception as e:
        logger.error(f"Error removing connection: {e}")
        # Don't fail on disconnect errors - connection is already closed
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Disconnected"})
        }

