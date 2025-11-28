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
    get_current_timestamp,
    get_iso_timestamp,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
SESSIONS_TABLE = os.environ.get("SESSIONS_TABLE")
INSTANCE_POOL_TABLE = os.environ.get("INSTANCE_POOL_TABLE")
ASG_NAME = os.environ.get("ASG_NAME")
PROJECT_NAME = os.environ.get("PROJECT_NAME", "cyberlab")
ENVIRONMENT = os.environ.get("ENVIRONMENT", "dev")


def handler(event, context):
    """
    Main handler for pool manager.
    
    Triggered by EventBridge schedule (every 5 minutes).
    """
    logger.info(f"Pool manager triggered: {event}")
    
    try:
        # Initialize clients
        sessions_db = DynamoDBClient(SESSIONS_TABLE)
        pool_db = DynamoDBClient(INSTANCE_POOL_TABLE)
        ec2_client = EC2Client()
        asg_client = AutoScalingClient()
        
        now = get_current_timestamp()
        results = {
            "expired_sessions_cleaned": 0,
            "orphaned_instances_released": 0,
            "pool_synced": False,
            "scaling_action": None,
        }
        
        # 1. Clean up expired sessions
        results["expired_sessions_cleaned"] = cleanup_expired_sessions(
            sessions_db, pool_db, ec2_client, now
        )
        
        # 2. Sync instance pool with ASG
        results["pool_synced"] = sync_instance_pool(
            pool_db, ec2_client, asg_client, now
        )
        
        # 3. Release orphaned instances
        results["orphaned_instances_released"] = release_orphaned_instances(
            sessions_db, pool_db, ec2_client, now
        )
        
        # 4. Check if we need to scale
        results["scaling_action"] = manage_scaling(
            sessions_db, pool_db, asg_client
        )
        
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
                
                logger.info(f"Cleaning up expired session: {session_id}")
                
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


def sync_instance_pool(pool_db, ec2_client, asg_client, now: int) -> bool:
    """Sync the instance pool table with actual ASG instances."""
    try:
        # Get all instances in the ASG
        asg_instances = asg_client.get_asg_instances(ASG_NAME)
        asg_instance_ids = {inst["InstanceId"] for inst in asg_instances}
        
        # Get current pool records
        # Note: This is a scan - in production, consider pagination
        pool_records = pool_db.query_by_index("StatusIndex", "status", InstanceStatus.AVAILABLE)
        pool_records.extend(pool_db.query_by_index("StatusIndex", "status", InstanceStatus.ASSIGNED))
        pool_records.extend(pool_db.query_by_index("StatusIndex", "status", InstanceStatus.STARTING))
        
        pool_instance_ids = {rec["instance_id"] for rec in pool_records}
        
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
                        "discovered_at": now,
                        "instance_state": state,
                    })
                    
                    logger.info(f"Added instance to pool: {instance_id} ({pool_status})")
        
        # Remove instances no longer in ASG
        for pool_record in pool_records:
            instance_id = pool_record["instance_id"]
            if instance_id not in asg_instance_ids:
                pool_db.delete_item({"instance_id": instance_id})
                logger.info(f"Removed instance from pool: {instance_id}")
        
        # Update instance states
        for pool_record in pool_records:
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
        logger.error(f"Error syncing instance pool: {e}")
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


def manage_scaling(sessions_db, pool_db, asg_client) -> dict:
    """Check if we need to scale the ASG based on demand."""
    action = {"type": None, "reason": None}
    
    try:
        # Count active sessions
        active_count = 0
        for status in [SessionStatus.PENDING, SessionStatus.PROVISIONING,
                       SessionStatus.READY, SessionStatus.ACTIVE]:
            sessions = sessions_db.query_by_index("StatusIndex", "status", status)
            active_count += len(sessions)
        
        # Count available instances
        available_instances = pool_db.query_by_index("StatusIndex", "status", InstanceStatus.AVAILABLE)
        available_count = len(available_instances)
        
        # Get ASG capacity
        capacity = asg_client.get_asg_capacity(ASG_NAME)
        
        logger.info(f"Scaling check: active_sessions={active_count}, available_instances={available_count}, "
                    f"asg_desired={capacity['desired']}, asg_min={capacity['min']}, asg_max={capacity['max']}")
        
        # Scale up if we have pending sessions but no available instances
        if active_count > 0 and available_count == 0:
            if capacity["desired"] < capacity["max"]:
                new_capacity = min(capacity["desired"] + 1, capacity["max"])
                if asg_client.set_desired_capacity(ASG_NAME, new_capacity):
                    action = {
                        "type": "scale_up",
                        "reason": "No available instances for active sessions",
                        "new_capacity": new_capacity,
                    }
                    logger.info(f"Scaled up ASG to {new_capacity}")
        
        # Scale down if we have too many idle instances
        elif available_count > 2 and active_count == 0:
            # Keep at least min_size
            if capacity["desired"] > capacity["min"]:
                new_capacity = max(capacity["desired"] - 1, capacity["min"])
                if asg_client.set_desired_capacity(ASG_NAME, new_capacity):
                    action = {
                        "type": "scale_down",
                        "reason": "Too many idle instances",
                        "new_capacity": new_capacity,
                    }
                    logger.info(f"Scaled down ASG to {new_capacity}")
        
        return action
    
    except Exception as e:
        logger.error(f"Error managing scaling: {e}")
        return {"type": "error", "reason": str(e)}

