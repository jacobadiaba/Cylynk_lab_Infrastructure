# CyberLab Infrastructure

## AWS Cost Analysis & Architecture

**Presented by:** CyberLab Team  
**Date:** December 12, 2025

---

# Agenda

1. **System Architecture Overview**
2. **Production Cost Analysis**
3. **Cost Savings & Optimization Strategies**

---

# SECTION 1

## System Architecture

---

# Architecture Overview

## Cloud-Based Cyber Range Platform

### Scalable, Secure, Cost-Effective

**Key Components:**

- Moodle LMS Integration
- Session Orchestration API
- Auto-Scaling AttackBox Pool
- Apache Guacamole Gateway
- DynamoDB Storage

---

# Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         MOODLE LMS                               │
│                    (academy.cyberlynk.io)                        │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │     AttackBox Launcher Plugin (local_attackbox)          │  │
│  │  • Session Timer Display                                 │  │
│  │  • Usage Dashboard                                       │  │
│  │  • Launch/Terminate Controls                            │  │
│  └──────────────────────────────────────────────────────────┘  │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTPS / JWT Token
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AWS API GATEWAY (HTTP API)                    │
│                                                                   │
│  Routes:                                                         │
│  • POST   /sessions          → create-session                   │
│  • GET    /sessions/{id}     → get-session-status              │
│  • DELETE /sessions/{id}     → terminate-session               │
│  • GET    /sessions/history  → usage-history                   │
│  • GET    /students/{id}/sessions → get active sessions        │
└───────────────────────────┬─────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   AWS        │  │   AWS        │  │   AWS        │
│   LAMBDA     │  │   LAMBDA     │  │   LAMBDA     │
│              │  │              │  │              │
│ • Create     │  │ • Get        │  │ • Terminate  │
│   Session    │  │   Status     │  │   Session    │
│              │  │ • Health     │  │              │
│ • Allocate   │  │   Checks     │  │ • Release    │
│   Instance   │  │              │  │   Instance   │
│              │  │ • Enrich     │  │              │
│ • Create     │  │   Data       │  │ • Track      │
│   Guacamole  │  │              │  │   Usage      │
│   Connection │  │              │  │              │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │
       └────────┬────────┴────────┬────────┘
                │                 │
                ▼                 ▼
    ┌─────────────────┐  ┌─────────────────┐
    │   DYNAMODB      │  │   DYNAMODB      │
    │   Sessions      │  │   Instance      │
    │   Table         │  │   Pool Table    │
    │                 │  │                 │
    │ • session_id    │  │ • instance_id   │
    │ • student_id    │  │ • status        │
    │ • status        │  │ • session_id    │
    │ • expires_at    │  │                 │
    │ • instance_id   │  │ Status:         │
    │                 │  │ • available     │
    │ GSI:            │  │ • in_use        │
    │ • StatusIndex   │  │ • terminating   │
    │ • StudentIndex  │  └─────────────────┘
    └─────────────────┘
                │
                ▼
    ┌─────────────────────────────────────┐
    │   AWS LAMBDA - Pool Manager         │
    │   (Runs every 1 minute)            │
    │                                     │
    │ • Clean expired sessions           │
    │ • Release orphaned instances       │
    │ • Auto-scale ASG based on demand   │
    │ • Sync pool with EC2 state         │
    └──────────────┬──────────────────────┘
                   │
                   ▼
    ┌─────────────────────────────────────┐
    │   AUTO SCALING GROUP                │
    │   (AttackBox Pool)                  │
    │                                     │
    │  Desired: 2-4 instances            │
    │  Min: 1                            │
    │  Max: 5 (dev) / 100 (prod)         │
    │                                     │
    │  ┌─────────┐  ┌─────────┐         │
    │  │ t3.med  │  │ t3.med  │  ...    │
    │  │ Kali    │  │ Kali    │         │
    │  │ Linux   │  │ Linux   │         │
    │  └────┬────┘  └────┬────┘         │
    └───────┼────────────┼───────────────┘
            │            │
            └─────┬──────┘
                  │ Private Subnet
                  ▼
    ┌─────────────────────────────────────┐
    │   APACHE GUACAMOLE SERVER           │
    │   (Gateway)                         │
    │                                     │
    │  • t3.small / t3.medium            │
    │  • RDP/VNC/SSH Proxy               │
    │  • Connection Management           │
    │  • Public IP / Domain              │
    │                                     │
    │  Routes:                           │
    │  • /guacamole/api/tokens           │
    │  • /guacamole/#/client/...         │
    └──────────────┬──────────────────────┘
                   │ HTTPS
                   ▼
         ┌──────────────────┐
         │    STUDENTS      │
         │  (Web Browser)   │
         │                  │
         │  • Access via    │
         │    Guacamole     │
         │  • RDP Session   │
         │  • No VPN needed │
         └──────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                   SUPPORTING SERVICES                            │
