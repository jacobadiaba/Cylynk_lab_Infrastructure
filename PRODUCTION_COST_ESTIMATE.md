# CyberLab Production Cost Estimate

**Date:** December 17, 2025  
**Version:** 1.0 - Tier-Based Architecture  
**Region:** US East (N. Virginia) - us-east-1

---

## Current Architecture Overview

CyberLab has implemented a **tier-based AttackBox system** with three subscription plans, each with dedicated EC2 pools managed by AWS Auto Scaling Groups with warm pools.

### Architecture Components

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         CYBERLAB ARCHITECTURE                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────────────────┐   │
│  │   Moodle    │────▶│ API Gateway │────▶│   Lambda Functions      │   │
│  │   Plugin    │     │  (HTTP API) │     │  - create-session       │   │
│  └─────────────┘     └─────────────┘     │  - get-session-status   │   │
│                                          │  - terminate-session    │   │
│                                          │  - pool-manager         │   │
│                                          │  - usage-history        │   │
│                                          │  - admin-sessions       │   │
│                                          └───────────┬─────────────┘   │
│                                                      │                  │
│  ┌───────────────────────────────────────────────────┼──────────────┐  │
│  │                     VPC (10.1.0.0/16)             │              │  │
│  │  ┌─────────────────┐                              ▼              │  │
│  │  │   Guacamole     │◀──────────────┬─────────────────────────┐  │  │
│  │  │   (t3.medium)   │               │      DynamoDB Tables    │  │  │
│  │  │   RDP Gateway   │               │  - Sessions             │  │  │
│  │  └────────┬────────┘               │  - Instance Pool        │  │  │
│  │           │                        │  - Usage Tracking       │  │  │
│  │           ▼                        └─────────────────────────┘  │  │
│  │  ┌────────────────────────────────────────────────────────────┐ │  │
│  │  │              TIER-BASED ATTACKBOX POOLS                    │ │  │
│  │  │                                                            │ │  │
│  │  │  FREEMIUM (t3.small)  │  STARTER (t3.medium) │ PRO (t3.large)│ │  │
│  │  │  ├─ Running: 1        │  ├─ Running: 1       │ ├─ Running: 1 │ │  │
│  │  │  ├─ Warm Pool: 2-5    │  ├─ Warm Pool: 2-5   │ ├─ Warm Pool: 3-8│ │
│  │  │  └─ Max: 5            │  └─ Max: 5           │ └─ Max: 10    │ │  │
│  │  │                                                            │ │  │
│  │  └────────────────────────────────────────────────────────────┘ │  │
│  │                                                                  │  │
│  │  ┌─────────────┐                                                │  │
│  │  │ NAT Gateway │ ──▶ Internet                                   │  │
│  │  └─────────────┘                                                │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Part 1: Current Production Cost Estimate

### Assumptions

| Assumption            | Value                              | Notes                              |
| --------------------- | ---------------------------------- | ---------------------------------- |
| **Total Users**       | 100 active users                   | Monthly active users               |
| **User Distribution** | 60% Freemium, 30% Starter, 10% Pro | Based on typical SaaS distribution |
| **Concurrent Peak**   | 20-30 users                        | ~25% of active users at peak       |
| **Session Duration**  | 1 hour average                     | Per lab session                    |
| **Sessions per User** | 8 sessions/month                   | 2 sessions/week average            |
| **Operating Hours**   | 24/7 availability                  | Required for global access         |
| **Data per Session**  | 300 MB average                     | RDP traffic                        |

---

### 1. Fixed Infrastructure Costs (Monthly)

#### 1.1 Networking (Optimized - AttackBox in Public Subnet)

| Resource               | Configuration    | Monthly Cost | Calculation                  |
| ---------------------- | ---------------- | ------------ | ---------------------------- |
| VPC                    | 1 VPC, 4 subnets | $0.00        | Free                         |
| ~~NAT Gateway~~        | ~~Disabled~~     | ~~$0.00~~    | **Saved $34.65/month!**      |
| Elastic IP (Guacamole) | 1 EIP attached   | $0.00        | Free when attached           |
| **TOTAL NETWORKING**   |                  | **$0.00**    | AttackBox uses public subnet |

> **Cost Optimization Applied:** AttackBox instances are placed in a public subnet with security groups
> blocking all internet inbound traffic. This eliminates the NAT Gateway cost (~$35/month) while
> maintaining security through security groups that only allow traffic from Guacamole.

