"""
Admin Sessions Lambda Function
Handles admin queries for all user sessions.
"""
import json
import os
import boto3
from boto3.dynamodb.conditions import Key, Attr
from decimal import Decimal
import time

dynamodb = boto3.resource('dynamodb')
sessions_table = dynamodb.Table(os.environ['SESSIONS_TABLE_NAME'])


def lambda_handler(event, context):
    """
    Handle admin session queries.
    
    Query Parameters:
    - status: Filter by status (all, active, ready, provisioning, terminated)
    - search: Search by student_id or session_id
    - limit: Maximum number of results (default: 200)
    """
    try:
        # Extract query parameters
        params = event.get('queryStringParameters', {}) or {}
        status_filter = params.get('status', 'all')
        search_query = params.get('search', '').lower()
        limit = int(params.get('limit', '200'))
        
        # Scan the sessions table
        scan_params = {
            'Limit': limit
        }
        
        # Add status filter if not 'all'
        if status_filter and status_filter != 'all':
            scan_params['FilterExpression'] = Attr('status').eq(status_filter)
        
        response = sessions_table.scan(**scan_params)
        sessions = response.get('Items', [])
        
        # Continue scanning if there are more items and limit not reached
        while 'LastEvaluatedKey' in response and len(sessions) < limit:
            scan_params['ExclusiveStartKey'] = response['LastEvaluatedKey']
            response = sessions_table.scan(**scan_params)
            sessions.extend(response.get('Items', []))
        
        # Apply search filter
        if search_query:
            sessions = [
                s for s in sessions
                if search_query in s.get('session_id', '').lower() or
                   search_query in s.get('student_id', '').lower()
            ]
        
        # Sort by created_at (most recent first)
        sessions.sort(key=lambda x: x.get('created_at', 0), reverse=True)
        
        # Limit results
        sessions = sessions[:limit]
        
        # Calculate statistics
        stats = calculate_stats(sessions)
        
        # Convert Decimals to native Python types for JSON serialization
        sessions = json.loads(json.dumps(sessions, default=decimal_default))
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': True,
                'data': {
                    'sessions': sessions,
                    'stats': stats,
                    'total_returned': len(sessions)
                }
            })
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': False,
                'error': 'Internal server error',
                'message': str(e)
            })
        }


def calculate_stats(sessions):
    """Calculate session statistics."""
    stats = {
        'total_sessions': len(sessions),
        'active_count': 0,
        'ready_count': 0,
        'provisioning_count': 0,
        'terminated_count': 0,
        'error_count': 0,
        'instances_in_use': 0,
        'total_instances': 0
    }
    
    instance_ids = set()
    
    for session in sessions:
        status = session.get('status', 'unknown')
        
        if status == 'active':
            stats['active_count'] += 1
        elif status == 'ready':
            stats['ready_count'] += 1
        elif status == 'provisioning':
            stats['provisioning_count'] += 1
        elif status == 'terminated':
            stats['terminated_count'] += 1
        elif status == 'error':
            stats['error_count'] += 1
        
        # Count unique instances in use
        instance_id = session.get('instance_id')
        if instance_id and status in ['active', 'ready', 'provisioning']:
            instance_ids.add(instance_id)
    
    stats['instances_in_use'] = len(instance_ids)
    stats['total_instances'] = stats['instances_in_use']  # This could be enhanced to show pool capacity
    
    return stats


def decimal_default(obj):
    """Convert Decimal to int or float for JSON serialization."""
    if isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        else:
            return float(obj)
    raise TypeError


def get_student_info(student_id):
    """
    Get student information from Moodle or other source.
    This is a placeholder - in production, you might want to:
    - Call Moodle API to get user details
    - Cache student info in DynamoDB
    - Return student name, email, etc.
    """
    # For now, just return the student_id
    # This could be enhanced to fetch real student names
    return {
        'student_id': student_id,
        'student_name': None,
        'email': None
    }