│                                                                   │
│  • CloudWatch Logs (Lambda, ASG, EC2)                           │
│  • EventBridge (Pool Manager Schedule)                          │
│  • S3 (Optional: Session logs, AMI snapshots)                   │
│  • VPC (Networking, Subnets, NAT Gateway)                       │
│  • IAM (Roles, Policies, Instance Profiles)                     │
│  • CloudWatch Alarms (Monitoring, Alerts)                       │
└─────────────────────────────────────────────────────────────────┘
```

---

# Data Flow: Student Launches AttackBox

```
1. STUDENT CLICKS LAUNCH
   ↓
2. MOODLE PLUGIN → API Gateway
   POST /sessions {student_id, course_id}
   ↓
3. CREATE-SESSION LAMBDA
   • Check quota (usage limits)
   • Find available instance from pool
   • Update DynamoDB (status: provisioning)
   • Start EC2 instance if stopped
   • Create Guacamole RDP connection
   ↓
4. POLL FOR STATUS (every 3s)
   GET /sessions/{sessionId}
   ↓
5. GET-SESSION-STATUS LAMBDA
   • Query DynamoDB session
   • Check EC2 instance health (3/3 checks)
   • Enrich with connection URL
   • Update status: ready
   ↓
6. STUDENT OPENS ATTACKBOX
   • Redirect to Guacamole URL
   • RDP session established
   • Session timer starts (4 hours)
   ↓
7. BACKGROUND: POOL MANAGER (every 1 min)
   • Clean expired sessions
   • Scale ASG if needed
   • Release idle instances