#### 1.2 Guacamole Gateway Server

| Resource            | Configuration    | Monthly Cost | Calculation              |
| ------------------- | ---------------- | ------------ | ------------------------ |
| EC2 Instance        | t3.medium (24/7) | $30.37       | $0.0416/hour × 720 hours |
| EBS Volume          | 50 GB gp3        | $4.00        | $0.08/GB                 |
| **TOTAL GUACAMOLE** |                  | **$34.37**   |                          |

#### 1.3 Serverless Components

| Resource             | Usage Estimate      | Monthly Cost | Calculation              |
| -------------------- | ------------------- | ------------ | ------------------------ |
| **DynamoDB**         |                     |              |                          |
| Sessions Table       | 50K read/write ops  | $3.00        | On-demand pricing        |
| Instance Pool Table  | 200K read/write ops | $5.00        | High-frequency polling   |
| Usage Tracking Table | 20K write ops       | $1.50        | Session tracking         |
| Storage              | ~2 GB               | $0.50        | $0.25/GB                 |
| **Lambda Functions** |                     |              |                          |
| create-session       | 800 invocations     | $0.02        | 100 users × 8 sessions   |
| get-session-status   | 480K invocations    | $1.00        | 800 sessions × 600 polls |
| terminate-session    | 800 invocations     | $0.02        | Matches create           |
| pool-manager         | 43.2K invocations   | $0.50        | Every minute             |
| usage-history        | 5K invocations      | $0.10        | Dashboard queries        |
| admin-sessions       | 2K invocations      | $0.05        | Admin operations         |
| **API Gateway**      |                     |              |                          |
| HTTP API Requests    | 500K requests       | $0.50        | $1.00 per million        |
| **TOTAL SERVERLESS** |                     | **$12.19**   |                          |

#### 1.4 Monitoring & Logging

| Resource                  | Configuration | Monthly Cost | Calculation  |
| ------------------------- | ------------- | ------------ | ------------ |
| CloudWatch Logs Ingestion | 10 GB         | $5.00        | $0.50/GB     |
| CloudWatch Logs Storage   | 10 GB         | $0.30        | $0.03/GB     |
| CloudWatch Alarms         | 15 alarms     | $1.50        | $0.10/alarm  |
| SNS Notifications         | 1K messages   | $0.50        | Email alerts |
| **TOTAL MONITORING**      |               | **$7.30**    |              |

#### Fixed Infrastructure Total

| Category        | Monthly Cost | Notes                      |
| --------------- | ------------ | -------------------------- |
| Networking      | $0.00        | NAT Gateway eliminated     |
| Guacamole       | $34.37       |                            |
| Serverless      | $12.19       |                            |
| Monitoring      | $7.30        |                            |
| **TOTAL FIXED** | **$53.86**   | Saved $34.65/month on NAT! |

---

### 2. Variable Costs: AttackBox Pools (Monthly)

#### 2.1 Current Tier Configuration

```hcl
# From terraform.tfvars (Cost-Optimized Instance Types)
attackbox_tiers = {
  freemium = {
    instance_type = "t3.micro"   # $0.0104/hour - sufficient for basic labs
    pool_size     = 1            # Running instances
    min_pool_size = 1
    max_pool_size = 5
    warm_pool_min = 2            # Stopped instances
    warm_pool_max = 5
  }
  starter = {
    instance_type = "t3.small"   # $0.0208/hour - good for standard labs
    pool_size     = 1
    min_pool_size = 1
    max_pool_size = 5
    warm_pool_min = 2
    warm_pool_max = 5
  }
  pro = {
    instance_type = "t3.medium"  # $0.0416/hour - handles 90% of advanced labs
    pool_size     = 1
    min_pool_size = 1
    max_pool_size = 10
    warm_pool_min = 3
    warm_pool_max = 8
  }
}
```

> **Cost Optimization Applied:** Downsized instance types by one tier. t3.micro is sufficient for
> basic labs (Nmap, recon), t3.small handles most standard labs, and t3.medium covers 90% of
> advanced work. Only memory-intensive tools (large Burp scans, heavy Metasploit) may need larger.

#### 2.2 Instance Costs by Tier

**Freemium Tier (t3.micro - 2 vCPU, 1GB RAM)**

