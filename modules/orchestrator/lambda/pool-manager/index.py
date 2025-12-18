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
            "pools_synced": {},
            "scaling_actions": {},
        }
        
        # 1. Clean up expired sessions (applies to all plans)
        results["expired_sessions_cleaned"] = cleanup_expired_sessions(
            sessions_db, pool_db, ec2_client, now
        )
        
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