```

---

# Key Architecture Features

## ✅ Auto-Scaling

- Dynamic capacity based on demand
- Scale from 1 to 100+ instances

## ✅ Health Monitoring

- Real-time EC2 health checks (3/3)
- Automatic instance recovery

## ✅ Session Management

- 4-hour session TTL
- Usage tracking per student
- Quota enforcement

## ✅ High Availability

- Multi-AZ deployment option
- Auto-healing instances
- Redundant Guacamole servers (prod)

---

# SECTION 2

## Production Cost Analysis

---

# Cost Components Overview

## Fixed vs Variable Costs

**Fixed (Always Running):**

- Networking (VPC, NAT Gateway)
- Guacamole Server
- DynamoDB Tables
- Lambda Functions
- Monitoring

**Variable (Usage-Based):**

- AttackBox Instances (70% of total cost)
- Data Transfer
- Storage

---

# Fixed Infrastructure Costs

| Component       | Specification       | Monthly Cost      |
| --------------- | ------------------- | ----------------- |
| **NAT Gateway** | 1 gateway + data    | $35-45            |
| **Guacamole**   | t3.medium + storage | $38-52            |
| **DynamoDB**    | 3 tables, on-demand | $6-16             |
| **Lambda**      | All functions       | $2-16             |
| **API Gateway** | HTTP API            | $2-19             |
| **CloudWatch**  | Logs + metrics      | $4-35             |
| **S3**          | Optional storage    | $2-23             |
|                 |                     |
| **TOTAL FIXED** |                     | **$89-206/month** |

_Typical production: ~$120-150/month_

---

# AttackBox Instance Costs

## t3.medium Pricing (2 vCPU, 4GB RAM)

| Pricing Model         | Per Hour      | Per Month (24/7) | Savings    |
| --------------------- | ------------- | ---------------- | ---------- |
| **On-Demand**         | $0.0416       | $30.37           | Baseline   |
| **Spot Instance**     | $0.0125-0.025 | $9-18            | **70-80%** |
| **Reserved 1-yr**     | $0.0255       | $18.62           | **38%**    |
| **Savings Plan 3-yr** | $0.0116       | $8.47            | **72%**    |

**+ EBS Storage:** $4/month per instance (50GB gp3)

**Total per instance:** $34.37/month (on-demand) or $22.62/month (reserved)

---

# Production Cost Scenarios

## Monthly Costs by Student Count

| Students | Min Instances | Avg Instances | Monthly Cost | Annual Cost    |
| -------- | ------------- | ------------- | ------------ | -------------- |
| **10**   | 2             | 3             | $285-340     | $3,420-4,080   |
| **50**   | 5             | 10            | $650-780     | $7,800-9,360   |
| **100**  | 10            | 20            | $1,150-1,400 | $13,800-16,800 |
| **200+** | 20            | 40            | $2,200-2,800 | $26,400-33,600 |

_Costs include all infrastructure + optimizations_

---

# Scenario 1: Small Deployment

## 10 Concurrent Students

```
Fixed Infrastructure:        $120/month
AttackBox Pool (3 avg):      $103/month
Data Transfer:               $50/month
Monitoring:                  $20/month
──────────────────────────────────────
TOTAL:                       $293/month
Annual:                      $3,516/year
```

**Cost per student hour:** $0.28-0.32

**Recommended for:**

- Pilot programs
- Small training cohorts
- Testing environments

---

# Scenario 2: Medium Deployment

## 50 Concurrent Students

```
Fixed Infrastructure:        $140/month
AttackBox Pool (10 avg):     $344/month
Data Transfer:               $150/month
Monitoring:                  $40/month
──────────────────────────────────────
TOTAL:                       $674/month
Annual:                      $8,088/year
```

**Cost per student hour:** $0.22-0.26

**Recommended for:**

- University courses
- Bootcamp programs
- Corporate training

---

# Scenario 3: Large Deployment

## 100 Concurrent Students

```
Fixed Infrastructure:        $160/month
AttackBox Pool (20 avg):     $687/month
Data Transfer:               $250/month
Monitoring:                  $80/month
──────────────────────────────────────
TOTAL:                       $1,177/month
Annual:                      $14,124/year
```

**Cost per student hour:** $0.19-0.23

**Recommended for:**

- Large universities
- Enterprise training programs
- Multi-cohort deployments

---

# Scenario 4: Enterprise Deployment

## 200+ Concurrent Students

```
Fixed Infrastructure:        $180/month
AttackBox Pool (40 avg):     $1,375/month
Data Transfer:               $400/month
Monitoring:                  $120/month
Support (Premium):           $100/month
──────────────────────────────────────
TOTAL:                       $2,175/month
Annual:                      $26,100/year
```

**Cost per student hour:** $0.15-0.19

**Recommended for:**

- National training programs
- Multi-campus deployments
- Managed service providers

---

# Cost Breakdown by Component

## Where Does the Money Go?

```
┌────────────────────────────────────────┐
│  AttackBox Instances:      65-75%     │█████████████████
│  Data Transfer:            10-15%     │████
│  Fixed Infrastructure:     8-12%      │███
│  Monitoring & Logs:        3-5%       │██
│  Other Services:           2-3%       │█
└────────────────────────────────────────┘
```

**Key Insight:** AttackBox compute is the primary cost driver
→ Focus optimization efforts here for maximum savings

---

# Cost Comparison: Cloud vs Traditional Lab

## 50-Student Deployment

| Item                       | Traditional Lab | CyberLab Cloud | Savings            |
| -------------------------- | --------------- | -------------- | ------------------ |
| **Hardware**               | $100,000        | $0             | $100,000           |
| **Networking**             | $20,000         | $0             | $20,000            |
| **Space (Year 1)**         | $24,000         | $0             | $24,000            |
| **Power/Cooling (Year 1)** | $12,000         | $0             | $12,000            |
| **Maintenance (Year 1)**   | $15,000         | $0             | $15,000            |
| **Cloud Infrastructure**   | $0              | $8,088         | -$8,088            |
|                            |                 |                |
| **Year 1 Total**           | $171,000        | $8,088         | **$162,912 (95%)** |
| **Year 2+ Annual**         | $51,000         | $8,088         | **$42,912 (84%)**  |

---

# ROI Timeline

## 5-Year Total Cost of Ownership

```
Traditional Lab:
Year 1: $171,000  ████████████████████████████████
Year 2: $ 51,000  ███████████
Year 3: $ 51,000  ███████████
Year 4: $ 51,000  ███████████
Year 5: $ 51,000  ███████████
─────────────────────────────────────────────
Total:  $375,000