| Resource            | Count    | Hours/Month | Unit Cost  | Monthly Cost |
| ------------------- | -------- | ----------- | ---------- | ------------ |
| Running Instance    | 1        | 720         | $0.0104/hr | $7.49        |
| Warm Pool (stopped) | 2-3 avg  | -           | $0.00/hr   | $0.00        |
| EBS (running)       | 1 × 50GB | -           | $0.08/GB   | $4.00        |
| EBS (warm pool)     | 3 × 50GB | -           | $0.08/GB   | $12.00       |
| **FREEMIUM TOTAL**  |          |             |            | **$23.49**   |

**Starter Tier (t3.small - 2 vCPU, 2GB RAM)**

| Resource            | Count    | Hours/Month | Unit Cost  | Monthly Cost |
| ------------------- | -------- | ----------- | ---------- | ------------ |
| Running Instance    | 1        | 720         | $0.0208/hr | $14.98       |
| Warm Pool (stopped) | 2-3 avg  | -           | $0.00/hr   | $0.00        |
| EBS (running)       | 1 × 50GB | -           | $0.08/GB   | $4.00        |
| EBS (warm pool)     | 3 × 50GB | -           | $0.08/GB   | $12.00       |
| **STARTER TOTAL**   |          |             |            | **$30.98**   |

**Pro Tier (t3.medium - 2 vCPU, 4GB RAM)**

| Resource            | Count    | Hours/Month | Unit Cost  | Monthly Cost |
| ------------------- | -------- | ----------- | ---------- | ------------ |
| Running Instance    | 1        | 720         | $0.0416/hr | $29.95       |
| Warm Pool (stopped) | 3-5 avg  | -           | $0.00/hr   | $0.00        |
| EBS (running)       | 1 × 50GB | -           | $0.08/GB   | $4.00        |
| EBS (warm pool)     | 5 × 50GB | -           | $0.08/GB   | $20.00       |
| **PRO TOTAL**       |          |             |            | **$53.95**   |

#### 2.3 Burst Capacity (Peak Usage)

During peak hours, additional instances may be launched from warm pool:

| Scenario        | Extra Instances | Avg Hours/Month | Cost      |
| --------------- | --------------- | --------------- | --------- |
| Freemium burst  | 2 × t3.micro    | 100 hrs         | $2.08     |
| Starter burst   | 2 × t3.small    | 80 hrs          | $3.33     |
| Pro burst       | 2 × t3.medium   | 50 hrs          | $4.16     |
| **BURST TOTAL** |                 |                 | **$9.57** |

#### AttackBox Pools Total

| Tier                | Base Cost   | Burst Cost | Total       |
| ------------------- | ----------- | ---------- | ----------- |
| Freemium            | $23.49      | $2.08      | $25.57      |
| Starter             | $30.98      | $3.33      | $34.31      |
| Pro                 | $53.95      | $4.16      | $58.11      |
| **TOTAL ATTACKBOX** | **$108.42** | **$9.57**  | **$117.99** |

---

### 3. Data Transfer Costs (Monthly)

| Type                    | Volume   | Unit Cost | Monthly Cost |
| ----------------------- | -------- | --------- | ------------ |
| Outbound (RDP to users) | 240 GB\* | $0.09/GB  | $21.60       |
| First 100 GB free       | -100 GB  | $0.00     | -$9.00       |
| Inter-AZ (Lambda ↔ EC2) | 20 GB    | $0.01/GB  | $0.20        |
| **TOTAL DATA TRANSFER** |          |           | **$12.80**   |

\*Calculation: 800 sessions × 300 MB = 240 GB

---

### 4. Total Monthly Production Cost

| Category             | Monthly Cost | % of Total | Notes                          |
| -------------------- | ------------ | ---------- | ------------------------------ |
| Fixed Infrastructure | $53.86       | 29.2%      | NAT Gateway eliminated         |
| AttackBox Pools      | $117.99      | 64.0%      | Downsized instances            |
| Data Transfer        | $12.80       | 6.9%       |                                |
| **Buffer (5%)**      | $9.23        | -          |                                |
| **TOTAL MONTHLY**    | **$193.88**  | 100%       | **Saved $101.46 vs original!** |

### Annual Cost Projection

