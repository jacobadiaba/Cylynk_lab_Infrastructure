# Role-Based Session Quotas - Deployment Guide

## Overview

This implementation adds monthly usage quotas for AttackBox sessions based on Moodle user roles:

- **Freemium**: 5 hours/month
- **Starter**: 15 hours/month
- **Pro**: Unlimited

## What Was Implemented

### ✅ Backend Infrastructure (Completed)

1. **DynamoDB Usage Table** - Tracks monthly usage per user
2. **Quota Enforcement** - Blocks session creation when quota exceeded
3. **Usage Tracking** - Records session duration on termination
4. **GET /usage API** - Returns user's usage statistics
5. **Expired Session Tracking** - Pool manager tracks usage for crashed sessions

### ✅ Moodle Plugin (Completed)

1. **get_usage.php** - AJAX endpoint to fetch usage from orchestrator
2. **launcher.js** - Updated with usage display and quota error handling
3. **styles.css** - Added usage badge styles with color coding

## Deployment Steps

### Step 1: Build Lambda Packages

```bash
cd modules/orchestrator/scripts
chmod +x build-lambdas.sh
./build-lambdas.sh
```

This creates `.zip` files in `modules/orchestrator/lambda/packages/`:

- `create-session.zip`
- `terminate-session.zip`
- `pool-manager.zip`
- `get-usage.zip`
- `common.zip` (layer)

### Step 2: Deploy Infrastructure

```bash
cd environments/dev  # or environments/prod

# Review changes
terraform plan

# Apply changes
terraform apply
```

**New Resources Created:**

- DynamoDB table: `{project}-{env}-usage`
- Lambda function: `{project}-{env}-get-usage`
- API Gateway routes: `GET /usage` and `GET /usage/{userId}`

### Step 3: Update Moodle Plugin

**Option A: Manual Upload**

1. Copy `moodle-plugin/local_attackbox/` to your Moodle server
2. Navigate to: Site Administration → Notifications
3. Click "Upgrade Moodle database now"

**Option B: Git Deployment**

```bash
cd /path/to/moodle/local/
git pull  # if you're using git
# or rsync the updated files
```

### Step 4: Configure Plugin Settings

In Moodle Admin Panel:

1. Go to: **Site Administration → Plugins → Local plugins → AttackBox Launcher**
2. Update these settings:
   - **API URL**: Your orchestrator API endpoint (from Terraform output)
   - **HMAC Secret**: Shared secret for token signing
   - **API Key**: Authentication key for orchestrator

### Step 5: Compile JavaScript (Moodle)

The launcher.js needs to be compiled:

```bash
# On your Moodle server
cd /path/to/moodle
php admin/cli/purge_caches.php

# If using Grunt (for AMD modules)
grunt amd --root=local/attackbox
```

**Or** use Moodle's built-in AMD compilation:

1. Enable **Developer → Debugging** mode
2. Visit any Moodle page
3. JavaScript will auto-compile on first load

### Step 6: Test the Implementation

#### Test 1: Usage Display

1. Log in to Moodle as a student
2. You should see a usage badge above the AttackBox button
3. Verify it shows: `[Plan]: Xh / Yh (Zh left)`

#### Test 2: Session Launch

1. Click "Launch AttackBox"
2. Session should create normally if quota available
3. Usage badge should update after session ends

#### Test 3: Quota Enforcement

1. Manually set a low quota for testing:
   ```sql
   -- In DynamoDB (via AWS Console)
   -- Create/update usage record
   {
     "user_id": "test_user_123",
     "usage_month": "2025-12",
     "consumed_minutes": 290,
     "quota_minutes": 300,
     "plan": "freemium"
   }
   ```
2. Try to launch AttackBox
3. Should see quota exceeded error with upgrade link

#### Test 4: Usage Tracking

1. Launch AttackBox
2. Use for a few minutes
3. Terminate session
4. Check DynamoDB usage table - consumed_minutes should increase

## Architecture Flow

```
┌─────────────┐
│   Student   │
│   (Moodle)  │
└──────┬──────┘
       │ Click Launch
       ▼
┌─────────────────────────┐
│  Token Generation       │
│  (includes plan+quota)  │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│  create-session Lambda  │
│  ├─ Check usage quota   │
│  ├─ If exceeded → 403   │
│  └─ If OK → Create      │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│   AttackBox Running     │
└──────┬──────────────────┘
       │ On terminate
       ▼
┌─────────────────────────┐
│ terminate-session Lambda│
│  └─ Record duration     │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│   DynamoDB Usage Table  │
│  (consumed_minutes++)   │
└─────────────────────────┘
```

## Monitoring & Troubleshooting

### CloudWatch Logs

Check Lambda logs for errors:

```bash
# Create session
aws logs tail /aws/lambda/{project}-{env}-create-session --follow

# Terminate session
aws logs tail /aws/lambda/{project}-{env}-terminate-session --follow

# Get usage
aws logs tail /aws/lambda/{project}-{env}-get-usage --follow
```

### DynamoDB Queries

**Check user usage:**

```bash
aws dynamodb get-item \
  --table-name cyberlab-dev-usage \
  --key '{"user_id": {"S": "123"}, "usage_month": {"S": "2025-12"}}'
```

**Scan all usage:**

```bash
aws dynamodb scan --table-name cyberlab-dev-usage
```

### Common Issues

**Issue: Usage badge not showing**

- Check browser console for JavaScript errors
- Verify `get_usage.php` is accessible
- Check API URL is configured correctly

**Issue: Quota not enforced**

- Verify `USAGE_TABLE` env var is set on create-session Lambda
- Check CloudWatch logs for quota check errors
- Ensure token includes `plan` and `quota_minutes`

**Issue: Usage not recorded**

- Check terminate-session Lambda logs
- Verify `USAGE_TABLE` env var is set
- Ensure DynamoDB permissions are correct

## Security Considerations

1. **Token Validation**: HMAC tokens expire after 5 minutes
2. **User Isolation**: Users can only query their own usage
3. **Admin Access**: GET /usage/{userId} requires admin role check (TODO)
4. **TTL Cleanup**: Old usage records auto-delete after 13 months

## Next Steps (Optional Enhancements)

1. **Admin Dashboard**: Create admin UI to view all user usage
2. **Email Notifications**: Alert users when approaching quota limit
3. **Grace Period**: Allow 5-10 extra minutes after limit reached
4. **Payment Integration**: Connect upgrade link to billing system
5. **Usage Reports**: Generate monthly usage reports per plan tier
6. **Nonce Persistence**: Move nonce tracking to DynamoDB/Redis

## Rollback Plan

If issues occur:

```bash
cd environments/dev

# Rollback to previous state
terraform apply -var="create_usage_table=false"

# Or restore from backup
aws dynamodb restore-table-from-backup \
  --target-table-name cyberlab-dev-usage \
  --backup-arn <backup-arn>
```

## Support

For issues or questions:

- Check CloudWatch Logs
- Review DynamoDB usage table
- Inspect browser console for frontend errors
- Verify Terraform outputs match plugin configuration