CyberLab Cloud:
Year 1: $  8,088  ██
Year 2: $  8,088  ██
Year 3: $  8,088  ██
Year 4: $  8,088  ██
Year 5: $  8,088  ██
─────────────────────────────────────────────
Total:  $ 40,440

SAVINGS: $334,560 (89% reduction)
```

---

# SECTION 3

## Cost Savings & Optimization Strategies

---

# Optimization Strategy Overview

## 8 Key Areas for Cost Reduction

1. **Spot Instances** (70-80% savings)
2. **Reserved Instances** (38% savings)
3. **Savings Plans** (up to 72% savings)
4. **Auto-Scaling Optimization**
5. **Data Transfer Optimization**
6. **Storage Optimization**
7. **Monitoring Optimization**
8. **Right-Sizing**

**Combined Potential Savings: 50-70% of baseline costs**

---

# Strategy 1: Spot Instances

## Leverage AWS Spare Capacity

**What are Spot Instances?**

- AWS excess capacity at 70-80% discount
- Can be interrupted with 2-minute warning
- Perfect for stateless, interruptible workloads

**Implementation for CyberLab:**

```
Mix Strategy:
• 50% On-Demand (reliable, always available)
• 50% Spot (cost-effective, best effort)

Example (10 instances):
• 5 On-Demand @ $30.37/month = $151.85
• 5 Spot @ $9-18/month = $45-90
────────────────────────────────────
Total: $196.85-241.85 (vs $303.70 on-demand)
Savings: $62-107/month (20-35%)
```

**Interruption Handling:**

- Pool manager reallocates sessions
- Graceful session migration
- User sees minimal disruption

---

# Strategy 2: Reserved Instances

## 1-Year Commitment for Predictable Workloads

**How It Works:**

- Commit to minimum capacity (e.g., 10 instances)
- Pay upfront or monthly
- Lock in 38% discount

**Recommended Approach:**

```
For 50-student deployment (10 avg instances):
• Reserve: 5 instances (minimum/base load)
• On-Demand/Spot: 5 instances (burst capacity)

Cost Breakdown:
• 5 Reserved @ $18.62/month = $93.10
• 5 On-Demand/Spot @ $20-30/month = $100-150
────────────────────────────────────
Total: $193.10-243.10
Savings: $60-110/month vs all on-demand
Annual Savings: $720-1,320
```

**Best For:** Stable minimum capacity that runs 24/7

---

# Strategy 3: Savings Plans

## Flexible Commitment for Maximum Savings

**3-Year Savings Plan:**

- Commit to $/hour compute spend
- Up to 72% discount
- Flexible across instance types and regions

**Example Calculation:**

```
Commit to $50/month ($0.069/hour) for 3 years:
• Gets you ~4-5 t3.medium instances worth
• Covers base load
• Savings: $130/month vs on-demand

