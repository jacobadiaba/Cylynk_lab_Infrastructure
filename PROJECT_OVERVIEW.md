# CyberLab Infrastructure - Project Overview

## Executive Summary

CyberLab Infrastructure is a comprehensive Infrastructure-as-Code (IaC) solution for deploying and managing a cloud-based cybersecurity training lab environment on AWS. The system provides on-demand Kali Linux AttackBox instances to students through a Moodle LMS integration, with automated session management, cost optimization, and multi-tier subscription support.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         STUDENT LAYER                             │
│  Moodle LMS → Plugin → Browser → Guacamole → AttackBox (Kali)   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      ORCHESTRATION LAYER                        │
│  API Gateway → Lambda Functions → DynamoDB (Sessions/Usage)     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      INFRASTRUCTURE LAYER                        │
│  EC2 Auto Scaling Groups → Warm Pools → VPC → Security Groups   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. **Terraform Modules** (Infrastructure Provisioning)

#### Networking Module (`modules/networking/`)

- VPC with CIDR configuration
- Management subnet (Guacamole server)
- AttackBox pool subnet (student instances)
- Student lab subnets (isolated environments)
- NAT Gateway (optional for cost optimization)
- VPC Flow Logs
- VPC Endpoints (for cost reduction)

#### Security Module (`modules/security/`)

- Security groups for Lambda, Guacamole, AttackBox
- IAM roles and policies
- EC2 key pairs
- VPN configuration support

#### AttackBox Module (`modules/attackbox/`)

- **Multi-tier Auto Scaling Groups**:
  - Freemium: t3.small (2 vCPU, 2GB RAM)
  - Starter: t3.medium (2 vCPU, 4GB RAM)
  - Pro: t3.large (2 vCPU, 8GB RAM)
- Warm pool support (30-60s instance startup)
- Custom AMI support (Packer-built Kali images)
- CloudWatch monitoring and logging
- Instance tagging for cost tracking

#### Guacamole Module (`modules/guacamole/`)

- Apache Guacamole RDP gateway server
- Docker-based deployment
- Nginx reverse proxy
- Let's Encrypt SSL certificates
- CloudWatch monitoring
- Auto-restart scripts

#### Orchestrator Module (`modules/orchestrator/`)

- **Lambda Functions**:
  - `create-session`: Allocates AttackBox instances
  - `get-session-status`: Polls session provisioning status
  - `terminate-session`: Releases instances and tracks usage
  - `pool-manager`: Background cleanup and scaling (runs every 5 min)
  - `admin-sessions`: Admin dashboard API
  - `get-usage`: Usage statistics API
  - `usage-history`: Historical usage data
  - `session-heartbeat`: Session keepalive tracking
- **DynamoDB Tables**:
  - `sessions`: Active session tracking with TTL
  - `instance-pool`: Instance availability tracking
  - `usage`: Monthly usage quotas per user
- **API Gateway**: HTTP API with CORS support
- Moodle token authentication (HMAC-SHA256)

#### Monitoring Module (`modules/monitoring/`)

- CloudWatch Log Groups
- CloudWatch Alarms
- SNS topics for alerts
- Cost anomaly detection
- Flow logs integration

#### Storage Module (`modules/storage/`)

- S3 buckets for backups/artifacts
- Lifecycle policies
- Versioning support

#### Cost Optimization Module (`modules/cost-optimization/`)

- AWS Budgets (daily/monthly)
- Cost anomaly detection
- AWS Compute Optimizer enrollment
- CloudWatch cost dashboard
- EC2 usage budget tracking

### 2. **Ansible Playbooks** (Configuration Management)

#### Guacamole Playbook (`ansible/playbooks/guacamole.yml`)