| Period     | Cost          | vs Original ($295) |
| ---------- | ------------- | ------------------ |
| Monthly    | $193.88       | -$101.46/month     |
| Quarterly  | $581.64       | -$304.38           |
| **Annual** | **$2,326.56** | **-$1,217.52/yr**  |

---

### 5. Cost Per User/Session Analysis

| Metric                         | Value |
| ------------------------------ | ----- |
| **Cost per Active User/Month** | $1.94 |
| **Cost per Session**           | $0.24 |
| **Cost per Session Hour**      | $0.24 |

#### By Tier

| Tier     | Users | Sessions/Mo | Cost/Session |
| -------- | ----- | ----------- | ------------ |
| Freemium | 60    | 480         | $0.07        |
| Starter  | 30    | 240         | $0.22        |
| Pro      | 10    | 80          | $1.15        |

---

### 6. Scaling Projections

| Scale          | Users | Monthly Cost | Cost/User |
| -------------- | ----- | ------------ | --------- |
| **Current**    | 100   | $295         | $2.95     |
| **Growth**     | 250   | $520         | $2.08     |
| **Scale**      | 500   | $920         | $1.84     |
| **Enterprise** | 1000  | $1,650       | $1.65     |

_Economies of scale reduce per-user cost by ~44% at 1000 users_

---

## Part 2: Future Cost Optimization Techniques

### Summary of Potential Savings

| Optimization           | Monthly Savings       | Implementation Effort |
| ---------------------- | --------------------- | --------------------- |
| Reserved Instances     | $50-80 (30-40%)       | Low                   |
| Spot Instances         | $40-60 (25-35%)       | Medium                |
| Scheduled Scaling      | $20-40 (10-20%)       | Low                   |
| Instance Right-Sizing  | $10-30 (5-15%)        | Low                   |
| Lambda Optimization    | $3-5 (2-3%)           | Low                   |
| **Combined Potential** | **$100-180 (35-60%)** |                       |

---

### Optimization 1: Reserved Instances (30-40% Savings)

**What:** Commit to 1-year or 3-year term for predictable baseline capacity.

**Current State:** All instances are On-Demand pricing.

**Recommendation:** Reserve the minimum running instances per tier.

| Tier      | Instance    | On-Demand/Mo | 1-Year Reserved | Savings       |
| --------- | ----------- | ------------ | --------------- | ------------- |
| Freemium  | t3.small    | $14.98       | $9.29           | $5.69 (38%)   |
| Starter   | t3.medium   | $29.95       | $18.57          | $11.38 (38%)  |
| Pro       | t3.large    | $59.90       | $37.14          | $22.76 (38%)  |
| **Total** | 3 instances | $104.83      | $65.00          | **$39.83/mo** |

**Annual Savings:** $477.96

**Implementation:**

```bash
# Purchase via AWS Console or CLI
aws ec2 purchase-reserved-instances-offering \
  --instance-type t3.medium \
  --instance-count 1 \
  --offering-type "No Upfront"
```

---

### Optimization 2: Spot Instances for Burst Capacity (60-70% Savings)

**What:** Use Spot Instances for overflow capacity beyond running + warm pool.

**Current State:** All burst instances are On-Demand.

**Recommendation:** Configure Mixed Instances Policy in ASG.

| Type      | On-Demand/Hr | Spot Price/Hr | Savings |
| --------- | ------------ | ------------- | ------- |
| t3.small  | $0.0208      | $0.0062       | 70%     |
| t3.medium | $0.0416      | $0.0125       | 70%     |
| t3.large  | $0.0832      | $0.0250       | 70%     |

**Implementation:**

```hcl
# In modules/attackbox/main.tf
resource "aws_autoscaling_group" "attackbox_pool" {
  mixed_instances_policy {
    instances_distribution {
      on_demand_base_capacity                  = 1  # Always-on
      on_demand_percentage_above_base_capacity = 0  # Rest is Spot
      spot_allocation_strategy                 = "capacity-optimized"
    }

    launch_template {
      launch_template_specification {
        launch_template_id = aws_launch_template.attackbox.id
        version            = "$Latest"
      }

      override {
        instance_type = var.instance_type
      }
      override {
        instance_type = var.backup_instance_type  # Fallback
      }
    }
  }
}
```

**Risk Mitigation:**

- Spot interruption notice: 2 minutes
- Save session state to S3 on interruption
- Automatic failover to On-Demand if Spot unavailable