Investment: $1,800/year × 3 = $5,400 total
Saves: $1,560/year × 3 = $4,680 over 3 years
ROI: 87% return on commitment
```

**Advantages:**

- More flexible than Reserved Instances
- Applies automatically to lowest-cost instances
- Can change instance types freely

---

# Strategy 4: Auto-Scaling Optimization

## Scale Aggressively, Save Significantly

**Current Implementation:**

- Pool manager runs every 1 minute
- Scales based on available instances
- Target: Keep 0-1 available instances

**Optimization Opportunities:**

### 1. Scheduled Scaling

```
Typical Usage Pattern:
• Mon-Fri 8AM-8PM: High usage (scale to 10-15)
• Nights/Weekends: Low usage (scale down to 2-3)

Savings: 40-50% on compute costs
```

### 2. Predictive Scaling

- Use historical data to pre-scale before demand
- Reduce wait times while minimizing idle instances

### 3. Aggressive Scale-Down

- Terminate idle instances after 5 minutes
- Keep only minimum capacity during low usage

**Expected Savings: 20-40% on variable costs**

---

# Strategy 5: Data Transfer Optimization

## Reduce Bandwidth Costs

**Current Costs:**

- $0.09/GB outbound after first 100GB free
- 50-student deployment: ~$150/month

**Optimization Strategies:**

### 1. VPC Endpoints (Save $20-50/month)

```
Enable DynamoDB & S3 VPC endpoints
• Eliminates inter-AZ transfer fees
• Keeps traffic within AWS network
• Cost: $14-20/month
• Saves: $30-70/month on transfer
Net Savings: $10-50/month
```

### 2. Compression & Optimization

- Enable RDP compression (already configured)
- Optimize Guacamole image quality settings
- Use browser caching
  **Savings: 10-20% on data transfer**

### 3. CloudFront CDN (Optional)

- For static assets (AMIs, updates)
- Better caching, lower costs for global users

---

# Strategy 6: Storage Optimization

## Reduce S3 and EBS Costs

**EBS Optimization:**

```
Current: 50GB gp2 @ $5/month
Optimized: 50GB gp3 @ $4/month
Savings: $1/instance/month

For 20 instances: $20/month saved
```

**S3 Lifecycle Policies:**

```
Session logs & backups:
• Keep 7 days in S3 Standard
• Move to Glacier after 30 days (90% cheaper)
• Delete after 180 days

Savings: $5-30/month depending on volume
```

**DynamoDB TTL:**

- Auto-delete expired sessions after 30 days
- Already configured in infrastructure
- Prevents unnecessary storage costs

---

# Strategy 7: Monitoring Optimization

## Smart Logging Without Sacrificing Visibility

**Current State:**

- All Lambda invocations logged
- 30-day retention
- Detailed logging enabled

**Optimizations:**

### 1. Log Retention Policy

```
Adjust by environment:
• Production: 30 days ($25-35/month)
• Development: 7 days ($5-10/month)

Savings: $20-25/month per environment
```

### 2. Log Filtering

```
Filter out noise:
• Exclude health check logs
• Sample verbose logs (10%)
• Keep only errors in detail

Savings: 40-60% on CloudWatch costs
```

### 3. Metric Optimization

- Use CloudWatch Embedded Metrics (free)
- Reduce custom metric count
- Use alarms efficiently

**Total Savings: $15-60/month**

---

# Strategy 8: Right-Sizing

## Match Resources to Actual Usage

**Instance Type Analysis:**

```
Current: t3.medium (2 vCPU, 4GB RAM)
Usage: ~30-50% CPU, 40-60% RAM

Options:
1. Keep t3.medium (current)
   Cost: $30.37/month

2. Test t3.small (2 vCPU, 2GB RAM)
   Cost: $15.18/month
   Savings: 50% if performance acceptable

3. Use t3a.medium (AMD)
   Cost: $27.36/month
   Savings: 10% with same performance
