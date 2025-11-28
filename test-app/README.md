# CyberLab AttackBox Launcher - Test App

A simple web application to test the CyberLab Orchestrator API before integrating with Moodle.

## Quick Start

### Option 1: Python Server (Recommended)

```bash
cd test-app
python serve.py
```

Then open: http://localhost:8080

### Option 2: Any Static Server

```bash
# Using Node.js npx
npx serve test-app

# Using PHP
cd test-app && php -S localhost:8080

# Using Python 3 directly
cd test-app && python -m http.server 8080
```

### Option 3: Open Directly

Just open `index.html` in your browser (some features may be limited due to CORS).

## Usage

1. **Configure API Endpoint**
   - Enter your Orchestrator API URL (from Terraform output)
   - Format: `https://your-api-id.execute-api.us-east-1.amazonaws.com/v1`

2. **Enter Student Info**
   - Student ID: Unique identifier (e.g., `student001`)
   - Student Name: Display name
   - Course ID: Course identifier
   - Lab ID: Usually `attackbox`

3. **Launch AttackBox**
   - Click "Launch AttackBox" to request a session
   - The app will poll for status automatically
   - When ready, click "Open Guacamole" to connect

4. **Monitor & Terminate**
   - Use "Check Status" to manually refresh
   - Use "Terminate Session" to release the AttackBox

## API Endpoints Tested

| Button | Method | Endpoint |
|--------|--------|----------|
| Launch AttackBox | POST | `/sessions` |
| Check Status | GET | `/sessions/{sessionId}` |
| Terminate Session | DELETE | `/sessions/{sessionId}` |

## Session States

| Status | Description |
|--------|-------------|
| `pending` | Session created, looking for instance |
| `provisioning` | Instance is starting up |
| `ready` | Instance ready, connection available |
| `active` | Student is connected |
| `terminated` | Session ended |
| `error` | Something went wrong |

## Troubleshooting

### CORS Errors
If you see CORS errors in the browser console:
1. Make sure you're using the Python server (not opening HTML directly)
2. Check that your API Gateway has CORS configured
3. The Orchestrator module includes CORS configuration by default

### API Not Responding
1. Verify the API endpoint URL is correct
2. Check that Lambda functions are deployed
3. Look at CloudWatch Logs for errors

### Session Stuck in Provisioning
1. Check if AttackBox instances are available in the ASG
2. Verify EC2 instance is starting (check AWS Console)
3. The pool-manager Lambda runs every 5 minutes to sync state

## Files

```
test-app/
├── index.html    # Main HTML page
├── styles.css    # Dark theme styles
├── app.js        # JavaScript logic
├── serve.py      # Python dev server
└── README.md     # This file
```

## Screenshot

The app features a dark "hacker" theme with:
- Real-time API logging
- Session status tracking
- One-click Guacamole connection
- Automatic status polling

