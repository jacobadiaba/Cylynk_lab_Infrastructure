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
ASG_NAME = os.environ.get("ASG_NAME")
GUACAMOLE_PRIVATE_IP = os.environ.get("GUACAMOLE_PRIVATE_IP", "")
GUACAMOLE_PUBLIC_IP = os.environ.get("GUACAMOLE_PUBLIC_IP", "")
GUACAMOLE_API_URL = os.environ.get("GUACAMOLE_API_URL", "")
GUACAMOLE_ADMIN_USER = os.environ.get("GUACAMOLE_ADMIN_USER", "guacadmin")
GUACAMOLE_ADMIN_PASS = os.environ.get("GUACAMOLE_ADMIN_PASS", "guacadmin")
SESSION_TTL_HOURS = int(os.environ.get("SESSION_TTL_HOURS", "4"))
MAX_SESSIONS = int(os.environ.get("MAX_SESSIONS", "1"))
USAGE_TABLE = os.environ.get("USAGE_TABLE")

# Moodle authentication
MOODLE_WEBHOOK_SECRET = os.environ.get("MOODLE_WEBHOOK_SECRET", "")
REQUIRE_MOODLE_AUTH = os.environ.get("REQUIRE_MOODLE_AUTH", "false").lower() == "true"

# RDP connection defaults (can be overridden via request)
RDP_USERNAME = os.environ.get("RDP_USERNAME", "kali")
RDP_PASSWORD = os.environ.get("RDP_PASSWORD", "kali")


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
            # Return existing session info
            session = active_sessions[0]
            return success_response(
                {
                    "session_id": session["session_id"],
                    "status": session["status"],
                    "instance_id": session.get("instance_id"),
                    "connection_info": session.get("connection_info", {}),
                    "created_at": session.get("created_at"),
                    "expires_at": session.get("expires_at"),
                    "reused": True,
                },
                "Existing session found"
            )
        
        # Generate new session
        session_id = generate_session_id()
        now = get_current_timestamp()
        expires_at = calculate_expiry(SESSION_TTL_HOURS)
        
        # Create session record in pending state
        session_record = {
            "session_id": session_id,
            "student_id": student_id,
            "student_name": student_name,
            "course_id": course_id,
            "lab_id": lab_id,
            "status": SessionStatus.PENDING,
            "created_at": now,
            "updated_at": now,
            "expires_at": expires_at,
            "metadata": metadata,
        }
        
        if not sessions_db.put_item(session_record):
            return error_response(500, "Failed to create session record")
        
        # Try to find an available instance from the pool
        instance_id = None
        instance_ip = None
        
        # Query available instances
        available_instances = pool_db.query_by_index(
            "StatusIndex", "status", InstanceStatus.AVAILABLE
        )
        
        if available_instances:
            # Use first available instance
            pool_record = available_instances[0]
            instance_id = pool_record["instance_id"]
            
            # Verify instance is actually running
            instance_info = ec2_client.get_instance_status(instance_id)
            if instance_info and instance_info.get("State", {}).get("Name") == "running":
                instance_ip = instance_info.get("PrivateIpAddress")
                
                # Mark instance as assigned
                pool_db.update_item(
                    {"instance_id": instance_id},
                    {
                        "status": InstanceStatus.ASSIGNED,
                        "session_id": session_id,
                        "student_id": student_id,
                        "assigned_at": now,
                    }
                )
                
                # Tag the instance
                ec2_client.tag_instance(instance_id, {
                    "SessionId": session_id,
                    "StudentId": student_id,
                    "AssignedAt": get_iso_timestamp(),
                })
            else:
                # Instance not running, mark as unhealthy
                pool_db.update_item(
                    {"instance_id": instance_id},
                    {"status": InstanceStatus.UNHEALTHY}
                )
                instance_id = None
        
        # If no available instance, check ASG for stopped instances or scale up
        if not instance_id:
            asg_instances = asg_client.get_asg_instances(ASG_NAME)
            
            # Look for stopped instances we can start
            for asg_instance in asg_instances:
                inst_id = asg_instance.get("InstanceId")
                lifecycle_state = asg_instance.get("LifecycleState")
                
                if lifecycle_state == "InService":
                    instance_info = ec2_client.get_instance_status(inst_id)
                    if instance_info:
                        state = instance_info.get("State", {}).get("Name")
                        
                        # Check if this instance is not already assigned
                        pool_record = pool_db.get_item({"instance_id": inst_id})
                        
                        if state == "stopped" and (not pool_record or pool_record.get("status") != InstanceStatus.ASSIGNED):
                            # Start this instance
                            if ec2_client.start_instance(inst_id):
                                instance_id = inst_id
                                
                                # Update/create pool record
                                pool_db.put_item({
                                    "instance_id": inst_id,
                                    "status": InstanceStatus.STARTING,
                                    "session_id": session_id,
                                    "student_id": student_id,
                                    "assigned_at": now,
                                })
                                
                                # Update session to provisioning
                                sessions_db.update_item(
                                    {"session_id": session_id},
                                    {
                                        "status": SessionStatus.PROVISIONING,
                                        "instance_id": inst_id,
                                        "updated_at": now,
                                    }
                                )
                                break
                        
                        elif state == "running" and (not pool_record or pool_record.get("status") == InstanceStatus.AVAILABLE):
                            # Use this running instance
                            instance_id = inst_id
                            instance_ip = instance_info.get("PrivateIpAddress")
                            
                            pool_db.put_item({
                                "instance_id": inst_id,
                                "status": InstanceStatus.ASSIGNED,
                                "session_id": session_id,
                                "student_id": student_id,
                                "assigned_at": now,
                            })
                            break
        
        # If still no instance, request ASG scale up
        if not instance_id:
            capacity = asg_client.get_asg_capacity(ASG_NAME)
            if capacity["desired"] < capacity["max"]:
                new_capacity = capacity["desired"] + 1
                if asg_client.set_desired_capacity(ASG_NAME, new_capacity):
                    logger.info(f"Scaled up ASG to {new_capacity}")
                    
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
