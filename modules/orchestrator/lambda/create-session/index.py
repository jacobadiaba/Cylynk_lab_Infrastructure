"""
Create Session Lambda Function

Handles requests from Moodle to launch an AttackBox for a student.
Automatically creates an RDP connection in Guacamole.
"""

import logging
import os
import sys

# Add common layer to path
sys.path.insert(0, "/opt/python")

from utils import (
    AutoScalingClient,
    DynamoDBClient,
    EC2Client,
    GuacamoleClient,
    InstanceStatus,
    SessionStatus,
    UsageTracker,
    calculate_expiry,
    error_response,
    DEFAULT_PLAN_LIMITS,
    generate_session_id,
    get_current_timestamp,
    get_iso_timestamp,
    get_moodle_token_from_event,
    parse_request_body,
    success_response,
    verify_moodle_request,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
SESSIONS_TABLE = os.environ.get("SESSIONS_TABLE")
INSTANCE_POOL_TABLE = os.environ.get("INSTANCE_POOL_TABLE")
GUACAMOLE_PRIVATE_IP = os.environ.get("GUACAMOLE_PRIVATE_IP", "")
GUACAMOLE_PUBLIC_IP = os.environ.get("GUACAMOLE_PUBLIC_IP", "")
GUACAMOLE_API_URL = os.environ.get("GUACAMOLE_API_URL", "")
GUACAMOLE_ADMIN_USER = os.environ.get("GUACAMOLE_ADMIN_USER", "guacadmin")
GUACAMOLE_ADMIN_PASS = os.environ.get("GUACAMOLE_ADMIN_PASS", "guacadmin")
SESSION_TTL_HOURS = int(os.environ.get("SESSION_TTL_HOURS", "4"))
MAX_SESSIONS = int(os.environ.get("MAX_SESSIONS", "1"))
USAGE_TABLE = os.environ.get("USAGE_TABLE")

# Multi-tier ASG configuration
ASG_NAME_FREEMIUM = os.environ.get("ASG_NAME_FREEMIUM", "")
ASG_NAME_STARTER = os.environ.get("ASG_NAME_STARTER", "")
ASG_NAME_PRO = os.environ.get("ASG_NAME_PRO", "")

# Moodle authentication
MOODLE_WEBHOOK_SECRET = os.environ.get("MOODLE_WEBHOOK_SECRET", "")
REQUIRE_MOODLE_AUTH = os.environ.get("REQUIRE_MOODLE_AUTH", "false").lower() == "true"

# RDP connection defaults (can be overridden via request)
RDP_USERNAME = os.environ.get("RDP_USERNAME", "kali")
RDP_PASSWORD = os.environ.get("RDP_PASSWORD", "kali")


def get_asg_for_plan(plan: str) -> str:
    """Get the ASG name for a given plan tier."""
    asg_map = {
        "freemium": ASG_NAME_FREEMIUM,
        "starter": ASG_NAME_STARTER,
        "pro": ASG_NAME_PRO,
    }
    asg_name = asg_map.get(plan)
    if not asg_name:
        # Fall back to freemium if plan not recognized or ASG not configured
        asg_name = ASG_NAME_FREEMIUM or ASG_NAME_STARTER or ASG_NAME_PRO
        logger.warning(f"Plan '{plan}' ASG not configured, falling back to: {asg_name}")
    return asg_name


def get_guacamole_public_url() -> str:
    """Get the public-facing Guacamole URL for students."""
    if GUACAMOLE_API_URL:
        return GUACAMOLE_API_URL
    if GUACAMOLE_PUBLIC_IP:
        return f"https://{GUACAMOLE_PUBLIC_IP}/guacamole"
    if GUACAMOLE_PRIVATE_IP:
        # Fallback to private IP (won't work for external access)
        logger.warning("Using private IP for Guacamole URL - external access won't work!")
        return f"https://{GUACAMOLE_PRIVATE_IP}/guacamole"
    return ""


def get_guacamole_internal_url() -> str:
    """Get the internal Guacamole URL for API calls (can use private IP)."""
    if GUACAMOLE_API_URL:
        return GUACAMOLE_API_URL
    if GUACAMOLE_PUBLIC_IP:
        return f"https://{GUACAMOLE_PUBLIC_IP}/guacamole"
    if GUACAMOLE_PRIVATE_IP:
        return f"https://{GUACAMOLE_PRIVATE_IP}/guacamole"
    return ""


def resolve_plan_info(token_payload: dict) -> tuple[str, int, list]:
    """
    Resolve plan, quota_minutes, and roles from the Moodle token payload.
    Falls back to defaults if not provided.
    """
    plan = (token_payload or {}).get("plan") or "freemium"
    quota_minutes = (token_payload or {}).get("quota_minutes")
    roles = (token_payload or {}).get("roles", [])

    if quota_minutes is None:
        quota_minutes = DEFAULT_PLAN_LIMITS.get(plan, -1)

    try:
        quota_minutes = int(quota_minutes)
    except (TypeError, ValueError):
        quota_minutes = DEFAULT_PLAN_LIMITS.get(plan, -1)

    return plan, quota_minutes, roles


def check_guacamole_connection_active(connection_id: str) -> bool:
    """
    Check if a user is actually connected to a Guacamole connection.
    
    This is used to detect stale sessions where the user logged out of
    Guacamole but the session wasn't properly terminated.
    
    Args:
        connection_id: The Guacamole connection identifier
        
    Returns:
        True if there's an active connection, False otherwise
    """
    logger.info(f"[STALE_SESSION_CHECK] Checking Guacamole connection activity for connection_id={connection_id}")
    
    internal_url = get_guacamole_internal_url()
    if not internal_url or not connection_id:
        logger.info(f"[STALE_SESSION_CHECK] No Guacamole URL or connection_id, returning False")
        return False
    
    try:
        guac = GuacamoleClient(
            base_url=internal_url,
            username=GUACAMOLE_ADMIN_USER,
            password=GUACAMOLE_ADMIN_PASS,
            timeout=3,  # Short timeout to avoid blocking
        )
        
        activity = guac.get_connection_activity(connection_id)
        logger.info(f"[STALE_SESSION_CHECK] Guacamole activity response: {activity}")
        
        if activity and activity.get("active", False):
            logger.info(f"[STALE_SESSION_CHECK] User IS actively connected to Guacamole")
            return True
        
        logger.info(f"[STALE_SESSION_CHECK] User is NOT connected to Guacamole (stale session detected)")
        return False
        
    except Exception as e:
        logger.warning(f"[STALE_SESSION_CHECK] Error checking Guacamole activity: {e} - assuming NOT connected")
        # On error, assume NOT connected to allow session recreation
        # This is safer than blocking users from creating new sessions
        return False


def cleanup_stale_session(
    session: dict,
    sessions_db: DynamoDBClient,
    pool_db: DynamoDBClient,
    reason: str = "stale_reconnect"
) -> None:
    """
    Clean up a stale session that the user is no longer connected to.
    
    This handles the case where a user logged out of Guacamole without
    properly ending their session via the API.
    
    Args:
        session: The session record to clean up
        sessions_db: DynamoDB client for sessions table
        pool_db: DynamoDB client for instance pool table
        reason: The termination reason to record
    """
    session_id = session["session_id"]
    student_id = session.get("student_id")
    instance_id = session.get("instance_id")
    connection_info = session.get("connection_info", {})
    now = get_current_timestamp()
    
    logger.info(f"[STALE_SESSION_CLEANUP] ========== STARTING STALE SESSION CLEANUP ==========")
    logger.info(f"[STALE_SESSION_CLEANUP] Session ID: {session_id}")
    logger.info(f"[STALE_SESSION_CLEANUP] Student ID: {student_id}")
    logger.info(f"[STALE_SESSION_CLEANUP] Instance ID: {instance_id}")
    logger.info(f"[STALE_SESSION_CLEANUP] Reason: {reason}")
    logger.info(f"[STALE_SESSION_CLEANUP] Previous status: {session.get('status')}")
    
    # Update session status to terminated
    logger.info(f"[STALE_SESSION_CLEANUP] Marking session as TERMINATED in DynamoDB...")
    sessions_db.update_item(
        {"session_id": session_id},
        {
            "status": SessionStatus.TERMINATED,
            "termination_reason": reason,
            "terminated_at": now,
            "updated_at": now,
        }
    )
    logger.info(f"[STALE_SESSION_CLEANUP] Session marked as TERMINATED successfully")
    
    # Release the instance back to the pool if assigned
    if instance_id:
        logger.info(f"[STALE_SESSION_CLEANUP] Releasing instance {instance_id} back to pool...")
        pool_db.update_item(
            {"instance_id": instance_id},
            {
                "status": InstanceStatus.AVAILABLE,
                "session_id": None,
                "student_id": None,
                "released_at": now,
            }
        )
        logger.info(f"[STALE_SESSION_CLEANUP] Instance {instance_id} released to pool (status=AVAILABLE)")
    else:
        logger.info(f"[STALE_SESSION_CLEANUP] No instance to release")
    
    # Clean up Guacamole resources (best effort)
    guac_connection_id = connection_info.get("guacamole_connection_id")
    guac_session_user = connection_info.get("guacamole_session_user")
    
    logger.info(f"[STALE_SESSION_CLEANUP] Guacamole connection ID: {guac_connection_id}")
    logger.info(f"[STALE_SESSION_CLEANUP] Guacamole session user: {guac_session_user}")
    
    if guac_connection_id or guac_session_user:
        internal_url = get_guacamole_internal_url()
        if internal_url:
            try:
                guac = GuacamoleClient(
                    base_url=internal_url,
                    username=GUACAMOLE_ADMIN_USER,
                    password=GUACAMOLE_ADMIN_PASS,
                    timeout=3,
                )
                
                # Delete the connection
                if guac_connection_id:
                    logger.info(f"[STALE_SESSION_CLEANUP] Deleting Guacamole connection {guac_connection_id}...")
                    if guac.delete_connection(guac_connection_id):
                        logger.info(f"[STALE_SESSION_CLEANUP] Guacamole connection {guac_connection_id} deleted successfully")
                    else:
                        logger.warning(f"[STALE_SESSION_CLEANUP] Failed to delete Guacamole connection {guac_connection_id}")
                
                # Delete the session user
                if guac_session_user:
                    logger.info(f"[STALE_SESSION_CLEANUP] Deleting Guacamole user {guac_session_user}...")
                    if guac.delete_user(guac_session_user):
                        logger.info(f"[STALE_SESSION_CLEANUP] Guacamole user {guac_session_user} deleted successfully")
                    else:
                        logger.warning(f"[STALE_SESSION_CLEANUP] Failed to delete Guacamole user {guac_session_user}")
                        
            except Exception as e:
                # Best effort - don't fail if Guacamole cleanup fails
                logger.warning(f"[STALE_SESSION_CLEANUP] Guacamole cleanup failed (non-blocking): {e}")
    else:
        logger.info(f"[STALE_SESSION_CLEANUP] No Guacamole resources to clean up")
    
    logger.info(f"[STALE_SESSION_CLEANUP] ========== STALE SESSION CLEANUP COMPLETE ==========")
    logger.info(f"[STALE_SESSION_CLEANUP] User {student_id} can now create a new session")


def create_guacamole_connection(
    session_id: str,
    student_id: str,
    student_name: str,
    instance_ip: str,
    course_id: str = "",
) -> dict:
    """
    Create an RDP connection in Guacamole for the student.
    Also creates a temporary user with access only to this connection,
    providing secure, direct access without sharing credentials.
    
    Returns:
        dict with connection_id and connection_url, or empty dict on failure
    """
    # Use internal URL for API calls
    internal_url = get_guacamole_internal_url()
    # Use public URL for student-facing links
    public_url = get_guacamole_public_url()
    
    if not internal_url:
        logger.warning("Guacamole URL not configured, skipping connection creation")
        return {}
    
    try:
        guac = GuacamoleClient(
            base_url=internal_url,
            username=GUACAMOLE_ADMIN_USER,
            password=GUACAMOLE_ADMIN_PASS,
        )
        
        # Create a unique connection name
        connection_name = f"AttackBox - {student_name} ({session_id[-8:]})"
        if course_id:
            connection_name = f"[{course_id}] {connection_name}"
        
        # Create RDP connection
        connection_id = guac.create_rdp_connection(
            name=connection_name,
            hostname=instance_ip,
            port=3389,
            username=RDP_USERNAME,
            password=RDP_PASSWORD,
            security="any",
            ignore_cert=True,
        )
        
        if not connection_id:
            logger.error("Failed to create Guacamole connection")
            return {}
        
        logger.info(f"Created Guacamole connection {connection_id} for session {session_id}")
        
        # Switch to public URL for generating student-facing links
        guac.base_url = public_url
        
        # Create a temporary session user and get a direct-access URL
        # This bypasses the login page entirely
        direct_url = guac.create_session_user_and_get_url(
            session_id=session_id,
            connection_id=connection_id,
            student_id=student_id,
        )
        
        # Generate username for cleanup later
        session_username = f"session_{session_id[-8:]}"
        
        if direct_url:
            logger.info(f"Created session user {session_username} with direct access URL")
            return {
                "guacamole_connection_id": connection_id,
                "guacamole_connection_url": direct_url,  # URL with embedded token
                "guacamole_base_url": public_url,
                "guacamole_session_user": session_username,
            }
        else:
            # Fallback to regular URL (will require login)
            logger.warning("Could not create session user, falling back to regular URL")
            connection_url = guac.get_connection_url(connection_id)
            return {
                "guacamole_connection_id": connection_id,
                "guacamole_connection_url": connection_url,
                "guacamole_base_url": public_url,
            }
            
    except Exception as e:
        logger.error(f"Error creating Guacamole connection: {e}")
        return {}


def handler(event, context):
    """
    Main handler for create session requests.
    
    Authentication:
    - If REQUIRE_MOODLE_AUTH is true, requires X-Moodle-Token header
    - Token contains user info (user_id, username, fullname, email)
    - Falls back to request body if auth not required
    
    Expected request body (when not using token auth):
    {
        "student_id": "student123",
        "student_name": "John Doe",
        "course_id": "course456",
        "lab_id": "lab789",  # optional
        "metadata": {}       # optional additional data
    }
    """
    logger.info(f"Create session request: {event}")
    
    try:
        # Parse request body
        body = parse_request_body(event)
        
        # Try to verify Moodle token if provided
        token_payload = None
        moodle_token = get_moodle_token_from_event(event)
        
        if moodle_token:
            if MOODLE_WEBHOOK_SECRET:
                token_payload = verify_moodle_request(event, MOODLE_WEBHOOK_SECRET)
                if not token_payload:
                    logger.warning("Invalid Moodle token provided")
                    if REQUIRE_MOODLE_AUTH:
                        return error_response(401, "Invalid or expired authentication token")
            else:
                logger.warning("Moodle token provided but MOODLE_WEBHOOK_SECRET not configured")
        elif REQUIRE_MOODLE_AUTH:
            return error_response(401, "Authentication required. Missing X-Moodle-Token header.")
        
        # Extract user info from token or body
        if token_payload:
            # Use verified token data (trusted)
            student_id = token_payload.get("user_id")
            student_name = token_payload.get("fullname") or token_payload.get("username", "Unknown")
            student_email = token_payload.get("email", "")
            moodle_site = token_payload.get("site_url", "")
            # Course is NOT tied - AttackBox is independent
            course_id = "independent"
            lab_id = "attackbox"
            metadata = body.get("metadata", {})
            metadata["auth_method"] = "moodle_token"
            metadata["moodle_site"] = moodle_site
            metadata["student_email"] = student_email
        else:
            # Use request body (less secure, for testing)
            student_id = body.get("student_id")
            student_name = body.get("student_name", "Unknown")
            course_id = body.get("course_id", "independent")
            lab_id = body.get("lab_id", "attackbox")
            metadata = body.get("metadata", {})
            metadata["auth_method"] = "request_body"
        
        if not student_id:
            return error_response(400, "Missing required field: student_id")
        
        # Resolve plan and quota from token
        plan, quota_minutes, roles = resolve_plan_info(token_payload)
        logger.info(f"User {student_id} plan: {plan}, quota: {quota_minutes} minutes")
        
        # Check usage quota (unless unlimited)
        if USAGE_TABLE and quota_minutes != -1:
            usage_tracker = UsageTracker(USAGE_TABLE)
            quota_check = usage_tracker.check_quota(student_id, quota_minutes)
            
            if not quota_check["allowed"]:
                logger.warning(f"Quota exceeded for user {student_id}: {quota_check}")
                return error_response(
                    403,
                    "Monthly usage limit exceeded",
                    {
                        "error": "quota_exceeded",
                        "plan": plan,
                        "consumed_minutes": quota_check["consumed_minutes"],
                        "quota_minutes": quota_minutes,
                        "remaining_minutes": 0,
                        "resets_at": quota_check["resets_at"],
                    }
                )
            
            logger.info(f"Quota check passed: {quota_check['remaining_minutes']} minutes remaining")
        
        # Initialize clients
        sessions_db = DynamoDBClient(SESSIONS_TABLE)
        pool_db = DynamoDBClient(INSTANCE_POOL_TABLE)
        ec2_client = EC2Client()
        asg_client = AutoScalingClient()
        
        # Check for existing active session
        existing_sessions = sessions_db.query_by_index(
            "StudentIndex", "student_id", student_id
        )
        
        active_sessions = [
            s for s in existing_sessions
            if s.get("status") in [SessionStatus.PENDING, SessionStatus.PROVISIONING, 
                                    SessionStatus.READY, SessionStatus.ACTIVE]
        ]
        
        if len(active_sessions) >= MAX_SESSIONS:
            session = active_sessions[0]
            connection_info = session.get("connection_info", {})
            guac_connection_id = connection_info.get("guacamole_connection_id")
            
            logger.info(f"[STALE_SESSION_CHECK] ========== EXISTING SESSION FOUND ==========")
            logger.info(f"[STALE_SESSION_CHECK] User {student_id} already has {len(active_sessions)} active session(s)")
            logger.info(f"[STALE_SESSION_CHECK] Existing session ID: {session['session_id']}")
            logger.info(f"[STALE_SESSION_CHECK] Existing session status: {session.get('status')}")
            logger.info(f"[STALE_SESSION_CHECK] Guacamole connection ID: {guac_connection_id}")
            logger.info(f"[STALE_SESSION_CHECK] Checking if user is actually connected to Guacamole...")
            
            # Check if the user is actually connected to Guacamole
            # If they logged out via Guacamole's logout button, the session
            # will appear "active" in DynamoDB but they won't be connected
            is_actually_connected = False
            
            if guac_connection_id:
                is_actually_connected = check_guacamole_connection_active(guac_connection_id)
                logger.info(f"[STALE_SESSION_CHECK] Guacamole connection check result: connected={is_actually_connected}")
            else:
                # No Guacamole connection ID - might be in PENDING/PROVISIONING state
                # These are still valid sessions that haven't finished setup yet
                if session.get("status") in [SessionStatus.PENDING, SessionStatus.PROVISIONING]:
                    logger.info(f"[STALE_SESSION_CHECK] Session is still provisioning (no Guacamole connection yet)")
                    logger.info(f"[STALE_SESSION_CHECK] Returning existing provisioning session")
                    return success_response(
                        {
                            "session_id": session["session_id"],
                            "status": session["status"],
                            "instance_id": session.get("instance_id"),
                            "connection_info": connection_info,
                            "created_at": session.get("created_at"),
                            "expires_at": session.get("expires_at"),
                            "reused": True,
                        },
                        "Existing session found (provisioning)"
                    )
                else:
                    logger.info(f"[STALE_SESSION_CHECK] No Guacamole connection ID but session is {session.get('status')}")
            
            if is_actually_connected:
                # User IS connected - return existing session as before
                logger.info(f"[STALE_SESSION_CHECK] ===== USER IS ACTIVELY CONNECTED =====")
                logger.info(f"[STALE_SESSION_CHECK] Returning existing session (user is using it)")
                return success_response(
                    {
                        "session_id": session["session_id"],
                        "status": session["status"],
                        "instance_id": session.get("instance_id"),
                        "connection_info": connection_info,
                        "created_at": session.get("created_at"),
                        "expires_at": session.get("expires_at"),
                        "reused": True,
                    },
                    "Existing session found"
                )
            else:
                # User is NOT connected - session is stale (user logged out of Guacamole)
                # Clean up the stale session and continue to create a new one
                logger.info(f"[STALE_SESSION_CHECK] ===== STALE SESSION DETECTED =====")
                logger.info(f"[STALE_SESSION_CHECK] User logged out of Guacamole but session was not terminated")
                logger.info(f"[STALE_SESSION_CHECK] Auto-terminating stale session and creating a new one...")
                cleanup_stale_session(session, sessions_db, pool_db, reason="stale_guacamole_logout")
                logger.info(f"[STALE_SESSION_CHECK] Proceeding to create new session for user {student_id}")
        
        # Generate new session
        session_id = generate_session_id()
        now = get_current_timestamp()
        expires_at = calculate_expiry(SESSION_TTL_HOURS)
        
        # Get the ASG for this user's plan
        asg_name = get_asg_for_plan(plan)
        logger.info(f"Using ASG {asg_name} for plan {plan}")
        
        # Create session record in pending state
        session_record = {
            "session_id": session_id,
            "student_id": student_id,
            "student_name": student_name,
            "course_id": course_id,
            "lab_id": lab_id,
            "plan": plan,  # Store plan in session for filtering
            "status": SessionStatus.PENDING,
            "created_at": now,
            "updated_at": now,
            "expires_at": expires_at,
            "metadata": metadata,
        }
        
        if not sessions_db.put_item(session_record):
            return error_response(500, "Failed to create session record")
        
        # Try to find an available instance from the pool for this plan
        # Use pessimistic locking to prevent race conditions
        instance_id = None
        instance_ip = None
        max_allocation_retries = 3
        
        # Query available instances and filter by plan
        all_available = pool_db.query_by_index(
            "StatusIndex", "status", InstanceStatus.AVAILABLE
        )
        # Filter by plan - only use instances from the same tier
        available_instances = [
            inst for inst in all_available
            if inst.get("plan", "pro") == plan  # Default to "pro" for backward compat
        ]
        logger.info(f"Found {len(available_instances)} available instances for plan {plan}")
        
        # Try to allocate an instance with retry logic for race conditions
        for retry_attempt in range(max_allocation_retries):
            if not available_instances:
                logger.info(f"No available instances found (attempt {retry_attempt + 1}/{max_allocation_retries})")
                break
                
            # Try each available instance until we successfully claim one
            for pool_record in available_instances:
                candidate_id = pool_record["instance_id"]
                
                try:
                    # Verify instance is actually running
                    instance_info = ec2_client.get_instance_status(candidate_id)
                    if not instance_info or instance_info.get("State", {}).get("Name") != "running":
                        # Instance not running, mark as unhealthy
                        pool_db.update_item(
                            {"instance_id": candidate_id},
                            {"status": InstanceStatus.UNHEALTHY}
                        )
                        continue
                    
                    # Atomically claim the instance using conditional update
                    # This prevents race conditions by ensuring status is still AVAILABLE
                    update_success = pool_db.conditional_update(
                        {"instance_id": candidate_id},
                        {
                            "status": InstanceStatus.ASSIGNED,
                            "session_id": session_id,
                            "student_id": student_id,
                            "assigned_at": now,
                        },
                        condition_expression="#status = :available",
                        expression_attribute_names={"#status": "status"},
                        expression_attribute_values={":available": InstanceStatus.AVAILABLE}
                    )
                    
                    if update_success:
                        # Successfully claimed the instance
                        instance_id = candidate_id
                        instance_ip = instance_info.get("PrivateIpAddress")
                        
                        # Tag the instance
                        ec2_client.tag_instance(instance_id, {
                            "SessionId": session_id,
                            "StudentId": student_id,
                            "AssignedAt": get_iso_timestamp(),
                        })
                        
                        logger.info(f"Successfully allocated instance {instance_id} to session {session_id}")
                        break
                    else:
                        # Another Lambda grabbed this instance, try next one
                        logger.info(f"Instance {candidate_id} was claimed by another session, trying next")
                        continue
                        
                except Exception as e:
                    logger.warning(f"Error attempting to allocate instance {candidate_id}: {str(e)}")
                    continue
            
            # If we successfully allocated an instance, break out of retry loop
            if instance_id:
                break
            
            # If not successful and we have retries left, re-query for available instances
            if retry_attempt < max_allocation_retries - 1:
                import time
                time.sleep(0.3 * (retry_attempt + 1))  # Exponential backoff
                all_available = pool_db.query_by_index(
                    "StatusIndex", "status", InstanceStatus.AVAILABLE
                )
                available_instances = [
                    inst for inst in all_available
                    if inst.get("plan", "pro") == plan
                ]
        
        # If no available instance, check ASG for stopped instances or scale up
        if not instance_id:
            logger.info(f"No immediately available instances for session {session_id}, checking ASG {asg_name} for warm pool or scaling")
            asg_instances = asg_client.get_asg_instances(asg_name)
            logger.info(f"Found {len(asg_instances)} instances in ASG {asg_name}")
            
            # Look for stopped instances we can start (warm pool) or running instances we can use
            for asg_instance in asg_instances:
                inst_id = asg_instance.get("InstanceId")
                lifecycle_state = asg_instance.get("LifecycleState")
                
                if lifecycle_state == "InService" or lifecycle_state == "Warmed:Stopped":
                    instance_info = ec2_client.get_instance_status(inst_id)
                    if instance_info:
                        state = instance_info.get("State", {}).get("Name")
                        
                        # Check pool record for this instance
                        pool_record = pool_db.get_item({"instance_id": inst_id})
                        pool_status = pool_record.get("status") if pool_record else None
                        pool_session = pool_record.get("session_id") if pool_record else None
                        
                        logger.info(f"Instance {inst_id}: state={state}, pool_status={pool_status}, pool_session={pool_session}")
                        
                        if state == "stopped" and pool_status != InstanceStatus.ASSIGNED:
                            # Start this instance (warm pool)
                            logger.info(f"Starting warm pool instance {inst_id} for session {session_id}")
                            if ec2_client.start_instance(inst_id):
                                instance_id = inst_id
                                
                                # Update/create pool record with plan
                                pool_db.put_item({
                                    "instance_id": inst_id,
                                    "status": InstanceStatus.STARTING,
                                    "session_id": session_id,
                                    "student_id": student_id,
                                    "assigned_at": now,
                                    "plan": plan,  # Track which tier this instance belongs to
                                })
                                
                                # Update session to provisioning with note
                                sessions_db.update_item(
                                    {"session_id": session_id},
                                    {
                                        "status": SessionStatus.PROVISIONING,
                                        "instance_id": inst_id,
                                        "updated_at": now,
                                        "provisioning_note": "Starting warm pool instance (30-60 seconds + status checks)",
                                    }
                                )
                                logger.info(f"Session {session_id} assigned to starting warm pool instance {inst_id}")
                                break
                        
                        elif state == "running":
                            # Check if instance is truly available
                            # It's usable if: no pool record, status is AVAILABLE, or status is STARTING/ASSIGNED but session is invalid
                            can_use = False
                            
                            if not pool_record:
                                can_use = True
                                logger.info(f"Instance {inst_id} has no pool record, claiming it")
                            elif pool_status == InstanceStatus.AVAILABLE:
                                can_use = True
                                logger.info(f"Instance {inst_id} is AVAILABLE, claiming it")
                            elif pool_status in [InstanceStatus.STARTING, InstanceStatus.ASSIGNED] and pool_session:
                                # Check if the assigned session is still valid
                                existing_session = sessions_db.get_item({"session_id": pool_session})
                                if not existing_session or existing_session.get("status") in [SessionStatus.TERMINATED, SessionStatus.ERROR]:
                                    can_use = True
                                    logger.info(f"Instance {inst_id} was assigned to invalid session {pool_session}, reclaiming it")
                                else:
                                    logger.info(f"Instance {inst_id} is assigned to active session {pool_session}, skipping")
                            else:
                                logger.info(f"Instance {inst_id} has status {pool_status}, skipping")
                            
                            if can_use:
                                instance_id = inst_id
                                instance_ip = instance_info.get("PrivateIpAddress")
                                
                                pool_db.put_item({
                                    "instance_id": inst_id,
                                    "status": InstanceStatus.ASSIGNED,
                                    "session_id": session_id,
                                    "student_id": student_id,
                                    "assigned_at": now,
                                    "plan": plan,  # Track which tier this instance belongs to
                                })
                                logger.info(f"Session {session_id} assigned to running instance {inst_id}")
                                break
        
        # If still no instance, request ASG scale up
        if not instance_id:
            capacity = asg_client.get_asg_capacity(asg_name)
            if capacity["desired"] < capacity["max"]:
                new_capacity = capacity["desired"] + 1
                if asg_client.set_desired_capacity(asg_name, new_capacity):
                    logger.info(f"Scaled up ASG {asg_name} to {new_capacity}")
                    
                    # Update session status
                    sessions_db.update_item(
                        {"session_id": session_id},
                        {
                            "status": SessionStatus.PROVISIONING,
                            "updated_at": now,
                            "provisioning_note": "Waiting for new instance from ASG",
                        }
                    )
                    
                    return success_response(
                        {
                            "session_id": session_id,
                            "status": SessionStatus.PROVISIONING,
                            "message": "New instance is being provisioned. Please poll for status.",
                            "poll_interval_seconds": 10,
                            "created_at": now,
                            "expires_at": expires_at,
                        },
                        "Session created, instance provisioning"
                    )
            else:
                # At max capacity
                sessions_db.update_item(
                    {"session_id": session_id},
                    {
                        "status": SessionStatus.ERROR,
                        "error": "No instances available and at max capacity",
                        "updated_at": now,
                    }
                )
                return error_response(503, "No instances available. Please try again later.")
        
        # Build connection info
        connection_info = {}
        if instance_ip:
            # Use PUBLIC URL for student-facing links
            guac_public_url = get_guacamole_public_url()
            
            connection_info = {
                "type": "rdp",
                "guacamole_url": guac_public_url,
                "instance_ip": instance_ip,
                "rdp_port": 3389,
                "vnc_port": 5901,
                "ssh_port": 22,
            }
            
            # Create Guacamole RDP connection
            guac_result = create_guacamole_connection(
                session_id=session_id,
                student_id=student_id,
                student_name=student_name,
                instance_ip=instance_ip,
                course_id=course_id,
            )
            
            if guac_result:
                connection_info.update(guac_result)
                # The direct URL to the RDP session
                connection_info["direct_url"] = guac_result.get("guacamole_connection_url")
            
            # Update session as ready
            sessions_db.update_item(
                {"session_id": session_id},
                {
                    "status": SessionStatus.READY,
                    "instance_id": instance_id,
                    "instance_ip": instance_ip,
                    "connection_info": connection_info,
                    "updated_at": now,
                }
            )
            
            return success_response(
                {
                    "session_id": session_id,
                    "status": SessionStatus.READY,
                    "instance_id": instance_id,
                    "connection_info": connection_info,
                    "created_at": now,
                    "expires_at": expires_at,
                },
                "Session created and ready"
            )
        else:
            # Instance is starting, return provisioning status
            sessions_db.update_item(
                {"session_id": session_id},
                {
                    "status": SessionStatus.PROVISIONING,
                    "instance_id": instance_id,
                    "updated_at": now,
                }
            )
            
            return success_response(
                {
                    "session_id": session_id,
                    "status": SessionStatus.PROVISIONING,
                    "instance_id": instance_id,
                    "message": "Instance is starting. Please poll for status.",
                    "poll_interval_seconds": 10,
                    "created_at": now,
                    "expires_at": expires_at,
                },
                "Session created, instance starting"
            )
    
    except Exception as e:
        logger.exception("Error creating session")
        return error_response(500, "Internal server error", str(e))