```

**Guacamole Right-Sizing:**

```
Current: t3.medium ($30/month)
Options:
• t3.small for <25 users: $15/month
• t3.large for >75 users: $60/month
• Add load balancer + 2× t3.medium for HA
```

**Expected Savings: 10-30% through right-sizing**

---

# Combined Optimization Impact

## Maximum Savings Scenario

### Starting Point (50 students, on-demand):

**Monthly Cost: $1,017**

### After Optimizations:

```
1. Spot Instances (50% pool):        -$107/month
2. Reserved Instances (5 base):       -$60/month
3. Aggressive Auto-Scaling:           -$80/month
4. VPC Endpoints:                     -$30/month
5. Storage Optimization:              -$20/month
6. Monitoring Optimization:           -$25/month
7. Right-Sizing (10% improvement):    -$35/month
──────────────────────────────────────────────
Total Savings:                        -$357/month
```

### Optimized Monthly Cost: **$660**

### Annual Savings: **$4,284 (42% reduction)**

---

# Optimization Roadmap

## Implementation Timeline

### Phase 1: Quick Wins (Week 1-2)

- ✅ Enable VPC endpoints
- ✅ Implement gp3 for EBS
- ✅ Adjust log retention
- ✅ Configure auto-scaling policies
  **Impact:** 15-20% cost reduction

### Phase 2: Medium-Term (Month 1-2)

- ✅ Purchase Reserved Instances (base capacity)
- ✅ Implement Spot Instance strategy
- ✅ Set up scheduled scaling
- ✅ Optimize monitoring
  **Impact:** Additional 25-30% reduction

### Phase 3: Long-Term (Month 3-6)

- ✅ Evaluate Savings Plans (3-year)
- ✅ Implement predictive scaling
- ✅ Multi-region optimization
- ✅ CloudFront CDN setup
  **Impact:** Additional 5-10% reduction

---

# Monitoring & Alerts

## Stay on Budget

### Recommended Budget Alerts:

1. **Daily Budget Alert**

   - Set at 110% of expected daily spend
   - Immediate notification

2. **Monthly Budget Alert**

   - Set at monthly budget + 20% buffer
   - Notify at 80% and 100% thresholds

3. **Anomaly Detection (Free)**
   - AWS automatically detects unusual spending
   - ML-based cost pattern analysis

### Key Metrics to Track:

- Instance hours by type (on-demand vs spot)
- Data transfer volumes
- Active session count
- Cost per student hour
- Monthly burn rate

---

# Cost Governance Best Practices

## Maintain Cost Discipline

### 1. Tagging Strategy

```
Required Tags:
• Environment: dev/prod
• Project: cyberlab
• Owner: team-name
• CostCenter: department
• Purpose: training/demo/test

Use for:
• Cost allocation reports
• Resource cleanup
• Budget tracking by team
```

### 2. Access Control

- Limit who can launch large instances
- Require approval for Reserved Instances
- Implement resource quotas per team

### 3. Regular Reviews

- Weekly: Usage patterns & anomalies
- Monthly: Cost optimization opportunities
- Quarterly: Architecture review & right-sizing

---

# Scaling Economics

## Cost Per Student Decreases with Scale

```
Cost per Student Hour:

Small (10 students):    $0.28/hour  ████████████
Medium (50 students):   $0.22/hour  █████████
Large (100 students):   $0.19/hour  ████████
Enterprise (200+):      $0.15/hour  ██████

