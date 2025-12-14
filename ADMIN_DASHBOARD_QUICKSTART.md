# Admin Dashboard - Quick Deployment Guide

This guide will help you deploy the admin dashboard feature in under 10 minutes.

## Prerequisites

- Terraform installed
- AWS credentials configured
- Access to Moodle server
- Manager role in Moodle

## Step 1: Build Lambda Function (2 minutes)

```bash
cd modules/orchestrator
bash scripts/build-lambdas.sh
```

This creates `lambda/packages/admin-sessions.zip`.

## Step 2: Deploy Infrastructure (3 minutes)

```bash
cd environments/dev  # or prod

# Review changes
terraform plan

# Deploy
terraform apply -auto-approve
```

**What gets deployed:**

- Admin sessions Lambda function
- API Gateway route: `GET /admin/sessions`
- CloudWatch log group
- Lambda permissions

## Step 3: Update Moodle Plugin (3 minutes)

### Option A: Copy Files (Recommended)

```bash
# From cyberlab-infrastructure directory
cp -r moodle-plugin/local_attackbox/* /path/to/moodle/local/attackbox/
```

### Option B: Upload via Moodle UI

1. Zip the plugin:

   ```bash
   cd moodle-plugin
   zip -r attackbox.zip local_attackbox/
   ```

2. Upload via Moodle:
   - Site administration > Plugins > Install plugins
   - Upload `attackbox.zip`
   - Follow prompts

### Upgrade Database

1. Visit: **Site administration > Notifications**
2. Click "Upgrade Moodle database now"
3. Wait for completion

### Clear Caches

```bash
# Via CLI (recommended)
php admin/cli/purge_caches.php

# Or via UI
# Site administration > Development > Purge all caches
```

## Step 4: Verify Installation (2 minutes)

### Check Capability

1. Go to: **Site administration > Users > Permissions > Define roles**
2. Click "Manager"
3. Search for "managesessions"
4. Should see: `local/attackbox:managesessions` with "Allow" checkbox

### Access Dashboard

1. Log in as a manager
2. Go to: **Site administration > Plugins > Local plugins > LynkBox Launcher**
3. You should see "Admin Dashboard" link

Or directly:

```
https://your-moodle-site.com/local/attackbox/admin_dashboard.php
```

### Test Functionality

1. Dashboard loads with session table
2. Statistics cards show data
3. Filters work (status, search)
4. Sessions are displayed
5. Terminate button appears for active sessions

## Troubleshooting

### Dashboard Returns 404

**Solution:** Check you have the capability:

```sql
-- Run in Moodle database
SELECT * FROM mdl_capabilities WHERE name = 'local/attackbox:managesessions';
```

If empty, run database upgrade again.

### No Sessions Displayed

**Check Lambda logs:**

```bash
aws logs tail /aws/lambda/cyberlab-dev-admin-sessions --follow
```

**Check API endpoint:**

```bash
curl https://your-api-gateway-url.execute-api.region.amazonaws.com/admin/sessions
```

### JavaScript Errors

**Clear browser cache and reload:**

- Chrome/Edge: `Ctrl+Shift+Delete`
- Firefox: `Ctrl+Shift+Delete`
- Safari: `Cmd+Option+E`

**Check console for errors:**

- Press `F12`
- Go to Console tab
- Look for red errors

### Permission Denied

**Grant capability manually:**

1. Site administration > Users > Permissions > Assign system roles
2. Click "Manager"
3. Add your user

## Post-Deployment Checklist

- [ ] Lambda function deployed and running
- [ ] API Gateway route accessible
- [ ] Moodle plugin updated
- [ ] Database upgraded
- [ ] Caches cleared
- [ ] Capability assigned to managers
- [ ] Dashboard accessible
- [ ] Sessions displayed correctly
- [ ] Terminate function works
- [ ] Filters and search work
- [ ] Auto-refresh working

## Configuration

### Adjust Session Limit

Edit [ajax/get_all_sessions.php](moodle-plugin/local_attackbox/ajax/get_all_sessions.php):

```php
// Line 41
$limit = isset($_GET['limit']) ? intval($_GET['limit']) : 500; // Change default
```

### Adjust Auto-Refresh Interval

Edit [amd/src/admin-dashboard.js](moodle-plugin/local_attackbox/amd/src/admin-dashboard.js):

```javascript
// Line 385
this.autoRefreshInterval = setInterval(() => {
  this.loadSessions();
}, 60000); // Change from 30000 (30s) to 60000 (1 min)
```

### Disable Auto-Refresh

Comment out the auto-refresh call in `admin_dashboard.php`:

```php
// $PAGE->requires->js_call_amd('local_attackbox/admin-dashboard', 'init', [...]);
```

## Next Steps

1. **Assign to Other Roles**: Grant `local/attackbox:managesessions` to other roles if needed
2. **Monitor Usage**: Check CloudWatch logs for errors
3. **Review Costs**: Monitor Lambda invocations and DynamoDB scans
4. **Customize UI**: Modify styles in [styles.css](moodle-plugin/local_attackbox/styles.css)
5. **Add Features**: Refer to [ADMIN_DASHBOARD.md](ADMIN_DASHBOARD.md) for enhancement ideas

## Support

- Full documentation: [ADMIN_DASHBOARD.md](ADMIN_DASHBOARD.md)
- API documentation: [modules/orchestrator/README.md](modules/orchestrator/README.md)
- Moodle plugin: [moodle-plugin/local_attackbox/README.md](moodle-plugin/local_attackbox/README.md)

## Summary

You now have:

- ✅ Admin dashboard for viewing all sessions
- ✅ Session filtering and search
- ✅ Terminate any user's session
- ✅ Real-time statistics
- ✅ Auto-refresh every 30 seconds
- ✅ Role-based access control

**Time to deploy:** ~10 minutes  
**Additional monthly cost:** ~$5  
**Supported sessions:** Up to 1000+ simultaneously