**Monthly Savings:** $13-25 on burst capacity

---

### Optimization 3: Scheduled Scaling (10-20% Savings)

**What:** Scale down during predictable low-usage periods.

**Current State:** Pools run 24/7 at same capacity.

**Recommendation:** Implement time-based scaling rules.

```
Weekday Schedule (GMT):
├── 00:00-06:00: Minimum (1 running per tier)
├── 06:00-09:00: Ramp up
├── 09:00-18:00: Full capacity
├── 18:00-22:00: Moderate
└── 22:00-00:00: Scale down

Weekend Schedule:
└── Minimum capacity (warm pools only)
```

**Implementation:**

```hcl
# Scheduled scaling actions
resource "aws_autoscaling_schedule" "scale_down_night" {
  scheduled_action_name  = "scale-down-night"
  autoscaling_group_name = aws_autoscaling_group.attackbox_pool.name
  min_size               = 0
  max_size               = var.max_pool_size
  desired_capacity       = 0
  recurrence             = "0 0 * * *"  # Midnight daily
}

resource "aws_autoscaling_schedule" "scale_up_morning" {
  scheduled_action_name  = "scale-up-morning"
  autoscaling_group_name = aws_autoscaling_group.attackbox_pool.name
  min_size               = var.min_pool_size
  max_size               = var.max_pool_size
  desired_capacity       = var.pool_size
  recurrence             = "0 6 * * 1-5"  # 6 AM weekdays
}
```

**Monthly Savings:** $20-40 (assumes 30% reduction in running hours)

---

### Optimization 4: Compute Savings Plans (Up to 66% Savings)

**What:** Commit to a dollar amount of compute usage per hour for 1-3 years.

**Current State:** No savings plan commitment.

**Recommendation:** After 3 months of stable usage, commit to baseline compute.

| Commitment         | Hourly Commit | Monthly Cost | Savings vs On-Demand |
| ------------------ | ------------- | ------------ | -------------------- |
| 1-Year No Upfront  | $0.15/hr      | $108         | 37%                  |
| 1-Year All Upfront | $0.13/hr      | $94          | 45%                  |
| 3-Year All Upfront | $0.09/hr      | $65          | 66%                  |

**Benefits over Reserved Instances:**

- Flexible across instance types (t3.small → t3.large)
- Applies to Lambda compute too
- Automatically applies to any EC2 usage

**Monthly Savings:** $50-100 depending on commitment

---

### Optimization 5: Instance Right-Sizing

**What:** Analyze actual CPU/memory usage and downsize if over-provisioned.

**Current State:** t3.small/medium/large based on tier assumptions.

**Monitoring Required:**

```bash
# CloudWatch metrics to monitor
- CPUUtilization (target: 40-70%)
- MemoryUtilization (requires CloudWatch agent)
- NetworkIn/NetworkOut
```

**Potential Adjustments:**

| Current             | If <30% CPU | Savings   |
| ------------------- | ----------- | --------- |
| t3.large (Pro)      | t3.medium   | $29.95/mo |
| t3.medium (Starter) | t3.small    | $14.97/mo |

**Implementation:** Monitor for 2-4 weeks before making changes.

---

### Optimization 6: Lambda Memory/Duration Optimization

**What:** Right-size Lambda memory allocation and reduce execution time.

**Current State:** Default 128-256MB memory, variable duration.

**Optimization Targets:**

| Function           | Current       | Optimized   | Savings |
| ------------------ | ------------- | ----------- | ------- |
| get-session-status | 128MB, 3s avg | 128MB, 1.5s | 50%     |
| pool-manager       | 256MB, 5s avg | 128MB, 3s   | 60%     |
| create-session     | 128MB, 2s avg | 128MB, 1s   | 50%     |

**Implementation:**

- Use AWS Lambda Power Tuning
- Reduce API calls within functions
- Cache frequently accessed data

**Monthly Savings:** $1-3 (Lambda costs are already minimal)

---

### Optimization 7: Data Transfer Optimization

**What:** Reduce outbound data transfer costs.

**Techniques:**

1. **RDP Compression:** Enable in Guacamole

   ```json
   {
     "enable-compression": true,
     "color-depth": 16,
     "resize-method": "display-update"
   }
   ```

2. **CloudFront for Static Assets:** Cache Guacamole client files

   - First 1 TB: $0.085/GB (vs $0.09/GB direct)
   - Faster delivery to users

