"""
Pool Manager Lambda Function

Scheduled function that:
1. Cleans up expired sessions
2. Syncs instance pool state with actual EC2 instances
3. Manages ASG scaling based on demand
4. Releases orphaned instances
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
    get_current_timestamp,
    get_iso_timestamp,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
SESSIONS_TABLE = os.environ.get("SESSIONS_TABLE")
INSTANCE_POOL_TABLE = os.environ.get("INSTANCE_POOL_TABLE")
USAGE_TABLE = os.environ.get("USAGE_TABLE")
PROJECT_NAME = os.environ.get("PROJECT_NAME", "cyberlab")
ENVIRONMENT = os.environ.get("ENVIRONMENT", "dev")

# Idle detection configuration
ENABLE_IDLE_DETECTION = os.environ.get("ENABLE_IDLE_DETECTION", "true").lower() == "true"
IDLE_HEARTBEAT_GRACE_PERIOD = int(os.environ.get("IDLE_HEARTBEAT_GRACE_PERIOD", "120"))  # 2 min grace

# Guacamole configuration for activity checking
GUACAMOLE_PRIVATE_IP = os.environ.get("GUACAMOLE_PRIVATE_IP", "")
GUACAMOLE_PUBLIC_IP = os.environ.get("GUACAMOLE_PUBLIC_IP", "")
GUACAMOLE_API_URL = os.environ.get("GUACAMOLE_API_URL", "")
GUACAMOLE_ADMIN_USER = os.environ.get("GUACAMOLE_ADMIN_USER", "guacadmin")
GUACAMOLE_ADMIN_PASS = os.environ.get("GUACAMOLE_ADMIN_PASS", "guacadmin")

# Tier-specific idle thresholds (seconds)
IDLE_THRESHOLDS = {
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

# Multi-tier ASG configuration
ASG_NAME_FREEMIUM = os.environ.get("ASG_NAME_FREEMIUM", "")
ASG_NAME_STARTER = os.environ.get("ASG_NAME_STARTER", "")
ASG_NAME_PRO = os.environ.get("ASG_NAME_PRO", "")

# Map plan tiers to ASG names
PLAN_ASG_MAP = {
    "freemium": ASG_NAME_FREEMIUM,
    "starter": ASG_NAME_STARTER,
    "pro": ASG_NAME_PRO,
}

# Get all configured ASGs (filter out empty ones)
def get_configured_asgs():
    """Get list of configured ASG names with their plan tiers."""
    return {plan: asg for plan, asg in PLAN_ASG_MAP.items() if asg}


def handler(event, context):
    """
    Main handler for pool manager.
    
    Triggered by EventBridge schedule (every 1 minute).
    Manages all tier-based pools (freemium, starter, pro).
    """
    logger.info(f"Pool manager triggered: {event}")
    
    try:
        # Initialize clients
        sessions_db = DynamoDBClient(SESSIONS_TABLE)
        pool_db = DynamoDBClient(INSTANCE_POOL_TABLE)
        ec2_client = EC2Client()
        asg_client = AutoScalingClient()
        
        now = get_current_timestamp()
        
        # Get configured ASGs
        configured_asgs = get_configured_asgs()
        logger.info(f"Managing pools: {list(configured_asgs.keys())}")
        
        results = {
            "expired_sessions_cleaned": 0,
            "orphaned_instances_released": 0,
            "idle_sessions_warned": 0,
            "idle_sessions_terminated": 0,
            "pools_synced": {},
            "scaling_actions": {},
        }
        
        # 1. Clean up expired sessions (applies to all plans)
        results["expired_sessions_cleaned"] = cleanup_expired_sessions(
            sessions_db, pool_db, ec2_client, now
        )
        
        # 1.5. Check for idle sessions and handle warnings/termination
        if ENABLE_IDLE_DETECTION:
            idle_results = check_idle_sessions(sessions_db, pool_db, ec2_client, now)
            results["idle_sessions_warned"] = idle_results.get("warned", 0)
            results["idle_sessions_terminated"] = idle_results.get("terminated", 0)
        
        # 2. Sync instance pool with ASGs (for each tier)
        for plan, asg_name in configured_asgs.items():
            synced = sync_instance_pool_for_plan(
                pool_db, ec2_client, asg_client, now, plan, asg_name
            )
            results["pools_synced"][plan] = synced
        
        # 3. Release orphaned instances (applies to all plans)
        results["orphaned_instances_released"] = release_orphaned_instances(
            sessions_db, pool_db, ec2_client, now
        )
        
        # 4. Check if we need to scale (for each tier)
        for plan, asg_name in configured_asgs.items():
            action = manage_scaling_for_plan(
                sessions_db, pool_db, asg_client, plan, asg_name
            )
            results["scaling_actions"][plan] = action
        
        logger.info(f"Pool manager completed: {results}")
        
        return {
            "statusCode": 200,
            "body": results,
        }
    
    except Exception as e:
        logger.exception("Error in pool manager")
        return {
            "statusCode": 500,
            "body": {"error": str(e)},
        }


def cleanup_expired_sessions(sessions_db, pool_db, ec2_client, now: int) -> int:
    """Clean up sessions that have expired."""
    cleaned = 0
    usage_tracker = UsageTracker(USAGE_TABLE) if USAGE_TABLE else None
    
    # Query active sessions and check expiry
    # Note: In production, you'd want a GSI on status or use DynamoDB Streams
    for status in [SessionStatus.PENDING, SessionStatus.PROVISIONING, 
                   SessionStatus.READY, SessionStatus.ACTIVE]:
        sessions = sessions_db.query_by_index("StatusIndex", "status", status)
        
        for session in sessions:
            expires_at = session.get("expires_at", 0)
            
            if expires_at and now > expires_at:
                session_id = session["session_id"]
                instance_id = session.get("instance_id")
                student_id = session.get("student_id")
                created_at = session.get("created_at", now)
                
                logger.info(f"Cleaning up expired session: {session_id}")
                
                # Track usage before terminating
                if usage_tracker and student_id:
                    duration_minutes = (now - created_at) / 60
                    if duration_minutes >= 0.5:  # At least 30 seconds
                        try:
                            usage_tracker.record_usage(
                                user_id=student_id,
                                minutes=int(duration_minutes)
                            )
                            logger.info(f"Recorded {int(duration_minutes)} minutes for expired session {session_id}")
                        except Exception as e:
                            logger.error(f"Failed to record usage for expired session: {e}")
                
                # Update session status
                sessions_db.update_item(
                    {"session_id": session_id},
                    {
                        "status": SessionStatus.TERMINATED,
                        "termination_reason": "expired",
                        "terminated_at": now,
                        "updated_at": now,
                    }
                )
                
                # Release instance
                if instance_id:
                    pool_db.update_item(
                        {"instance_id": instance_id},
                        {
                            "status": InstanceStatus.AVAILABLE,
                            "session_id": None,
                            "student_id": None,
                            "released_at": now,
                        }
                    )
                    
                    # Clear instance tags
                    ec2_client.tag_instance(instance_id, {
                        "SessionId": "",
                        "StudentId": "",
                        "ReleasedAt": get_iso_timestamp(),
                    })
                
                cleaned += 1
    
    return cleaned


def get_guacamole_internal_url() -> str:
    """Get the internal Guacamole URL for API calls."""
    if GUACAMOLE_API_URL:
        return GUACAMOLE_API_URL
    if GUACAMOLE_PUBLIC_IP:
        return f"https://{GUACAMOLE_PUBLIC_IP}/guacamole"
    if GUACAMOLE_PRIVATE_IP:
        return f"https://{GUACAMOLE_PRIVATE_IP}/guacamole"
    return ""


def check_guacamole_activity_for_sessions(sessions: list) -> dict:
    """
    Check Guacamole for active connections across multiple sessions.
    Returns a dict mapping connection_id to activity info.
    """
    internal_url = get_guacamole_internal_url()
    if not internal_url:
        return {}
    
    try:
        guac = GuacamoleClient(
            base_url=internal_url,
            username=GUACAMOLE_ADMIN_USER,
            password=GUACAMOLE_ADMIN_PASS,
        )
        
        # Get all active connections at once (more efficient)
        active_connections = guac.get_all_active_connections()
        return active_connections
        
    except Exception as e:
        logger.warning(f"Error checking Guacamole activity: {e}")
        return {}


def check_idle_sessions(sessions_db, pool_db, ec2_client, now: int) -> dict:
    """
    Check for idle sessions and handle warnings/termination.
    
    This function:
    1. Queries active sessions
    2. Checks Guacamole for actual connection activity
    3. Compares last_active_at with thresholds
    4. Updates sessions that are idle
    5. Terminates sessions that exceed termination threshold
    
    Returns dict with warned and terminated counts.
    """
    results = {"warned": 0, "terminated": 0}
    usage_tracker = UsageTracker(USAGE_TABLE) if USAGE_TABLE else None
    
    # Get all active sessions
    active_sessions = []
    for status in [SessionStatus.READY, SessionStatus.ACTIVE]:
        sessions = sessions_db.query_by_index("StatusIndex", "status", status)
        active_sessions.extend(sessions)
    
    if not active_sessions:
        return results
    
    logger.info(f"Checking {len(active_sessions)} sessions for idle status")
    
    # Get Guacamole activity for all connections at once
    guac_activity = check_guacamole_activity_for_sessions(active_sessions)
    
    for session in active_sessions:
        session_id = session["session_id"]
        student_id = session.get("student_id")
        instance_id = session.get("instance_id")
        created_at = session.get("created_at", now)
        last_active_at = session.get("last_active_at", created_at)
        last_heartbeat_at = session.get("last_heartbeat_at", 0)
        idle_warning_sent_at = session.get("idle_warning_sent_at")
        focus_mode = session.get("focus_mode", False)
        plan = session.get("plan", "freemium")
        
        # Skip if focus mode is enabled (user opted out of idle termination)
        if focus_mode:
            logger.debug(f"Session {session_id} has focus mode enabled, skipping idle check")
            continue
        
        # Check Guacamole activity for this session's connection
        connection_info = session.get("connection_info", {})
        guac_connection_id = connection_info.get("guacamole_connection_id")
        
        guac_connected = False
        guac_last_activity = 0
        
        if guac_connection_id and guac_connection_id in guac_activity:
            conn_activity = guac_activity[guac_connection_id]
            guac_connected = conn_activity.get("total_connections", 0) > 0
            
            # Try to get last activity timestamp from active sessions
            for active_session in conn_activity.get("active_sessions", []):
                start_date = active_session.get("start_date")
                if start_date:
                    try:
                        ts = int(start_date) // 1000
                        if ts > guac_last_activity:
                            guac_last_activity = ts
                    except (ValueError, TypeError):
                        pass
        
        # Determine effective last activity time
        # Use the most recent of: last_active_at, last_heartbeat_at, guac_last_activity
        effective_last_active = max(last_active_at, last_heartbeat_at, guac_last_activity)
        
        # If Guacamole shows active connection, consider the session active
        if guac_connected:
            # User is connected, update activity timestamp
            if effective_last_active < now - IDLE_HEARTBEAT_GRACE_PERIOD:
                effective_last_active = now
        
        # Calculate idle time
        idle_seconds = now - effective_last_active
        
        # Get thresholds for this plan
        plan_thresholds = IDLE_THRESHOLDS.get(plan, IDLE_THRESHOLDS["freemium"])
        warning_threshold = plan_thresholds["warning"]
        termination_threshold = plan_thresholds["termination"]
        
        logger.debug(f"Session {session_id}: idle={idle_seconds}s, warning={warning_threshold}s, "
                    f"terminate={termination_threshold}s, guac_connected={guac_connected}")
        
        # Check if session should be terminated
        if idle_seconds >= termination_threshold:
            logger.info(f"Terminating idle session {session_id} (idle for {idle_seconds}s, threshold={termination_threshold}s)")
            
            # Track usage before terminating
            if usage_tracker and student_id:
                duration_minutes = (now - created_at) / 60
                if duration_minutes >= 0.5:
                    try:
                        usage_tracker.record_usage(
                            user_id=student_id,
                            minutes=int(duration_minutes)
                        )
                        logger.info(f"Recorded {int(duration_minutes)} minutes for idle-terminated session")
                    except Exception as e:
                        logger.error(f"Failed to record usage: {e}")
            
            # Update session status
            sessions_db.update_item(
                {"session_id": session_id},
                {
                    "status": SessionStatus.TERMINATED,
                    "termination_reason": "idle_timeout",
                    "terminated_at": now,
                    "updated_at": now,
                    "idle_seconds_at_termination": idle_seconds,
                }
            )
            
            # Release instance back to pool
            if instance_id:
                pool_db.update_item(
                    {"instance_id": instance_id},
                    {
                        "status": InstanceStatus.AVAILABLE,
                        "session_id": None,
                        "student_id": None,
                        "released_at": now,
                    }
                )
                
                ec2_client.tag_instance(instance_id, {
                    "SessionId": "",
                    "StudentId": "",
                    "ReleasedAt": get_iso_timestamp(),
                    "TerminationReason": "idle_timeout",
                })
            
            results["terminated"] += 1
            
        # Check if warning should be sent/updated
        elif idle_seconds >= warning_threshold:
            if not idle_warning_sent_at:
                logger.info(f"Session {session_id} entering idle warning state (idle for {idle_seconds}s)")
                
                sessions_db.update_item(
                    {"session_id": session_id},
                    {
                        "idle_warning_sent_at": now,
                        "idle_seconds": idle_seconds,
                        "updated_at": now,
                    }
                )
                
                results["warned"] += 1
        
        # Clear warning if session became active again
        elif idle_warning_sent_at and idle_seconds < warning_threshold:
            logger.info(f"Session {session_id} became active, clearing idle warning")
            
            sessions_db.update_item(
                {"session_id": session_id},
                {
                    "idle_warning_sent_at": None,
                    "last_active_at": effective_last_active,
                    "updated_at": now,
                }
            )
    
    return results


def sync_instance_pool_for_plan(pool_db, ec2_client, asg_client, now: int, plan: str, asg_name: str) -> bool:
    """Sync the instance pool table with actual ASG instances for a specific plan."""
    try:
        logger.info(f"Syncing pool for plan '{plan}' with ASG '{asg_name}'")
        
        # Get all instances in the ASG
        asg_instances = asg_client.get_asg_instances(asg_name)
        asg_instance_ids = {inst["InstanceId"] for inst in asg_instances}
        
        # Get current pool records for this plan
        all_pool_records = []
        for status in [InstanceStatus.AVAILABLE, InstanceStatus.ASSIGNED, InstanceStatus.STARTING]:
            records = pool_db.query_by_index("StatusIndex", "status", status)
            # Filter by plan (default to "pro" for backward compatibility)
            plan_records = [r for r in records if r.get("plan", "pro") == plan]
            all_pool_records.extend(plan_records)
        
        pool_instance_ids = {rec["instance_id"] for rec in all_pool_records}
        
        # Add new instances to pool
        for asg_instance in asg_instances:
            instance_id = asg_instance["InstanceId"]
            lifecycle_state = asg_instance.get("LifecycleState")
            
            if instance_id not in pool_instance_ids and lifecycle_state == "InService":
                # Get instance details
                instance_info = ec2_client.get_instance_status(instance_id)
                if instance_info:
                    state = instance_info.get("State", {}).get("Name")
                    
                    pool_status = InstanceStatus.AVAILABLE
                    if state == "pending":
                        pool_status = InstanceStatus.STARTING
                    elif state == "stopped":
                        pool_status = InstanceStatus.AVAILABLE
                    elif state == "running":
                        pool_status = InstanceStatus.AVAILABLE
                    
                    pool_db.put_item({
                        "instance_id": instance_id,
                        "status": pool_status,
                        "plan": plan,  # Store plan tier
                        "discovered_at": now,
                        "instance_state": state,
                    })
                    
                    logger.info(f"Added instance to {plan} pool: {instance_id} ({pool_status})")
        
        # Remove instances no longer in ASG
        for pool_record in all_pool_records:
            instance_id = pool_record["instance_id"]
            if instance_id not in asg_instance_ids:
                pool_db.delete_item({"instance_id": instance_id})
                logger.info(f"Removed instance from {plan} pool: {instance_id}")
        
        # Update instance states
        for pool_record in all_pool_records:
            instance_id = pool_record["instance_id"]
            if instance_id in asg_instance_ids:
                instance_info = ec2_client.get_instance_status(instance_id)
                if instance_info:
                    state = instance_info.get("State", {}).get("Name")
                    current_status = pool_record.get("status")
                    
                    # Update status based on actual state
                    new_status = current_status
                    if state == "running" and current_status == InstanceStatus.STARTING:
                        new_status = InstanceStatus.AVAILABLE
                    elif state == "stopped" and current_status not in [InstanceStatus.ASSIGNED]:
                        new_status = InstanceStatus.AVAILABLE
                    
                    if new_status != current_status:
                        pool_db.update_item(
                            {"instance_id": instance_id},
                            {
                                "status": new_status,
                                "instance_state": state,
                                "updated_at": now,
                            }
                        )
        
        return True
    
    except Exception as e:
        logger.error(f"Error syncing instance pool for plan {plan}: {e}")
        return False


def release_orphaned_instances(sessions_db, pool_db, ec2_client, now: int) -> int:
    """Release instances that are assigned but have no active session."""
    released = 0
    
    # Get assigned instances
    assigned_instances = pool_db.query_by_index("StatusIndex", "status", InstanceStatus.ASSIGNED)
    
    for pool_record in assigned_instances:
        instance_id = pool_record["instance_id"]
        session_id = pool_record.get("session_id")
        assigned_at = pool_record.get("assigned_at", 0)
        
        # Check if session exists and is active
        is_orphaned = False
        
        if not session_id:
            is_orphaned = True
        else:
            session = sessions_db.get_item({"session_id": session_id})
            if not session:
                is_orphaned = True
            elif session.get("status") in [SessionStatus.TERMINATED, SessionStatus.ERROR]:
                is_orphaned = True
        
        # Also check for stale assignments (assigned > 1 hour with no session update)
        if not is_orphaned and assigned_at:
            if now - assigned_at > 3600:  # 1 hour
                session = sessions_db.get_item({"session_id": session_id}) if session_id else None
                if session:
                    updated_at = session.get("updated_at", 0)
                    if now - updated_at > 3600:
                        is_orphaned = True
                        logger.info(f"Instance {instance_id} appears stale (no session activity)")
        
        if is_orphaned:
            logger.info(f"Releasing orphaned instance: {instance_id}")
            
            pool_db.update_item(
                {"instance_id": instance_id},
                {
                    "status": InstanceStatus.AVAILABLE,
                    "session_id": None,
                    "student_id": None,
                    "released_at": now,
                }
            )
            
            # Clear tags
            ec2_client.tag_instance(instance_id, {
                "SessionId": "",
                "StudentId": "",
                "ReleasedAt": get_iso_timestamp(),
            })
            
            released += 1
    
    return released


def manage_scaling_for_plan(sessions_db, pool_db, asg_client, plan: str, asg_name: str) -> dict:
    """Check if we need to scale the ASG based on demand for a specific plan."""
    action = {"type": None, "reason": None, "plan": plan}
    
    try:
        # Count active sessions for this plan
        active_count = 0
        for status in [SessionStatus.PENDING, SessionStatus.PROVISIONING,
                       SessionStatus.READY, SessionStatus.ACTIVE]:
            sessions = sessions_db.query_by_index("StatusIndex", "status", status)
            # Filter by plan (default to "pro" for backward compatibility)
            plan_sessions = [s for s in sessions if s.get("plan", "pro") == plan]
            active_count += len(plan_sessions)
        
        # Count available instances for this plan
        available_instances = pool_db.query_by_index("StatusIndex", "status", InstanceStatus.AVAILABLE)
        available_count = len([i for i in available_instances if i.get("plan", "pro") == plan])
        
        # Count instances that are already starting for this plan
        starting_instances = pool_db.query_by_index("StatusIndex", "status", InstanceStatus.STARTING)
        starting_count = len([i for i in starting_instances if i.get("plan", "pro") == plan])
        
        # Count assigned instances for this plan
        assigned_instances = pool_db.query_by_index("StatusIndex", "status", InstanceStatus.ASSIGNED)
        assigned_count = len([i for i in assigned_instances if i.get("plan", "pro") == plan])
        
        # Get ASG capacity
        capacity = asg_client.get_asg_capacity(asg_name)
        
        logger.info(f"[{plan}] Scaling check: active_sessions={active_count}, available={available_count}, "
                    f"starting={starting_count}, assigned={assigned_count}, "
                    f"asg_desired={capacity['desired']}, asg_min={capacity['min']}, asg_max={capacity['max']}")
        
        # Calculate how many instances are "in progress" (either available, starting, or assigned)
        instances_in_progress = available_count + starting_count + assigned_count
        
        # Scale up only if we have more active sessions than instances that can serve them
        # AND there are no instances currently starting (to prevent duplicate scale-ups)
        if active_count > instances_in_progress and starting_count == 0:
            if capacity["desired"] < capacity["max"]:
                # Scale up by the deficit, but at most 2 at a time to avoid over-provisioning
                deficit = active_count - instances_in_progress
                scale_amount = min(deficit, 2)
                new_capacity = min(capacity["desired"] + scale_amount, capacity["max"])
                if asg_client.set_desired_capacity(asg_name, new_capacity):
                    action = {
                        "type": "scale_up",
                        "plan": plan,
                        "reason": f"Active sessions ({active_count}) > instances in progress ({instances_in_progress})",
                        "new_capacity": new_capacity,
                    }
                    logger.info(f"[{plan}] Scaled up ASG {asg_name} to {new_capacity}")
        
        # Scale down if we have too many idle instances and no active sessions
        elif available_count > 2 and active_count == 0:
            # Keep at least min_size
            if capacity["desired"] > capacity["min"]:
                new_capacity = max(capacity["desired"] - 1, capacity["min"])
                if asg_client.set_desired_capacity(asg_name, new_capacity):
                    action = {
                        "type": "scale_down",
                        "plan": plan,
                        "reason": "Too many idle instances",
                        "new_capacity": new_capacity,
                    }
                    logger.info(f"[{plan}] Scaled down ASG {asg_name} to {new_capacity}")
        
        return action
    
    except Exception as e:
        logger.error(f"Error managing scaling for plan {plan}: {e}")
        return {"type": "error", "plan": plan, "reason": str(e)}

