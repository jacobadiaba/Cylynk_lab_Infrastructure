# CyberLab Session Orchestrator Module

This Terraform module deploys the session orchestration layer that connects Moodle to AWS lab resources. It manages the lifecycle of student AttackBox sessions.

## Architecture

```
┌─────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Moodle    │────▶│  API Gateway    │────▶│ Lambda Functions│
│   (LMS)     │     │  (HTTP API)     │     │                 │
└─────────────┘     └─────────────────┘     └────────┬────────┘
                                                     │
                    ┌────────────────────────────────┼────────────────────────────────┐
                    │                                │                                │
                    ▼                                ▼                                ▼
            ┌───────────────┐              ┌─────────────────┐              ┌─────────────────┐
            │   DynamoDB    │              │  EC2 / ASG      │              │   Guacamole     │
            │  (Sessions)   │              │  (AttackBoxes)  │              │   (Gateway)     │
            └───────────────┘              └─────────────────┘              └─────────────────┘
```

## Components

### Lambda Functions

| Function | Purpose | Trigger |
|----------|---------|---------|
| `create-session` | Allocates AttackBox to student | POST /sessions |
| `get-session-status` | Returns session/instance status | GET /sessions/{id} |
| `terminate-session` | Releases AttackBox from student | DELETE /sessions/{id} |
| `pool-manager` | Cleanup, sync, and scaling | EventBridge (5 min) |

### DynamoDB Tables

- **sessions**: Tracks active student sessions with TTL
- **instance-pool**: Tracks AttackBox instance availability

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/sessions` | Create new session |
| GET | `/v1/sessions/{sessionId}` | Get session status |
| GET | `/v1/students/{studentId}/sessions` | Get student's sessions |
| DELETE | `/v1/sessions/{sessionId}` | Terminate session |

## Usage

### Basic Example

```hcl
module "orchestrator" {
  source = "../../modules/orchestrator"

  project_name = "cyberlab"
  environment  = "dev"
  aws_region   = "us-east-1"

  # Networking
  vpc_id                   = module.networking.vpc_id
  subnet_ids               = [module.networking.management_subnet_id]
  lambda_security_group_id = module.security.lambda_security_group_id

  # AttackBox Integration
  attackbox_asg_name          = module.attackbox.asg_name
  attackbox_asg_arn           = module.attackbox.asg_arn
  attackbox_security_group_id = module.security.attackbox_security_group_id

  # Guacamole Integration
  guacamole_private_ip = module.guacamole.private_ip
  guacamole_api_url    = "https://guac.example.com/guacamole"

  # Session Configuration
  session_ttl_hours        = 4
  max_sessions_per_student = 1

  tags = local.common_tags
}
```

### Moodle Integration

#### Request a Session

```bash
curl -X POST https://api-endpoint/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "student_id": "student123",
    "student_name": "John Doe",
    "course_id": "SEC101",
    "lab_id": "attackbox"
  }'
```

#### Response (Session Ready)

```json
{
  "success": true,
  "message": "Session created and ready",
  "data": {
    "session_id": "sess-abc123def456",
    "status": "ready",
    "instance_id": "i-0123456789abcdef0",
    "connection_info": {
      "type": "guacamole",
      "guacamole_url": "https://guac.example.com/guacamole",
      "instance_ip": "10.0.10.15",
      "rdp_port": 3389,
      "vnc_port": 5901
    },
    "expires_at": 1699999999
  }
}
```

#### Response (Provisioning)

```json
{
  "success": true,
  "message": "Session created, instance provisioning",
  "data": {
    "session_id": "sess-abc123def456",
    "status": "provisioning",
    "message": "Instance is starting. Please poll for status.",
    "poll_interval_seconds": 10
  }
}
```

#### Check Session Status

```bash
curl https://api-endpoint/v1/sessions/sess-abc123def456
```

#### Terminate Session

```bash
curl -X DELETE https://api-endpoint/v1/sessions/sess-abc123def456
```

## Session Lifecycle

```
┌─────────┐     ┌──────────────┐     ┌───────┐     ┌────────┐     ┌────────────┐
│ PENDING │────▶│ PROVISIONING │────▶│ READY │────▶│ ACTIVE │────▶│ TERMINATED │
└─────────┘     └──────────────┘     └───────┘     └────────┘     └────────────┘
     │                 │                                               ▲
     │                 │                                               │
     └─────────────────┴───────────────────────────────────────────────┘
                              (on error or timeout)
```

## Building Lambda Packages

Before deploying, build the Lambda packages:

```bash
cd modules/orchestrator
./scripts/build-lambdas.sh
```

This creates:
- `lambda/layers/common.zip` - Shared utilities layer
- `lambda/packages/*.zip` - Individual function packages

## Configuration

### Required Variables

| Variable | Description |
|----------|-------------|
| `project_name` | Project name for resource naming |
| `environment` | Environment (dev/staging/production) |
| `vpc_id` | VPC ID for Lambda |
| `subnet_ids` | Subnet IDs for Lambda |
| `lambda_security_group_id` | Security group for Lambda |
| `attackbox_asg_name` | AttackBox ASG name |
| `guacamole_private_ip` | Guacamole server IP |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `session_ttl_hours` | 4 | Session duration before auto-cleanup |
| `max_sessions_per_student` | 1 | Max concurrent sessions per student |
| `api_stage_name` | v1 | API Gateway stage |
| `enable_xray_tracing` | false | Enable X-Ray tracing |

## Outputs

| Output | Description |
|--------|-------------|
| `api_endpoint` | API Gateway endpoint URL |
| `api_stage_url` | Full API URL with stage |
| `sessions_table_name` | DynamoDB sessions table |
| `create_session_endpoint` | POST endpoint for new sessions |

## Security Considerations

1. **API Authentication**: Consider adding API key or JWT validation
2. **Moodle Webhook Secret**: Use `moodle_webhook_secret` for signed requests
3. **VPC**: Lambda runs in VPC for private resource access
4. **IAM**: Least-privilege policies for Lambda execution role

## Monitoring

- CloudWatch Logs: `/aws/lambda/{project}-{env}-{function}`
- CloudWatch Metrics: Lambda invocations, errors, duration
- X-Ray Tracing: Enable `enable_xray_tracing` for distributed tracing

