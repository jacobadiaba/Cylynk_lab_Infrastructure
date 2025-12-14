"""
Get Session History Lambda Function

Returns user's session history and usage statistics.
Queries DynamoDB for all sessions belonging to a specific user.
"""

import logging
import os
import sys
from datetime import datetime, timezone

# Add common layer to path
sys.path.insert(0, "/opt/python")

from utils import (
    DynamoDBClient,
    error_response,
    get_moodle_token_from_event,
    get_path_parameter,
    success_response,
    verify_moodle_request,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
SESSIONS_TABLE = os.environ.get("SESSIONS_TABLE")
MOODLE_WEBHOOK_SECRET = os.environ.get("MOODLE_WEBHOOK_SECRET", "")
REQUIRE_MOODLE_AUTH = os.environ.get("REQUIRE_MOODLE_AUTH", "false").lower() == "true"


def handler(event, context):
    """
    Main handler for get session history requests.
    
    Routes:
    - GET /sessions/history - Get history for authenticated user (from token)
    - GET /sessions/history/{userId} - Get history for specific user (requires admin)
    
    Query Parameters:
    - limit: Maximum number of sessions to return (default: 50, max: 100)
    - status: Filter by session status (optional)
    
    Returns:
    {
        "sessions": [
            {
                "session_id": "sess-abc123",
                "student_id": "user123",
                "student_name": "John Doe",
                "status": "terminated",
                "created_at": "2025-12-01T10:00:00Z",
                "terminated_at": "2025-12-01T12:30:00Z",
                "duration_minutes": 150,
                "instance_id": "i-0123456789abcdef0"
            }
        ],
        "total_sessions": 15,
        "total_minutes": 2250
    }
    """
    logger.info(f"Get session history request: {event}")
    
    try:
        if not SESSIONS_TABLE:
            return error_response(503, "Sessions table not configured")
        
        # Try to get user_id from path parameter (admin query)
        path_user_id = get_path_parameter(event, "userId")
        
        # Verify Moodle token
        token_payload = None
        moodle_token = get_moodle_token_from_event(event)
        
        if moodle_token and MOODLE_WEBHOOK_SECRET:
            token_payload = verify_moodle_request(event, MOODLE_WEBHOOK_SECRET)
            if not token_payload:
                logger.warning("Invalid Moodle token provided")
                if REQUIRE_MOODLE_AUTH:
                    return error_response(401, "Invalid or expired authentication token")
        elif REQUIRE_MOODLE_AUTH and not path_user_id:
            return error_response(401, "Authentication required. Missing X-Moodle-Token header.")
        
        # Determine which user's history to query
        if path_user_id:
            # Admin query for specific user
            # TODO: Add admin role check here
            user_id = path_user_id
            logger.info(f"Admin querying history for user: {user_id}")
        elif token_payload:
            # User querying their own history
            user_id = token_payload.get("user_id")
            if not user_id:
                return error_response(400, "Invalid token: missing user_id")
        else:
            return error_response(400, "Missing user_id")
        
        # Parse query parameters
        query_params = event.get("queryStringParameters") or {}
        limit = int(query_params.get("limit", "50"))
        limit = min(limit, 100)  # Cap at 100
        
        status_filter = query_params.get("status")
        
        # Query sessions from DynamoDB
        db_client = DynamoDBClient(SESSIONS_TABLE)
        sessions = db_client.query_user_sessions(user_id, limit, status_filter)
        
        # Calculate total usage
        total_minutes = 0
        formatted_sessions = []
        
        for session in sessions:
            # Calculate duration if both created_at and terminated_at exist
            duration_minutes = 0
            created_at = session.get("created_at")
            terminated_at = session.get("terminated_at")
            
            if created_at and terminated_at:
                try:
                    start = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    end = datetime.fromisoformat(terminated_at.replace("Z", "+00:00"))
                    duration_seconds = (end - start).total_seconds()
                    duration_minutes = int(duration_seconds / 60)
                    total_minutes += duration_minutes
                except (ValueError, AttributeError) as e:
                    logger.warning(f"Error calculating duration for session {session.get('session_id')}: {e}")
            
            formatted_sessions.append({
                "session_id": session.get("session_id"),
                "student_id": session.get("student_id"),
                "student_name": session.get("student_name"),
                "status": session.get("status"),
                "created_at": created_at,
                "terminated_at": terminated_at,
                "duration_minutes": duration_minutes,
                "instance_id": session.get("instance_id"),
            })
        
        # Sort by created_at descending (most recent first)
        formatted_sessions.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        result = {
            "sessions": formatted_sessions,
            "total_sessions": len(formatted_sessions),
            "total_minutes": total_minutes,
        }
        
        return success_response(result, "Session history retrieved")
    
    except Exception as e:
        logger.exception("Error getting session history")
        return error_response(500, "Internal server error", str(e))
