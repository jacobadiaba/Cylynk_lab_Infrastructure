# Admin Dashboard for LynkBox Session Management

This document describes the admin dashboard feature that allows administrators to view and manage all user sessions across the CyberLab infrastructure.

## Overview

The admin dashboard provides a centralized interface for:

- Viewing all active, provisioning, and terminated sessions
- Searching sessions by student ID, name, or session ID
- Filtering sessions by status
- Terminating any user's session
- Real-time session statistics and monitoring

## Components

### 1. Moodle Plugin Frontend (`moodle-plugin/local_attackbox/`)

#### Admin Dashboard Page (`admin_dashboard.php`)

- Main admin interface with session table
- Filters: Status (all/active/ready/provisioning/terminated), Search
- Statistics cards showing total sessions, active count, provisioning count
- Auto-refreshes every 30 seconds

#### Ajax Endpoints

- **`ajax/get_all_sessions.php`**: Fetches all sessions with filtering
  - Parameters: `status`, `search`, `limit`
  - Requires `local/attackbox:managesessions` capability
- **`ajax/admin_terminate_session.php`**: Terminates any user's session
  - Parameters: `sessionId`, `reason` (default: "admin")
  - Requires `local/attackbox:managesessions` capability

#### JavaScript (`amd/src/admin-dashboard.js`)

- Handles session loading and rendering
- Implements filtering and search
- Manages terminate actions with confirmation
- Auto-refresh functionality
- Real-time duration and expiry calculations

### 2. Backend Lambda (`modules/orchestrator/lambda/admin-sessions/`)

#### Admin Sessions Function (`index.py`)

- Scans DynamoDB sessions table
- Filters by status and search query
- Calculates session statistics:
  - Total sessions
  - Active/ready/provisioning/terminated counts
  - Instances in use
- Returns paginated results (default: 200 sessions)

### 3. API Gateway Routes

- **GET `/admin/sessions`**: Get all sessions
  - Query params: `status`, `search`, `limit`
  - Returns: `{success, data: {sessions, stats, total_returned}}`

## Capabilities and Permissions

### New Capability: `local/attackbox:managesessions`

Defined in `moodle-plugin/local_attackbox/db/access.php`:

```php
'local/attackbox:managesessions' => [
    'riskbitmask' => RISK_CONFIG | RISK_DATALOSS,
    'captype' => 'write',
    'contextlevel' => CONTEXT_SYSTEM,
    'archetypes' => [
        'manager' => CAP_ALLOW,
    ],
]
```

**Assigned to:**

- Managers (by default)
- Can be assigned to other roles via Moodle role management

**Allows:**

- Viewing all user sessions
- Terminating any user's session
- Accessing admin dashboard

## Installation

### 1. Build and Deploy Lambda Function

```bash
cd modules/orchestrator
bash scripts/build-lambdas.sh
```

This builds the `admin-sessions.zip` package.

### 2. Deploy Infrastructure

```bash
cd environments/dev  # or prod
terraform init
terraform plan
terraform apply
```

This deploys:

- Admin sessions Lambda function
- API Gateway route: `GET /admin/sessions`
- CloudWatch log group
- IAM permissions

### 3. Compile Moodle JavaScript

The JavaScript needs to be minified for Moodle's AMD loader:

```bash
cd moodle-plugin/local_attackbox

# Using Grunt (if configured)
grunt amd

# Or manually copy to build directory
mkdir -p amd/build
cp amd/src/admin-dashboard.js amd/build/admin-dashboard.min.js
```

### 4. Update Moodle Plugin

1. Copy the plugin files to Moodle:

   ```bash
   cp -r moodle-plugin/local_attackbox /path/to/moodle/local/
   ```

2. Visit Moodle admin notifications to upgrade the plugin:

   ```
   Site administration > Notifications
   ```

3. Clear Moodle caches:
   ```
   Site administration > Development > Purge all caches
   ```

### 5. Assign Permissions

Grant the `local/attackbox:managesessions` capability to appropriate roles:

1. Go to: **Site administration > Users > Permissions > Define roles**
2. Edit the "Manager" role (or create a custom role)
3. Search for "managesessions"
4. Ensure it's set to "Allow"

## Usage

### Accessing the Admin Dashboard

1. Log in as a user with `local/attackbox:managesessions` capability
2. Navigate to:

   ```
   Site administration > Plugins > Local plugins > LynkBox Launcher > Admin Dashboard
   ```

   Or directly via URL:

   ```
   https://your-moodle-site.com/local/attackbox/admin_dashboard.php
   ```

### Dashboard Features

#### Session Statistics