3. **VPC Endpoints:** Already implemented for S3/DynamoDB

**Monthly Savings:** $3-8

---

### Optimization 8: Storage Optimization

**What:** Reduce EBS and snapshot costs.

**Techniques:**

1. **gp3 vs gp2:** Already using gp3 ✓

2. **Reduce EBS Size:** If AttackBox uses <30GB, reduce to 30GB

   - Current: 50GB × $0.08 = $4.00/instance
   - Optimized: 30GB × $0.08 = $2.40/instance
   - **Savings:** $1.60/instance

3. **Snapshot Lifecycle:** Delete old warm pool snapshots

   ```hcl
   resource "aws_dlm_lifecycle_policy" "attackbox_snapshots" {
     description        = "AttackBox snapshot lifecycle"
     execution_role_arn = aws_iam_role.dlm_role.arn

     policy_details {
       schedule {
         retain_rule {
           count = 3  # Keep only 3 snapshots
         }
       }
     }
   }
   ```

**Monthly Savings:** $10-20

---

### Optimization 9: DynamoDB Optimization

**What:** Switch from On-Demand to Provisioned capacity for predictable workloads.

**Current State:** On-Demand pricing (flexible but more expensive).

**After 3 months of data:**

- If read/write patterns are predictable, switch to Provisioned
- Use Auto Scaling for Provisioned capacity

| Table          | Current (On-Demand) | Provisioned | Savings |
| -------------- | ------------------- | ----------- | ------- |
| Sessions       | $3.00               | $1.50       | 50%     |
| Instance Pool  | $5.00               | $2.50       | 50%     |
| Usage Tracking | $1.50               | $0.75       | 50%     |

**Monthly Savings:** $4-6

---

### Optimization 10: Multi-Region Considerations

**What:** Deploy in region closest to users for reduced latency and potentially lower costs.

**Current:** us-east-1 (N. Virginia)

**If users are in Europe/Africa:**

- eu-west-1 (Ireland): Similar pricing
- af-south-1 (Cape Town): Higher pricing but lower latency

**Latency Impact on RDP:**
| Region | Latency to Ghana | User Experience |
|--------|------------------|-----------------|
| us-east-1 | 150-200ms | Acceptable |
| eu-west-1 | 80-120ms | Good |
| af-south-1 | 30-50ms | Excellent |

**Trade-off:** af-south-1 is ~20% more expensive but provides better UX.

---

## Implementation Roadmap

### Phase 1: Quick Wins (Week 1-2)

- [ ] Implement scheduled scaling
- [ ] Enable RDP compression
- [ ] Set up cost monitoring/alerts

**Expected Savings:** $20-40/month

### Phase 2: Reserved Capacity (Month 2)

- [ ] Analyze 30-day usage patterns
- [ ] Purchase Reserved Instances for baseline
- [ ] Implement Spot for burst capacity

**Expected Savings:** $50-80/month

### Phase 3: Advanced Optimization (Month 3-4)

- [ ] Right-size instances based on metrics
- [ ] Evaluate Savings Plans commitment
- [ ] Optimize Lambda functions
- [ ] Switch DynamoDB to Provisioned

**Expected Savings:** $30-50/month

---

## Summary

### Current Production Cost

|                         | Monthly | Annual |
| ----------------------- | ------- | ------ |
| **Current (On-Demand)** | $295    | $3,544 |

### Optimized Production Cost

| Optimization Level  | Monthly | Annual | Savings |
| ------------------- | ------- | ------ | ------- |
| Quick Wins          | $255    | $3,060 | 14%     |
| + Reserved/Spot     | $185    | $2,220 | 37%     |
| + Full Optimization | $140    | $1,680 | **53%** |

### Cost Per User at Scale

| Scale      | Current Model | Fully Optimized |
| ---------- | ------------- | --------------- |
| 100 users  | $2.95/user    | $1.40/user      |
| 500 users  | $1.84/user    | $0.90/user      |
| 1000 users | $1.65/user    | $0.75/user      |

---

**Next Steps:**

1. Deploy to production with current configuration
2. Monitor for 30 days to establish baselines
3. Implement Phase 1 optimizations
4. Evaluate Reserved/Savings Plan commitments

**Document Maintained By:** Infrastructure Team  
**Last Updated:** December 17, 2025
