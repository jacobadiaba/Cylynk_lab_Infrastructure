"""
Get Usage Lambda Function

Returns user's monthly AttackBox usage statistics.
Supports both authenticated (token) and direct user_id queries.
"""

import logging
import os
import sys

# Add common layer to path
sys.path.insert(0, "/opt/python")

from utils import (
    UsageTracker,
    error_response,
    get_moodle_token_from_event,
    get_path_parameter,
    success_response,
    verify_moodle_request,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
USAGE_TABLE = os.environ.get("USAGE_TABLE")
MOODLE_WEBHOOK_SECRET = os.environ.get("MOODLE_WEBHOOK_SECRET", "")
REQUIRE_MOODLE_AUTH = os.environ.get("REQUIRE_MOODLE_AUTH", "false").lower() == "true"


def handler(event, context):
    """
    Main handler for get usage requests.
    
    Routes:
    - GET /usage - Get usage for authenticated user (from token)
    - GET /usage/{userId} - Get usage for specific user (requires admin)
    
    Returns:
    {
        "user_id": "user123",
        "usage_month": "2025-12",
        "plan": "starter",
        "quota_minutes": 900,
        "consumed_minutes": 450,
        "remaining_minutes": 450,
        "session_count": 8,
        "resets_at": "2026-01-01T00:00:00Z"
    }
    """
    logger.info(f"Get usage request: {event}")
    
    try:
        if not USAGE_TABLE:
            return error_response(503, "Usage tracking not configured")
        
        # Try to get user_id from path parameter (admin query)
        path_user_id = get_path_parameter(event, "userId")
        
        # Try to verify Moodle token
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
        
        # Determine which user's usage to query
        if path_user_id:
            # Admin query for specific user
            # TODO: Add admin role check here
            user_id = path_user_id
            logger.info(f"Admin querying usage for user: {user_id}")
        elif token_payload:
            # User querying their own usage
            user_id = token_payload.get("user_id")
            if not user_id:
                return error_response(400, "Invalid token: missing user_id")
        else:
            return error_response(400, "Missing user_id")
        
        # Get plan info from token or use defaults
        plan = "freemium"
        quota_minutes = 300  # Default freemium quota
        
        if token_payload:
            plan = token_payload.get("plan", "freemium")
            quota_minutes = token_payload.get("quota_minutes", 300)
            try:
                quota_minutes = int(quota_minutes)
            except (TypeError, ValueError):
                quota_minutes = 300
        
        # Query usage
        usage_tracker = UsageTracker(USAGE_TABLE)
        usage_stats = usage_tracker.get_usage_stats(user_id, plan, quota_minutes)
        
        return success_response(usage_stats, "Usage statistics retrieved")
    
    except Exception as e:
        logger.exception("Error getting usage")
        return error_response(500, "Internal server error", str(e))