Displays real-time statistics:

- **Total Sessions**: All sessions in the system
- **Active Now**: Currently active sessions
- **Provisioning**: Sessions being created
- **Instances Used**: Number of EC2 instances in use

#### Session Table

Shows all sessions with:

- Session ID (truncated with tooltip)
- Student name and ID
- Status badge (color-coded)
- Instance ID
- Started time (relative, e.g., "5m ago")
- Duration
- Time until expiry
- Terminate button (for active sessions)

#### Filters

- **Status**: All, Active, Ready, Provisioning, Terminated
- **Search**: By session ID, student ID, or student name
- **Refresh**: Manual refresh button
- **Auto-refresh**: Automatically updates every 30 seconds

#### Actions

- **Terminate Session**:
  - Click "Terminate" button
  - Confirm action in dialog
  - Session is immediately terminated
  - Instance is stopped and cleaned up

## API Response Format

### GET `/admin/sessions`

**Request:**

```
GET /admin/sessions?status=active&search=john&limit=100
```

**Response:**

```json
{
  "success": true,
  "data": {
    "sessions": [
      {
        "session_id": "sess_abc123...",
        "student_id": "12345",
        "student_name": "John Doe",
        "status": "active",
        "instance_id": "i-0abc123...",
        "created_at": 1703001600,
        "expires_at": 1703005200,
        "guacamole_url": "https://...",
        "vnc_url": "https://...",
        "rdp_url": "https://..."
      }
    ],
    "stats": {
      "total_sessions": 45,
      "active_count": 12,
      "ready_count": 3,
      "provisioning_count": 2,
      "terminated_count": 28,
      "error_count": 0,
      "instances_in_use": 15,
      "total_instances": 15
    },
    "total_returned": 15
  }
}
```

## Security Considerations

1. **Capability-Based Access**: Only users with `local/attackbox:managesessions` can access the dashboard

2. **Session Key Validation**: All Ajax requests require valid Moodle session key (`sesskey`)

3. **Authentication Token**: Backend API calls use secure JWT tokens with shared secret

4. **Audit Trail**: All termination actions are logged with:

   - Admin user ID
   - Session ID
   - Reason: "admin"
   - Timestamp

5. **CORS**: API endpoints use proper CORS headers for same-origin requests

## Troubleshooting

### Dashboard Not Loading

1. Check CloudWatch logs: `/aws/lambda/{project}-{env}-admin-sessions`
2. Verify Lambda function is deployed
3. Check API Gateway endpoint is accessible
4. Ensure capability is assigned to your role

### Sessions Not Appearing

1. Check DynamoDB table has data
2. Verify Lambda has DynamoDB read permissions
3. Check filter settings (try "All" status)
4. Look for errors in browser console

### Terminate Not Working

1. Verify `terminate-session` Lambda is running
2. Check CloudWatch logs for errors
3. Ensure session ID is valid
4. Check IAM permissions for EC2 and DynamoDB

### JavaScript Not Loading

1. Clear Moodle caches
2. Check `amd/build/admin-dashboard.min.js` exists
3. Verify no JavaScript errors in browser console
4. Check Moodle is in production mode (not developer mode)

## Monitoring

### CloudWatch Metrics

- Lambda invocations
- Lambda duration
- Lambda errors
- API Gateway requests

### CloudWatch Logs

```
/aws/lambda/{project}-{env}-admin-sessions
```

### Key Metrics to Watch

- Number of DynamoDB scan operations (affects costs)
- Lambda execution time (should be < 1s)
- Error rate (should be < 1%)

## Future Enhancements

Potential improvements:

1. **Bulk Actions**: Terminate multiple sessions at once
2. **Session Details**: Detailed view of individual sessions
3. **Reset Instance**: Reset AttackBox to clean state without terminating
4. **Session Logs**: View session activity logs
5. **Usage Charts**: Visualize usage patterns over time
6. **Export Data**: Export session history to CSV
7. **Real-time Updates**: WebSocket for live session updates
8. **Student Info**: Fetch and cache student names from Moodle

## Cost Impact

**Additional Resources:**

- Lambda function: ~$0.20/month (assuming 1000 admin views/month)
- API Gateway: ~$3.50/month (1000 requests)
- DynamoDB scans: Included in free tier or ~$1.25/1M reads

**Total additional cost:** ~$5/month

## Related Documentation

- [Main README](README.md)
- [Cost Optimization](COST_OPTIMIZATION_IMPLEMENTATION.md)
- [Deployment Guide](environments/dev/README.md)
- [Moodle Plugin Development](moodle-plugin/local_attackbox/README.md)