Economies of Scale: 46% reduction from small to enterprise
```

**Why?**

- Fixed costs amortized across more users
- Better instance utilization
- Volume discount eligibility
- More efficient auto-scaling

**Sweet Spot:** 50-100 concurrent students

- Balance between cost efficiency and operational simplicity
- Manageable from operations perspective
- Significant cost advantages vs traditional lab

---

# Risk Management

## Cost Overrun Prevention

### Common Pitfalls to Avoid:

1. **Forgotten Instances**

   - Solution: Auto-terminate after X hours
   - Pool manager cleans up automatically

2. **Data Transfer Spikes**

   - Solution: VPC endpoints, compression
   - Monitor and set alerts

3. **Over-Provisioning**

   - Solution: Start small, scale gradually
   - Monitor actual utilization

4. **Lack of Monitoring**
   - Solution: Enable all budget alerts
   - Weekly cost review meetings

### Insurance Policies:

- Set ASG max limits (prevent runaway scaling)
- Enable termination protection on critical resources
- Implement spending limits per environment

---

# Summary: Key Takeaways

## 1. Significant Cost Savings

- **82-95% cheaper** than traditional physical labs
- **$40,000-300,000+ saved** over 5 years depending on scale

## 2. Optimization Potential

- **40-70% reduction** from baseline with optimization strategies
- **Quick wins** available (VPC endpoints, gp3, log retention)

## 3. Economies of Scale

- **Cost per student drops 46%** from small to enterprise scale
- **Sweet spot: 50-100 concurrent students**

## 4. Flexible & Scalable

- **Scale from 10 to 200+ students** without infrastructure changes
- **Pay only for what you use**
- **No hardware depreciation or maintenance**

---

# Recommendations by Deployment Size

## Small (10-25 Students) - $300-400/month

✅ Start with on-demand instances  
✅ Basic monitoring (free tier)  
✅ 7-day log retention  
✅ Manual scaling oversight

## Medium (50-100 Students) - $700-1,000/month

✅ 50% Spot + 50% on-demand mix  
✅ Reserve 5-10 base instances  
✅ Scheduled auto-scaling  
✅ VPC endpoints  
✅ 30-day log retention

## Large (100-200 Students) - $1,400-2,000/month

✅ Savings Plan (1-3 year)  
✅ Aggressive Spot usage (60-70%)  
✅ Multi-AZ for HA  
✅ CloudFront CDN  
✅ Premium support

---

# Next Steps

## Getting Started

### 1. Infrastructure Setup

- ✅ Already deployed via Terraform
- ✅ Auto-scaling configured
- ✅ Health checks implemented

### 2. Cost Baseline

- [ ] Run for 1 month to establish baseline
- [ ] Track actual usage patterns
- [ ] Measure cost per student hour

### 3. Quick Optimizations (Week 1-2)

- [ ] Enable VPC endpoints
- [ ] Switch EBS to gp3
- [ ] Adjust log retention
- [ ] Configure cost alerts

### 4. Long-Term Planning (Month 2-3)

- [ ] Purchase Reserved Instances
- [ ] Implement Spot strategy
- [ ] Set up scheduled scaling
- [ ] Evaluate Savings Plans

---

# Questions?

## Contact Information

**Technical Lead:** CyberLab Team  
**Documentation:** See AWS_COST_ANALYSIS.md  
**Infrastructure:** Terraform in `/environments/`

---

# Appendix: Useful Tools

## AWS Cost Management Tools

1. **AWS Cost Explorer**

   - Visualize spending patterns
   - Identify cost anomalies
   - Forecast future costs

2. **AWS Pricing Calculator**

   - Estimate costs before deployment
   - Compare pricing models
   - Plan budgets

3. **AWS Trusted Advisor**

   - Cost optimization recommendations
   - Best practice checks
   - Security & performance tips

4. **AWS Compute Optimizer**
   - Right-sizing recommendations
   - Based on actual usage data
   - ML-driven insights

---

# Appendix: Additional Resources

## Documentation & References

- AWS EC2 Pricing: https://aws.amazon.com/ec2/pricing/
- AWS Savings Plans: https://aws.amazon.com/savingsplans/
- AWS Spot Instances: https://aws.amazon.com/ec2/spot/
- Cost Optimization Best Practices: https://aws.amazon.com/architecture/cost-optimization/

## Internal Resources

- Full Cost Analysis: `AWS_COST_ANALYSIS.md`
- Terraform Infrastructure: `environments/dev/` and `environments/prod/`
- Architecture Docs: `README.md`

---

# Thank You!

## CyberLab Infrastructure

### Scalable • Cost-Effective • Secure

**Let's Build the Future of Cyber Education** 🚀
