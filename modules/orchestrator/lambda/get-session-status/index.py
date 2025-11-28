"""
Get Session Status Lambda Function

Returns the current status of a session or all sessions for a student.
"""

import logging
import os
import sys

# Add common layer to path
sys.path.insert(0, "/opt/python")

from utils import (
    DynamoDBClient,
    EC2Client,
    InstanceStatus,
    SessionStatus,
    error_response,
    get_current_timestamp,
    get_path_parameter,
    success_response,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
SESSIONS_TABLE = os.environ.get("SESSIONS_TABLE")
INSTANCE_POOL_TABLE = os.environ.get("INSTANCE_POOL_TABLE")
GUACAMOLE_PRIVATE_IP = os.environ.get("GUACAMOLE_PRIVATE_IP", "")


def handler(event, context):
    """
    Main handler for session status requests.
    
    Routes:
    - GET /sessions/{sessionId} - Get specific session
    - GET /students/{studentId}/sessions - Get all sessions for a student
    """
    logger.info(f"Get session status request: {event}")
    
    try:
        # Initialize clients
        sessions_db = DynamoDBClient(SESSIONS_TABLE)
        pool_db = DynamoDBClient(INSTANCE_POOL_TABLE)
        ec2_client = EC2Client()
        
        # Determine which route was called
        route_key = event.get("routeKey", "")
        
        if "sessionId" in (event.get("pathParameters") or {}):
            # Get specific session
            session_id = get_path_parameter(event, "sessionId")
            return get_session_by_id(session_id, sessions_db, pool_db, ec2_client)
        
        elif "studentId" in (event.get("pathParameters") or {}):
            # Get all sessions for student
            student_id = get_path_parameter(event, "studentId")
            return get_sessions_by_student(student_id, sessions_db, pool_db, ec2_client)
        
        else:
            return error_response(400, "Missing sessionId or studentId parameter")
    
    except Exception as e:
        logger.exception("Error getting session status")
        return error_response(500, "Internal server error", str(e))


def get_session_by_id(session_id: str, sessions_db, pool_db, ec2_client):
    """Get a specific session by ID."""
    if not session_id:
        return error_response(400, "Missing sessionId")
    
    session = sessions_db.get_item({"session_id": session_id})
    
    if not session:
        return error_response(404, "Session not found")
    
    # Enrich session with live instance status if applicable
    session = enrich_session_status(session, pool_db, ec2_client)
    
    return success_response(
        format_session_response(session),
        "Session retrieved"
    )


def get_sessions_by_student(student_id: str, sessions_db, pool_db, ec2_client):
    """Get all sessions for a student."""
    if not student_id:
        return error_response(400, "Missing studentId")
    
    sessions = sessions_db.query_by_index("StudentIndex", "student_id", student_id)
    
    # Enrich each session and filter to active ones
    enriched_sessions = []
    for session in sessions:
        session = enrich_session_status(session, pool_db, ec2_client)
        enriched_sessions.append(format_session_response(session))
    
    # Sort by created_at descending
    enriched_sessions.sort(key=lambda x: x.get("created_at", 0), reverse=True)
    
    # Separate active and historical
    active_sessions = [
        s for s in enriched_sessions
        if s.get("status") in [SessionStatus.PENDING, SessionStatus.PROVISIONING,
                                SessionStatus.READY, SessionStatus.ACTIVE]
    ]
    
    return success_response(
        {
            "student_id": student_id,
            "active_sessions": active_sessions,
            "total_sessions": len(enriched_sessions),
            "sessions": enriched_sessions[:10],  # Last 10 sessions
        },
        f"Found {len(active_sessions)} active session(s)"
    )


def enrich_session_status(session: dict, pool_db, ec2_client) -> dict:
    """Enrich session with live instance status."""
    instance_id = session.get("instance_id")
    
    if not instance_id:
        return session
    
    # Check if session has expired
    now = get_current_timestamp()
    expires_at = session.get("expires_at", 0)
    
    if expires_at and now > expires_at:
        session["status"] = SessionStatus.TERMINATED
        session["termination_reason"] = "expired"
        return session
    
    # Get live instance status
    instance_info = ec2_client.get_instance_status(instance_id)
    
    if not instance_info:
        # Instance not found
        if session.get("status") not in [SessionStatus.TERMINATED, SessionStatus.ERROR]:
            session["status"] = SessionStatus.ERROR
            session["error"] = "Instance not found"
        return session
    
    instance_state = instance_info.get("State", {}).get("Name", "unknown")
    instance_ip = instance_info.get("PrivateIpAddress")
    
    # Update session based on instance state
    if instance_state == "running":
        if session.get("status") == SessionStatus.PROVISIONING:
            session["status"] = SessionStatus.READY
        
        session["instance_ip"] = instance_ip
        session["instance_state"] = instance_state
        
        # Build/update connection info
        if instance_ip and "connection_info" not in session:
            session["connection_info"] = {
                "type": "guacamole",
                "guacamole_url": f"https://{GUACAMOLE_PRIVATE_IP}/guacamole" if GUACAMOLE_PRIVATE_IP else None,
                "instance_ip": instance_ip,
                "rdp_port": 3389,
                "vnc_port": 5901,
                "ssh_port": 22,
            }
    
    elif instance_state == "pending":
        session["status"] = SessionStatus.PROVISIONING
        session["instance_state"] = instance_state
    
    elif instance_state in ["stopping", "shutting-down"]:
        session["status"] = SessionStatus.TERMINATING
        session["instance_state"] = instance_state
    
    elif instance_state in ["stopped", "terminated"]:
        session["status"] = SessionStatus.TERMINATED
        session["instance_state"] = instance_state
    
    return session


def format_session_response(session: dict) -> dict:
    """Format session for API response."""
    return {
        "session_id": session.get("session_id"),
        "student_id": session.get("student_id"),
        "student_name": session.get("student_name"),
        "course_id": session.get("course_id"),
        "lab_id": session.get("lab_id"),
        "status": session.get("status"),
        "instance_id": session.get("instance_id"),
        "instance_ip": session.get("instance_ip"),
        "instance_state": session.get("instance_state"),
        "connection_info": session.get("connection_info"),
        "created_at": session.get("created_at"),
        "updated_at": session.get("updated_at"),
        "expires_at": session.get("expires_at"),
        "error": session.get("error"),
        "termination_reason": session.get("termination_reason"),
    }