- Docker installation
- Guacamole container deployment
- Nginx configuration
- SSL certificate setup (Let's Encrypt)
- CloudWatch agent installation
- Health check scripts

#### AttackBox Playbook (`ansible/playbooks/attackbox.yml`)

- Kali Linux hardening
- RDP server configuration (xrdp)
- VNC server setup
- CloudWatch agent
- Security tools installation
- User environment setup
- Reset scripts

### 3. **Moodle Plugin** (`moodle-plugin/local_attackbox/`)

#### Features

- **Floating Launcher Button**: Always-visible on all Moodle pages
- **Cyberpunk UI**: Hacker-themed loading overlay with progress messages
- **Real-time Status Polling**: 3-second intervals, max 10 minutes
- **Usage Dashboard**: Shows monthly quota consumption
- **Admin Dashboard**: View/manage all user sessions
- **Secure Authentication**: HMAC-SHA256 signed tokens

#### Components

- `admin_dashboard.php`: Admin interface for session management
- `usage.php`: Student usage statistics page
- `ajax/get_token.php`: Token generation endpoint
- `ajax/get_all_sessions.php`: Admin session listing
- `ajax/admin_terminate_session.php`: Admin termination
- `ajax/get_usage.php`: Usage statistics
- `amd/src/launcher.js`: Main launcher UI
- `amd/src/admin-dashboard.js`: Admin dashboard UI
- `amd/src/usage-dashboard.js`: Usage visualization

### 4. **Packer** (AMI Building)

- Custom Kali Linux AMI with pre-installed tools
- CloudWatch agent pre-configured
- RDP/VNC servers ready
- Security hardening applied

---

## Key Features & Capabilities

### ✅ Session Management

1. **Multi-Tier Support**

   - Freemium: 5 hours/month quota, t3.small instances
   - Starter: 15 hours/month quota, t3.medium instances
   - Pro: Unlimited quota, t3.large instances

2. **Instance Pool Management**

   - Warm pool for fast startup (30-60 seconds)
   - Automatic scaling based on demand
   - Instance reuse for cost optimization
   - Dead session cleanup

3. **Session Lifecycle**

   - Status: PENDING → PROVISIONING → READY → ACTIVE → TERMINATED
   - Automatic expiry (4-hour default TTL)
   - Manual termination
   - Admin termination capability

4. **Provisioning Flow**
   - Best case: 5-10 seconds (instance in pool)
   - Normal case: 5-7 minutes (warm pool)
   - Worst case: 8-12 minutes (cold start)

### ✅ Usage Tracking & Quotas

1. **Monthly Quotas**

   - Per-user tracking in DynamoDB
   - Plan-based limits
   - Real-time consumption tracking
   - Quota enforcement on session creation

2. **Usage APIs**

   - `GET /usage`: Current user's usage
   - `GET /usage/{userId}`: Admin query
   - `GET /usage/history`: Historical data

3. **Usage Dashboard**
   - Visual quota display in Moodle
   - Color-coded badges (green/yellow/red)
   - Remaining time calculation

### ✅ Admin Features

1. **Admin Dashboard**

   - View all active/provisioning/terminated sessions
   - Search by student ID, name, or session ID
   - Filter by status
   - Terminate any user's session
   - Real-time statistics

2. **Session Statistics**
   - Total sessions
   - Active/ready/provisioning counts
   - Instances in use
   - Auto-refresh every 30 seconds

### ✅ Cost Optimization

1. **Budget Management**

   - Daily budget alerts (80%, 100%, 110% thresholds)
   - Monthly budget tracking
   - EC2 usage hour budgets
   - Email notifications

2. **Cost Monitoring**

   - CloudWatch cost dashboard
   - Cost anomaly detection
   - Compute Optimizer recommendations
   - SNS alerts for overruns

3. **Infrastructure Optimizations**
   - VPC endpoints (reduce NAT costs)
   - Warm pools (reduce cold start costs)
   - Instance reuse (reduce launch costs)
   - Auto-scaling (scale down when idle)

### ✅ Security

1. **Authentication**

   - Moodle token-based authentication
   - HMAC-SHA256 signed tokens
   - Token expiration (5 minutes)
   - Nonce-based replay protection

2. **Network Security**

   - VPC isolation
   - Security groups (least privilege)
   - Private subnets for instances
   - VPN support

3. **Access Control**
   - Moodle capability-based permissions
   - Admin-only endpoints
   - User isolation (users can only see own sessions)

### ✅ Monitoring & Observability

1. **CloudWatch Integration**

   - Lambda function logs
   - EC2 instance logs
   - Guacamole logs
   - Cost metrics
   - Custom metrics

2. **Alarms**

   - Lambda errors
   - EC2 instance health
   - Cost thresholds
   - API Gateway errors

3. **Dashboards**
   - Cost overview dashboard
   - Session statistics
   - Instance pool status

### ✅ CI/CD

1. **GitHub Actions Workflows**

   - Terraform validation
   - Terraform deployment (dev/prod)
   - Ansible linting
   - Security scanning (tfsec, checkov)

2. **OIDC Authentication**
   - No long-lived credentials
   - Automatic credential rotation
   - Role-based access

---

## Current Limitations & Known Gaps

### Missing Features

1. **Session Recording**

   - No screen recording capability
   - No session replay functionality

2. **Advanced Analytics**

   - No detailed usage analytics dashboard
   - No predictive scaling
   - Limited historical trend analysis

3. **Multi-Region Support**

   - Single region deployment only
   - No disaster recovery

4. **Backup & Recovery**

   - No automated backup of student work
   - No snapshot management
   - No disaster recovery plan

5. **Resource Limits**

   - No per-session resource limits (CPU/memory throttling)
   - No network bandwidth limits

6. **Integration Features**

   - No webhook support for external systems
   - No REST API for programmatic access (beyond Moodle)
   - No GraphQL API

7. **Advanced Admin Features**

   - No bulk operations (terminate multiple sessions)
   - No session reset (without termination)
   - No manual instance allocation
   - No custom instance types per user

8. **Student Features**

   - No session pause/resume
   - No session extension
   - No multiple concurrent sessions
   - No session sharing/collaboration

9. **Compliance & Auditing**

   - Limited audit logging
   - No compliance reports
   - No GDPR/privacy features

10. **Performance Optimization**
    - No CDN for static assets
    - No caching layer
    - No database query optimization

---

## Potential Feature Additions

### High Priority

1. **Session Recording & Replay**

   - Record student sessions for review
   - Replay sessions for troubleshooting
   - Compliance/audit trail

2. **Advanced Analytics Dashboard**

   - Usage trends over time
   - Peak usage patterns
   - Cost per student
   - Instance utilization metrics

3. **Backup & Snapshot Management**

   - Automated student work backups
   - Snapshot before termination
   - Restore from snapshot

4. **Resource Limits & Throttling**

   - Per-session CPU/memory limits
   - Network bandwidth throttling
   - Prevent resource abuse

5. **Webhook Integration**
   - Notify external systems on session events
   - Integration with LMS/CRM systems
   - Custom event handlers

### Medium Priority

6. **Multi-Region Support**

   - Deploy to multiple AWS regions
   - Regional failover
   - Latency-based routing

7. **Session Pause/Resume**

   - Pause sessions without termination
   - Resume from same state
   - Extend session duration

8. **Bulk Operations**

   - Terminate multiple sessions
   - Reset multiple instances
   - Batch user management

9. **Custom Instance Types**

   - Allow admins to assign custom instance types
   - Override plan-based defaults
   - Special lab requirements

10. **REST API Documentation**
    - OpenAPI/Swagger spec
    - API documentation site
    - SDK generation

### Low Priority

11. **Session Collaboration**

    - Share sessions between students
    - Multi-user sessions
    - Screen sharing

12. **Advanced Quota Management**

    - Per-course quotas
    - Time-based quotas (daily/weekly)
    - Quota transfer between users

13. **Compliance Features**

    - GDPR data export
    - Audit log export
    - Compliance reports

14. **Performance Enhancements**

    - Redis caching layer
    - CDN for static assets
    - Database query optimization

15. **Mobile App Support**
    - Mobile-optimized UI
    - Push notifications
    - Mobile session management

---

## Technology Stack

- **Infrastructure**: Terraform, AWS (EC2, Lambda, DynamoDB, API Gateway, VPC)
- **Configuration**: Ansible
- **Orchestration**: AWS Lambda (Python)
- **Frontend**: Moodle Plugin (PHP, JavaScript)
- **Remote Access**: Apache Guacamole (RDP/VNC)
- **OS**: Kali Linux (AttackBox)
- **CI/CD**: GitHub Actions
- **Monitoring**: CloudWatch, SNS
- **Cost Management**: AWS Budgets, Cost Anomaly Detection

---

## Deployment Environments

- **Development**: `environments/dev/`
- **Production**: `environments/prod/` (manual deployment only)

---

## Documentation

- `README.md`: Main project documentation
- `ADMIN_DASHBOARD.md`: Admin dashboard guide
- `LAUNCH_ATTACKBOX_FLOWCHART.md`: Detailed launch flow
- `QUOTA_DEPLOYMENT.md`: Quota system deployment
- `PRODUCTION_COST_ESTIMATE.md`: Cost analysis
- Module-specific READMEs in each `modules/*/README.md`

---

## Next Steps for Feature Development

1. **Prioritize Features**: Review the potential features list and prioritize based on business needs
2. **Design Phase**: Create detailed design documents for selected features
3. **Implementation**: Follow the existing code patterns and architecture
4. **Testing**: Ensure compatibility with existing features
5. **Documentation**: Update relevant documentation files

---

## Contact & Support

- Infrastructure Team @ AmaliTech gGmbH
- GitHub Issues: [Repository Issues](https://github.com/jacobadiaba/Cylynk_lab_Infrastructure/issues)
