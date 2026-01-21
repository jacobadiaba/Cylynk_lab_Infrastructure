"""
Terminate Session Lambda Function

Handles requests to terminate a student's AttackBox session.
Cleans up Guacamole connection.
"""

import logging
import os
import sys

# Add common layer to path
sys.path.insert(0, "/opt/python")

from utils import (
    DynamoDBClient,
    EC2Client,
    GuacamoleClient,
    InstanceStatus,
    SessionStatus,
    UsageTracker,
    error_response,
    get_current_timestamp,
    get_iso_timestamp,
    get_path_parameter,
    parse_request_body,
    success_response,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
SESSIONS_TABLE = os.environ.get("SESSIONS_TABLE")
INSTANCE_POOL_TABLE = os.environ.get("INSTANCE_POOL_TABLE")
USAGE_TABLE = os.environ.get("USAGE_TABLE")
GUACAMOLE_PRIVATE_IP = os.environ.get("GUACAMOLE_PRIVATE_IP", "")
GUACAMOLE_PUBLIC_IP = os.environ.get("GUACAMOLE_PUBLIC_IP", "")
GUACAMOLE_API_URL = os.environ.get("GUACAMOLE_API_URL", "")
GUACAMOLE_ADMIN_USER = os.environ.get("GUACAMOLE_ADMIN_USER", "guacadmin")
GUACAMOLE_ADMIN_PASS = os.environ.get("GUACAMOLE_ADMIN_PASS", "guacadmin")
ENABLE_GUACAMOLE_CLEANUP = os.environ.get("ENABLE_GUACAMOLE_CLEANUP", "true").lower() == "true"


def cleanup_guacamole_resources(connection_id: str, session_username: str = None) -> dict:
    """
    Delete the Guacamole connection and session user for this session.
    
    This is a best-effort operation - failures here should NOT block session termination.
    Uses a short timeout (2 seconds) to prevent blocking the termination process.
    
    Returns:
        dict with cleanup results
    """
    # Prefer public URL for Lambdas outside VPC, then explicit API URL, then private IP
    # This helps avoid timeouts when Guacamole is only reachable via its public address.
    guac_url = (
        (f"https://{GUACAMOLE_PUBLIC_IP}/guacamole" if GUACAMOLE_PUBLIC_IP else None)
        or (GUACAMOLE_API_URL or None)
        or (f"https://{GUACAMOLE_PRIVATE_IP}/guacamole" if GUACAMOLE_PRIVATE_IP else "")
    )
    
    result = {
        "connection_deleted": False,
        "user_deleted": False,
        "sessions_killed": 0,
        "error": None,
    }
    
    if not guac_url:
        logger.warning("No Guacamole URL configured, skipping cleanup")
        return result
    
    try:
        # Use very short timeout for Guacamole operations during termination
        # This prevents Guacamole issues from blocking session termination
        guac = GuacamoleClient(
            base_url=guac_url,
            username=GUACAMOLE_ADMIN_USER,
            password=GUACAMOLE_ADMIN_PASS,
            timeout=2,  # 2-second timeout for quick termination
        )
        
        # Kill active sessions first (force disconnects users)
        if connection_id:
            try:
                result["sessions_killed"] = guac.kill_active_sessions(connection_id)
                if result["sessions_killed"] > 0:
                    logger.info(f"Killed {result['sessions_killed']} active session(s) for connection {connection_id}")
            except Exception as e:
                logger.warning(f"Error killing active sessions for {connection_id}: {e}")
        
        # Delete the connection definition
        if connection_id:
            try:
                result["connection_deleted"] = guac.delete_connection(connection_id)
                if result["connection_deleted"]:
                    logger.info(f"Deleted Guacamole connection: {connection_id}")
                else:
                    logger.warning(f"Failed to delete Guacamole connection: {connection_id}")
            except Exception as e:
                logger.warning(f"Error deleting Guacamole connection {connection_id}: {e}")
                result["error"] = str(e)
        
        # Delete the session user
        if session_username:
            try:
                result["user_deleted"] = guac.delete_user(session_username)
                if result["user_deleted"]:
                    logger.info(f"Deleted Guacamole session user: {session_username}")
                else:
                    logger.warning(f"Failed to delete Guacamole user: {session_username}")
            except Exception as e:
                logger.warning(f"Error deleting Guacamole user {session_username}: {e}")
        
        return result
    except Exception as e:
        # Log but don't fail - Guacamole cleanup is best-effort
        logger.warning(f"Guacamole cleanup failed (non-blocking): {e}")
        result["error"] = str(e)
        return result


def handler(event, context):
    """
    Main handler for terminate session requests.
    
    Routes:
    - DELETE /sessions/{sessionId} - Terminate specific session
    
    Optional body:
    {
        "reason": "user_requested",  # or "admin", "timeout", etc.
        "stop_instance": true        # Whether to stop the EC2 instance
    }
    """
    logger.info(f"Terminate session request: {event}")
    
    try:
        # Get session ID from path
        session_id = get_path_parameter(event, "sessionId")
        
        if not session_id:
            return error_response(400, "Missing sessionId")
        
        # Parse optional body
        body = parse_request_body(event)
        reason = body.get("reason", "user_requested")
        stop_instance = body.get("stop_instance", True)
        
        # Initialize clients
        sessions_db = DynamoDBClient(SESSIONS_TABLE)
        pool_db = DynamoDBClient(INSTANCE_POOL_TABLE)
        ec2_client = EC2Client()
        
        # Get session
        session = sessions_db.get_item({"session_id": session_id})
        
        if not session:
            return error_response(404, "Session not found")
        
        # Check if already terminated
        if session.get("status") in [SessionStatus.TERMINATED, SessionStatus.TERMINATING]:
            return success_response(
                {
                    "session_id": session_id,
                    "status": session.get("status"),
                    "message": "Session already terminated or terminating",
                },
                "Session already terminated"
            )
        
        now = get_current_timestamp()
        instance_id = session.get("instance_id")
        connection_info = session.get("connection_info", {})
        
        # Update session status
        sessions_db.update_item(
            {"session_id": session_id},
            {
                "status": SessionStatus.TERMINATING,
                "termination_reason": reason,
                "terminated_at": now,
                "updated_at": now,
            }
        )
        
        # Delete Guacamole connection and session user if they exist
        # This is best-effort - failures here should NOT block termination
        guac_connection_id = connection_info.get("guacamole_connection_id")
        guac_session_user = connection_info.get("guacamole_session_user")
        guac_cleanup = {"connection_deleted": False, "user_deleted": False, "error": None, "skipped": False}
        
        if not ENABLE_GUACAMOLE_CLEANUP:
            logger.info("Guacamole cleanup disabled via ENABLE_GUACAMOLE_CLEANUP=false")
            guac_cleanup["skipped"] = True
        elif guac_connection_id or guac_session_user:
            try:
                logger.info(f"Attempting Guacamole cleanup for connection {guac_connection_id}")
                guac_cleanup = cleanup_guacamole_resources(guac_connection_id, guac_session_user)
                
                if guac_cleanup.get("error"):
                    logger.warning(f"Guacamole cleanup completed with errors: {guac_cleanup['error']}")
                elif guac_cleanup.get("connection_deleted") or guac_cleanup.get("user_deleted"):
                    logger.info(f"Guacamole cleanup successful")
            except Exception as e:
                # Never let Guacamole cleanup block session termination
                logger.warning(f"Guacamole cleanup exception (continuing anyway): {e}")
                guac_cleanup["error"] = str(e)
        
        # Handle instance
        instance_stopped = False
        if instance_id:
            # Update pool record
            pool_db.update_item(
                {"instance_id": instance_id},
                {
                    "status": InstanceStatus.STOPPING if stop_instance else InstanceStatus.AVAILABLE,
                    "session_id": None,
                    "student_id": None,
                    "released_at": now,
                }
            )
            
            # Remove session tags from instance
            ec2_client.tag_instance(instance_id, {
                "SessionId": "",
                "StudentId": "",
                "ReleasedAt": get_iso_timestamp(),
            })
            
            # Optionally stop the instance
            if stop_instance:
                if ec2_client.stop_instance(instance_id):
                    instance_stopped = True
                    logger.info(f"Stopped instance {instance_id}")
                else:
                    logger.warning(f"Failed to stop instance {instance_id}")
        
        # Track usage if session was active (before marking as terminated)
        if USAGE_TABLE and session.get("student_id"):
            created_at = session.get("created_at", now)
            duration_minutes = (now - created_at) / 60
            
            # Only charge if session ran for at least some time
            if duration_minutes >= 0.5:  # At least 30 seconds
                try:
                    usage_tracker = UsageTracker(USAGE_TABLE)
                    usage_tracker.record_usage(
                        user_id=session["student_id"],
                        minutes=int(duration_minutes)
                    )
                    logger.info(f"Recorded {int(duration_minutes)} minutes of usage for user {session['student_id']}")
                except Exception as e:
                    logger.error(f"Failed to record usage: {e}")
                    # Don't fail the termination if usage tracking fails
        
        # Mark session as terminated - THIS MUST HAPPEN
        logger.info(f"Marking session {session_id} as TERMINATED")
        try:
            sessions_db.update_item(
                {"session_id": session_id},
                {
                    "status": SessionStatus.TERMINATED,
                    "updated_at": get_current_timestamp(),
                }
            )
            logger.info(f"Successfully marked session {session_id} as TERMINATED")
        except Exception as e:
            logger.error(f"CRITICAL: Failed to mark session {session_id} as TERMINATED: {e}")
            # Re-raise to ensure we know about this failure
            raise
        
        return success_response(
            {
                "session_id": session_id,
                "status": SessionStatus.TERMINATED,
                "instance_id": instance_id,
                "instance_stopped": instance_stopped,
                "guacamole_sessions_killed": guac_cleanup.get("sessions_killed", 0),
                "guacamole_connection_deleted": guac_cleanup.get("connection_deleted", False),
                "guacamole_user_deleted": guac_cleanup.get("user_deleted", False),
                "reason": reason,
                "terminated_at": now,
            },
            "Session terminated successfully"
        )
    
    except Exception as e:
        logger.exception("Error terminating session")
        return error_response(500, "Internal server error", str(e))
