# AttackBox Launcher - Moodle Plugin

A Moodle local plugin that adds a floating "Launch AttackBox" button on all pages, allowing students to quickly access their secure Kali Linux hacking environment.

## Features

- **Floating Button**: Always-visible launcher button on every Moodle page
- **Cyberpunk UI**: Hacker-themed loading overlay with progress messages
- **Secure Authentication**: HMAC-SHA256 signed tokens for API authentication
- **Course-Independent**: AttackBox is not tied to any specific course
- **Real-Time Status**: Polls for session status with animated progress updates
- **RemUI Compatible**: Tested with RemUI theme

## Requirements

- Moodle 4.4 or higher
- CyberLab Orchestrator API deployed
- Shared secret configured in both Moodle and AWS

## Installation

### 1. Copy Plugin Files

Copy the `local_attackbox` directory to your Moodle installation:

```bash
cp -r local_attackbox /path/to/moodle/local/
```

### 2. Install via Moodle

1. Log in as admin
2. Go to **Site Administration → Notifications**
3. Moodle will detect the new plugin and prompt for installation
4. Click **Upgrade Moodle database now**

### 3. Configure the Plugin

1. Go to **Site Administration → Plugins → Local plugins → AttackBox Launcher**
2. Configure the following settings:

| Setting | Description | Example |
|---------|-------------|---------|
| **Orchestrator API URL** | Base URL of the CyberLab API | `https://abc123.execute-api.us-east-1.amazonaws.com/v1` |
| **Shared Secret** | Secret for token signing (must match AWS) | `your-secure-shared-secret-here` |
| **Session Duration** | Display-only TTL in hours | `4` |
| **Enable Launcher** | Show/hide the floating button | `Yes` |
| **Button Position** | Where to display the button | `Bottom Right` |
| **Poll Interval** | Status check frequency in ms | `3000` |

### 4. Configure AWS Lambda

Update your Terraform variables to include the shared secret:

```hcl
# environments/dev/terraform.tfvars
moodle_webhook_secret = "your-secure-shared-secret-here"
require_moodle_auth   = true
```

Then apply the changes:

```bash
cd environments/dev
terraform apply
```

## Usage

Once installed and configured:

1. Students log into Moodle
2. A floating "Launch AttackBox" button appears (bottom-right by default)
3. Clicking the button opens a full-screen loading overlay
4. Progress messages show the launch status:
   - "Initializing virtual SOC environment..."
   - "Configuring VPN and firewall bypass rules..."
   - "Installing cyber tools: Nmap, Burp, Metasploit..."
   - etc.
5. When ready, the AttackBox opens in a new browser tab via Guacamole

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         MOODLE LMS                          │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              local_attackbox plugin                  │   │
│  │                                                      │   │
│  │   db/hooks.php → registers hook callback             │   │
│  │   classes/hook_callbacks.php → injects JS on footer │   │
│  │   ajax/get_token.php → generates signed token       │   │
│  │   amd/src/launcher.js → floating button + overlay   │   │
│  │   styles.css → auto-loaded by Moodle                │   │
│  │                                                      │   │
│  └──────────────────────┬──────────────────────────────┘   │
│                         │                                   │
└─────────────────────────┼───────────────────────────────────┘
                          │
                          │ HTTPS (X-Moodle-Token header)
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│               AWS API Gateway + Lambda                       │
│                                                             │
│  POST /sessions        → create-session Lambda              │
│  GET /sessions/{id}    → get-session-status Lambda          │
│                                                             │
│  Token verification → MoodleTokenVerifier                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              AttackBox Pool (EC2 + Guacamole)               │
└─────────────────────────────────────────────────────────────┘
```

## Token Format

Tokens are base64-encoded JSON with HMAC-SHA256 signature:

```
<base64_payload>.<hex_signature>
```

Payload structure:
```json
{
  "user_id": "123",
  "username": "student001",
  "email": "student@example.com",
  "firstname": "John",
  "lastname": "Doe",
  "fullname": "John Doe",
  "timestamp": 1701676800,
  "expires": 1701677100,
  "nonce": "abc123def456...",
  "issuer": "moodle",
  "site_url": "https://moodle.example.com"
}
```

## Customization

### Change Button Position

Edit **Site Administration → Plugins → Local plugins → AttackBox Launcher → Button Position**

Options: Bottom Right, Bottom Left, Top Right, Top Left

### Modify Progress Messages

Edit `lang/en/local_attackbox.php`:

```php
$string['progress:25'] = 'Your custom message here...';
```

### Custom Styling

Override styles in your theme or add custom CSS:

```css
.attackbox-btn {
    --attackbox-primary: #ff00ff;  /* Change accent color */
}
```

## Troubleshooting

### Button not appearing

1. Check if plugin is enabled in settings
2. Verify you're logged in (button only shows for authenticated users)
3. Check browser console for JavaScript errors
4. Ensure API URL and shared secret are configured

### "Authentication required" error

1. Verify shared secret matches in Moodle and AWS
2. Check token hasn't expired (default 5 minutes)
3. Ensure `REQUIRE_MOODLE_AUTH` is set correctly in Lambda

### Session stuck on "Provisioning"

1. Check AWS CloudWatch logs for Lambda errors
2. Verify AttackBox pool has available instances
3. Ensure Guacamole server is accessible from Lambda

### CORS errors

1. Add your Moodle domain to `allowed_origins` in Terraform
2. Verify API Gateway CORS configuration

## Development

### Build AMD module

After editing `amd/src/launcher.js`:

```bash
cd /path/to/moodle
grunt amd
```

Or in development mode (no minification):

```bash
grunt amd --force
```

### Clear Moodle caches

```bash
php admin/cli/purge_caches.php
```

## License

GNU GPL v3 or later - see [LICENSE](http://www.gnu.org/copyleft/gpl.html)

## Support

For issues or feature requests, contact the CyberLab infrastructure team.

