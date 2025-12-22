"""
Session Heartbeat Lambda Function

Receives heartbeats from the browser/client and optionally queries
Guacamole for connection activity to track user activity.

Updates the session's last_active_at timestamp and returns idle status.
"""

import logging
import os
import sys

# Add common layer to path
sys.path.insert(0, "/opt/python")

from utils import (
    DynamoDBClient,
    GuacamoleClient,
    SessionStatus,
    error_response,
    get_current_timestamp,
    get_moodle_token_from_event,
    get_path_parameter,
    parse_request_body,
    success_response,
    verify_moodle_request,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
SESSIONS_TABLE = os.environ.get("SESSIONS_TABLE")
GUACAMOLE_PRIVATE_IP = os.environ.get("GUACAMOLE_PRIVATE_IP", "")
GUACAMOLE_PUBLIC_IP = os.environ.get("GUACAMOLE_PUBLIC_IP", "")
GUACAMOLE_API_URL = os.environ.get("GUACAMOLE_API_URL", "")
GUACAMOLE_ADMIN_USER = os.environ.get("GUACAMOLE_ADMIN_USER", "guacadmin")
GUACAMOLE_ADMIN_PASS = os.environ.get("GUACAMOLE_ADMIN_PASS", "guacadmin")
MOODLE_WEBHOOK_SECRET = os.environ.get("MOODLE_WEBHOOK_SECRET", "")
REQUIRE_MOODLE_AUTH = os.environ.get("REQUIRE_MOODLE_AUTH", "false").lower() == "true"

# Idle configuration (in seconds)
IDLE_WARNING_THRESHOLD = int(os.environ.get("IDLE_WARNING_THRESHOLD", "900"))  # 15 min default
IDLE_TERMINATION_THRESHOLD = int(os.environ.get("IDLE_TERMINATION_THRESHOLD", "1800"))  # 30 min default


def get_guacamole_internal_url() -> str:
    """Get the internal Guacamole URL for API calls."""
    if GUACAMOLE_API_URL:
        return GUACAMOLE_API_URL
    if GUACAMOLE_PUBLIC_IP:
        return f"https://{GUACAMOLE_PUBLIC_IP}/guacamole"
    if GUACAMOLE_PRIVATE_IP:
        return f"https://{GUACAMOLE_PRIVATE_IP}/guacamole"
    return ""


def check_guacamole_activity(session: dict) -> dict:
    """
    Check Guacamole for recent connection activity.
    
    Returns dict with:
    - connected: bool - whether user is currently connected
    - last_activity: int - timestamp of last activity (0 if unknown)
    - active_connections: int - number of active connections
    """
    result = {
        "connected": False,
        "last_activity": 0,
        "active_connections": 0,
    }
    
    connection_info = session.get("connection_info", {})
    connection_id = connection_info.get("guacamole_connection_id")
    
    if not connection_id:
        logger.debug("No Guacamole connection ID in session")
        return result
    
    internal_url = get_guacamole_internal_url()
    if not internal_url:
        logger.debug("Guacamole URL not configured")
        return result
    
    try:
        guac = GuacamoleClient(
            base_url=internal_url,
            username=GUACAMOLE_ADMIN_USER,
            password=GUACAMOLE_ADMIN_PASS,
        )
        
        # Get active connections for this connection ID
        activity = guac.get_connection_activity(connection_id)
        
        if activity:
            result["connected"] = activity.get("active", False)
            result["last_activity"] = activity.get("last_activity", 0)
            result["active_connections"] = activity.get("active_connections", 0)
            
            logger.info(f"Guacamole activity for connection {connection_id}: {result}")
        
    except Exception as e:
        logger.warning(f"Error checking Guacamole activity: {e}")
    
    return result


def handler(event, context):
    """
    Main handler for session heartbeat requests.
    
    POST /sessions/{sessionId}/heartbeat
    
    Request body (optional):
    {
        "activity_type": "browser" | "guacamole",
        "tab_visible": true/false,
        "focus_mode": true/false
    }
    
    Returns:
    {
        "session_id": "sess-xxx",
        "status": "active",
        "idle_seconds": 120,
        "idle_warning": false,
        "idle_warning_at": 900,
        "idle_termination_at": 1800,
        "time_until_warning": 780,
        "time_until_termination": 1680,
        "guacamole_connected": true
    }
    """
    logger.info(f"Session heartbeat request: {event}")
    
    try:
        if not SESSIONS_TABLE:
            return error_response(503, "Sessions table not configured")
        
        # Get session ID from path
        session_id = get_path_parameter(event, "sessionId")
        if not session_id:
            return error_response(400, "Missing session ID")
        
        # Parse request body
        body = parse_request_body(event)
        activity_type = body.get("activity_type", "browser")
        tab_visible = body.get("tab_visible", True)
        focus_mode = body.get("focus_mode", False)
        
        # Optional: Verify Moodle token
        token_payload = None
        moodle_token = get_moodle_token_from_event(event)
        
        if moodle_token and MOODLE_WEBHOOK_SECRET:
            token_payload = verify_moodle_request(event, MOODLE_WEBHOOK_SECRET)
            if not token_payload and REQUIRE_MOODLE_AUTH:
                return error_response(401, "Invalid authentication token")
        
        # Get session from DynamoDB
        sessions_db = DynamoDBClient(SESSIONS_TABLE)
        session = sessions_db.get_item({"session_id": session_id})
        
        if not session:
            return error_response(404, "Session not found")
        
        # Check if session is in a valid state
        status = session.get("status")
        if status not in [SessionStatus.READY, SessionStatus.ACTIVE, SessionStatus.PROVISIONING]:
            return error_response(400, f"Session is {status}, heartbeat not applicable")
        
        now = get_current_timestamp()
        created_at = session.get("created_at", now)
        last_active_at = session.get("last_active_at", created_at)
        expires_at = session.get("expires_at", 0)
        
        # Check Guacamole activity for more accurate idle detection
        guac_activity = check_guacamole_activity(session)
        guac_connected = guac_activity.get("connected", False)
        guac_last_activity = guac_activity.get("last_activity", 0)
        
        # Determine the most recent activity
        # Use Guacamole activity if available and more recent
        effective_last_active = last_active_at
        if guac_last_activity > 0 and guac_last_activity > last_active_at:
            effective_last_active = guac_last_activity
            logger.info(f"Using Guacamole last activity: {guac_last_activity}")
        
        # Update last_active_at if this is an active heartbeat
        should_update_activity = False
        
        if activity_type == "browser" and tab_visible:
            # Browser tab is visible, user is likely active
            should_update_activity = True
        elif guac_connected:
            # User is actively connected via Guacamole
            should_update_activity = True
        
        if should_update_activity:
            effective_last_active = now
        
        # Calculate idle time
        idle_seconds = now - effective_last_active
        
        # Get tier-specific idle thresholds
        plan = session.get("plan", "freemium")
        warning_threshold = get_idle_threshold_for_plan(plan, "warning")
        termination_threshold = get_idle_threshold_for_plan(plan, "termination")
        
        # If focus mode is enabled, don't apply idle termination
        if focus_mode:
            termination_threshold = float('inf')
            warning_threshold = float('inf')
        
        # Calculate warning state
        idle_warning = idle_seconds >= warning_threshold and idle_seconds < termination_threshold
        idle_critical = idle_seconds >= termination_threshold
        
        time_until_warning = max(0, warning_threshold - idle_seconds)
        time_until_termination = max(0, termination_threshold - idle_seconds)
        
        # Prepare update data
        update_data = {
            "last_active_at": effective_last_active,
            "last_heartbeat_at": now,
            "updated_at": now,
            "idle_seconds": idle_seconds,
            "guacamole_connected": guac_connected,
        }
        
        # Track warning state
        if idle_warning and not session.get("idle_warning_sent_at"):
            update_data["idle_warning_sent_at"] = now
            logger.info(f"Session {session_id} entered idle warning state")
        elif not idle_warning and session.get("idle_warning_sent_at"):
            # User became active again, clear warning
            update_data["idle_warning_sent_at"] = None
            logger.info(f"Session {session_id} became active again, clearing warning")
        
        # Update status to ACTIVE if currently READY and user is active
        if status == SessionStatus.READY and should_update_activity:
            update_data["status"] = SessionStatus.ACTIVE
        
        # Update session in DynamoDB
        sessions_db.update_item(
            {"session_id": session_id},
            update_data
        )
        
        # Build response
        response_data = {
            "session_id": session_id,
            "status": update_data.get("status", status),
            "idle_seconds": idle_seconds,
            "idle_warning": idle_warning,
            "idle_critical": idle_critical,
            "idle_warning_threshold": warning_threshold,
            "idle_termination_threshold": termination_threshold,
            "time_until_warning": time_until_warning,
            "time_until_termination": time_until_termination,
            "guacamole_connected": guac_connected,
            "guacamole_active_connections": guac_activity.get("active_connections", 0),
            "expires_at": expires_at,
            "focus_mode": focus_mode,
            "plan": plan,
        }
        
        # Add warning message if applicable
        if idle_critical:
            response_data["warning_message"] = "Session will be terminated due to inactivity"
            response_data["warning_level"] = "critical"
        elif idle_warning:
            minutes_until_termination = int(time_until_termination / 60)
            response_data["warning_message"] = f"Session idle - will terminate in {minutes_until_termination} minutes"
            response_data["warning_level"] = "warning"
        
        return success_response(response_data, "Heartbeat received")
    
    except Exception as e:
        logger.exception("Error processing heartbeat")
        return error_response(500, "Internal server error", str(e))


def get_idle_threshold_for_plan(plan: str, threshold_type: str) -> int:
    """
    Get idle threshold based on plan tier.
    
    Tier-based thresholds:
    - Freemium: More aggressive (15 min warning, 30 min termination)
    - Starter: Moderate (20 min warning, 40 min termination)
    - Pro: Relaxed (30 min warning, 60 min termination)
    """
    thresholds = {
        "freemium": {
            "warning": int(os.environ.get("IDLE_WARNING_FREEMIUM", "900")),      # 15 min
            "termination": int(os.environ.get("IDLE_TERMINATION_FREEMIUM", "1800")),  # 30 min
        },
        "starter": {
            "warning": int(os.environ.get("IDLE_WARNING_STARTER", "1200")),      # 20 min
            "termination": int(os.environ.get("IDLE_TERMINATION_STARTER", "2400")),   # 40 min
        },
        "pro": {
            "warning": int(os.environ.get("IDLE_WARNING_PRO", "1800")),          # 30 min
            "termination": int(os.environ.get("IDLE_TERMINATION_PRO", "3600")),       # 60 min
        },
    }
    
    plan_thresholds = thresholds.get(plan, thresholds["freemium"])
    return plan_thresholds.get(threshold_type, IDLE_WARNING_THRESHOLD)
