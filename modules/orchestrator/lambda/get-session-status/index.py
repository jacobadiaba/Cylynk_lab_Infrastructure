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


def get_stage_info(session: dict) -> dict:
    """
    Calculate the current stage and progress for loading animations.
    
    Stages and their progress:
    - session_created: 5%
    - finding_instance: 10%
    - instance_claimed: 18%
    - instance_starting: 25%
    - instance_running: 33%
    - waiting_health: 42%
    - health_check_passed: 50%
    - creating_guac_connection: 62%
    - guac_connection_ready: 70%
    - creating_guac_user: 85%
    - generating_token: 94%
    - ready: 100%
    """
    status = session.get("status", "")
    instance_state = session.get("instance_state", "")
    connection_info = session.get("connection_info", {})
    
    # Determine stage based on status and available info
    if status == SessionStatus.PENDING:
        if session.get("instance_id"):
            return {
                "stage": "instance_claimed",
                "progress": 18,
                "message": "Instance assigned, preparing to start",
                "estimated_seconds": 45,
            }
        else:
            return {
                "stage": "finding_instance",
                "progress": 10,
                "message": "Finding available instance",
                "estimated_seconds": 55,
            }
    
    elif status == SessionStatus.PROVISIONING:
        if instance_state == "pending":
            return {
                "stage": "instance_starting",
                "progress": 25,
                "message": "Instance is starting up",
                "estimated_seconds": 40,
            }
        elif instance_state == "running":
            # Instance running but session not yet ready
            if not connection_info:
                return {
                    "stage": "waiting_health",
                    "progress": 42,
                    "message": "Waiting for instance health check",
                    "estimated_seconds": 25,
                }
            elif not connection_info.get("guacamole_connection_id"):
                return {
                    "stage": "creating_guac_connection",
                    "progress": 62,
                    "message": "Creating secure RDP connection",
                    "estimated_seconds": 15,
                }
            else:
                return {
                    "stage": "generating_token",
                    "progress": 94,
                    "message": "Generating access credentials",
                    "estimated_seconds": 3,
                }
        else:
            return {
                "stage": "instance_starting",
                "progress": 25,
                "message": "Instance is being prepared",
                "estimated_seconds": 40,
            }
    
    elif status == SessionStatus.READY:
        return {
            "stage": "ready",
            "progress": 100,
            "message": "AttackBox ready",
            "estimated_seconds": 0,
        }
    
    elif status == SessionStatus.ACTIVE:
        return {
            "stage": "ready",
            "progress": 100,
            "message": "AttackBox active",
            "estimated_seconds": 0,
        }
    
    elif status == SessionStatus.ERROR:
        return {
            "stage": "error",
            "progress": 0,
            "message": session.get("error", "An error occurred"),
            "estimated_seconds": 0,
        }
    
    elif status == SessionStatus.TERMINATED:
        return {
            "stage": "terminated",
            "progress": 0,
            "message": "Session terminated",
            "estimated_seconds": 0,
        }
    
    else:
        return {
            "stage": "session_created",
            "progress": 5,
            "message": "Session created",
            "estimated_seconds": 60,
        }


def calculate_time_remaining(session: dict) -> int:
    """Calculate remaining time in seconds."""
    expires_at = session.get("expires_at", 0)
    if not expires_at:
        return 0
    
    now = get_current_timestamp()
    remaining = expires_at - now
    return max(0, remaining)


def format_session_response(session: dict) -> dict:
    """Format session for API response with stage info for loading animations."""
    # Get stage info for loading animation
    stage_info = get_stage_info(session)
    
    # Calculate time remaining
    time_remaining = calculate_time_remaining(session)
    
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
        "direct_url": session.get("connection_info", {}).get("direct_url") 
                      or session.get("connection_info", {}).get("guacamole_connection_url"),
        "created_at": session.get("created_at"),
        "updated_at": session.get("updated_at"),
        "expires_at": session.get("expires_at"),
        "time_remaining": time_remaining,
        "error": session.get("error"),
        "termination_reason": session.get("termination_reason"),
        # Stage info for loading animations
        "stage": stage_info.get("stage"),
        "progress": stage_info.get("progress"),
        "stage_message": stage_info.get("message"),
        "estimated_seconds": stage_info.get("estimated_seconds"),
    }

