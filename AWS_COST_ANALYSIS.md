# CyberLab Infrastructure - AWS Production Cost Analysis

**Analysis Date:** December 12, 2025  
**Region:** US East (N. Virginia) - us-east-1  
**Currency:** USD

---

## Executive Summary

| Scenario                   | Monthly Cost    | Annual Cost       |
| -------------------------- | --------------- | ----------------- |
| **Minimum (10 students)**  | $285 - $340     | $3,420 - $4,080   |
| **Moderate (50 students)** | $650 - $780     | $7,800 - $9,360   |
| **High (100 students)**    | $1,150 - $1,400 | $13,800 - $16,800 |
| **Peak (200+ students)**   | $2,200 - $2,800 | $26,400 - $33,600 |

---

## Fixed Costs (Always Running)

### 1. Networking Infrastructure

| Resource                     | Specification                 | Monthly Cost     | Notes                              |
| ---------------------------- | ----------------------------- | ---------------- | ---------------------------------- |
| **VPC**                      | 1 VPC with subnets            | $0               | Free                               |
| **NAT Gateway**              | 1 NAT Gateway + data transfer | $35-45           | $32.40/month + $0.045/GB processed |
| **Elastic IP**               | 1 EIP (Guacamole)             | $3.60            | $0.005/hour when not attached      |
| **VPC Endpoints** (optional) | DynamoDB, S3 endpoints        | $14-20           | $0.01/hour per endpoint + data     |
| **VPC Flow Logs** (optional) | CloudWatch Logs storage       | $5-10            | Based on traffic volume            |
| **TOTAL NETWORKING**         |                               | **$38-78/month** |                                    |

### 2. Guacamole Server (Gateway)

| Resource            | Specification               | Monthly Cost     | Notes                           |
| ------------------- | --------------------------- | ---------------- | ------------------------------- |
| **EC2 Instance**    | t3.small (2 vCPU, 2GB RAM)  | $15              | Always running                  |
| **EC2 Instance**    | t3.medium (2 vCPU, 4GB RAM) | $30              | Production recommendation       |
| **EBS Volume**      | 50GB gp3                    | $4               | Root volume                     |
| **Data Transfer**   | Outbound to students        | $9-18/TB         | $0.09/GB after first 100GB free |
| **TOTAL GUACAMOLE** |                             | **$38-52/month** | Using t3.medium + storage       |

### 3. DynamoDB Tables

| Table              | Usage                       | Monthly Cost    | Notes               |
| ------------------ | --------------------------- | --------------- | ------------------- |
| **Sessions**       | 100-1000 reads/writes daily | $2-5            | On-demand pricing   |
| **Instance Pool**  | 500-2000 reads/writes daily | $3-7            | Frequently accessed |
| **Usage Tracking** | 100-500 writes daily        | $1-3            | Write-heavy         |
| **Storage**        | ~1-5GB with TTL cleanup     | $0.25-1.25      | $0.25/GB-month      |
| **TOTAL DYNAMODB** |                             | **$6-16/month** | Scales with usage   |

### 4. Lambda Functions

| Function               | Invocations/Month | Monthly Cost    | Notes                      |
| ---------------------- | ----------------- | --------------- | -------------------------- |
| **create-session**     | 3,000-30,000      | $0.20-2         | On-demand session creation |
| **get-session-status** | 50,000-500,000    | $1-10           | Polling every 3 seconds    |
| **terminate-session**  | 3,000-30,000      | $0.20-2         | Session cleanup            |
| **usage-history**      | 1,000-10,000      | $0.10-1         | Dashboard queries          |
| **pool-manager**       | 43,200/month      | $0.50-1         | Runs every 1 minute        |
| **TOTAL LAMBDA**       |                   | **$2-16/month** | First 1M requests free     |

### 5. API Gateway

| Resource              | Requests/Month    | Monthly Cost    | Notes                      |
| --------------------- | ----------------- | --------------- | -------------------------- |
| **HTTP API**          | 100,000-1,000,000 | $1-10           | $1.00 per million requests |
| **Data Transfer**     | 10-100GB          | $0.90-9         | $0.09/GB                   |
| **TOTAL API GATEWAY** |                   | **$2-19/month** | Scales with traffic        |

### 6. CloudWatch & Monitoring

| Resource                     | Usage          | Monthly Cost    | Notes                                 |
| ---------------------------- | -------------- | --------------- | ------------------------------------- |
| **Logs Storage**             | 5-50GB         | $2.50-25        | $0.50/GB ingestion + $0.03/GB storage |
| **Metrics**                  | Custom metrics | $0-3            | 10 custom metrics free                |
| **Alarms**                   | 10-20 alarms   | $1-2            | $0.10 per alarm                       |
| **X-Ray Tracing** (optional) | 100K traces    | $0.50-5         | $5 per 1M traces                      |
| **TOTAL MONITORING**         |                | **$4-35/month** | Higher with detailed logging          |

### 7. S3 Storage (Optional)

| Resource          | Usage           | Monthly Cost    | Notes                       |
| ----------------- | --------------- | --------------- | --------------------------- |
| **Session Logs**  | 10-100GB        | $0.23-2.30      | $0.023/GB-month             |
| **Backups**       | 50-500GB        | $1.15-11.50     | AMI snapshots, configs      |
| **Data Transfer** | Out to Internet | $0.90-9/GB      | First 100GB free            |
| **TOTAL S3**      |                 | **$2-23/month** | Depends on retention policy |

---

## Variable Costs (Based on Usage)

### 8. AttackBox Instances (Auto-Scaling Pool)

#### Instance Pricing (t3.medium - Recommended)

- **On-Demand:** $0.0416/hour = $30.37/month per instance (24/7)
- **Spot Instances:** $0.0125-0.0250/hour = $9-18/month per instance (70-80% savings)
- **Reserved (1-year):** $0.0255/hour = $18.62/month per instance (38% savings)

#### EBS Storage per Instance

- **Root Volume:** 50GB gp3 = $4/month
- **Total per Instance:** $34.37/month (on-demand) or $22.62/month (reserved)

#### Usage Scenarios

**Scenario A: Low Usage (10 concurrent students)**

- **Min capacity:** 2 instances (always running)
- **Avg capacity:** 3 instances
- **Max capacity:** 10 instances
- **Monthly cost:** $103-240 (on-demand) or $68-180 (reserved)

**Scenario B: Moderate Usage (50 concurrent students)**

- **Min capacity:** 5 instances
- **Avg capacity:** 10 instances
- **Max capacity:** 25 instances
- **Monthly cost:** $344-860 (on-demand) or $226-565 (reserved)

**Scenario C: High Usage (100 concurrent students)**

- **Min capacity:** 10 instances
- **Avg capacity:** 20 instances
- **Max capacity:** 50 instances
- **Monthly cost:** $687-1,720 (on-demand) or $452-1,130 (reserved)

**Scenario D: Peak Usage (200+ concurrent students)**

- **Min capacity:** 20 instances
- **Avg capacity:** 40 instances
- **Max capacity:** 100 instances
- **Monthly cost:** $1,375-3,440 (on-demand) or $904-2,260 (reserved)

### 9. Data Transfer Costs

| Type                      | Volume    | Monthly Cost | Notes                      |
| ------------------------- | --------- | ------------ | -------------------------- |
| **Inbound**               | Any       | $0           | Free                       |
| **Inter-AZ**              | 100GB-1TB | $1-10        | $0.01/GB each direction    |
| **Outbound to Internet**  | 500GB-5TB | $45-405      | $0.09/GB after first 100GB |
| **CloudFront (optional)** | 1-10TB    | $85-750      | $0.085/GB for first 10TB   |

---

## Total Monthly Cost Breakdown

### Scenario 1: Small Production (10 concurrent students)

```
Fixed Infrastructure:        $90-180
AttackBox Pool (3 avg):     $103-240
Data Transfer:              $50-100
Monitoring & Logs:          $20-40
──────────────────────────────────
TOTAL:                      $263-560/month
RECOMMENDED:                $285-340/month
```

### Scenario 2: Medium Production (50 concurrent students)

```
Fixed Infrastructure:        $90-180
AttackBox Pool (10 avg):    $344-860
Data Transfer:              $150-300
Monitoring & Logs:          $40-80
──────────────────────────────────
TOTAL:                      $624-1,420/month
RECOMMENDED:                $650-780/month
```

### Scenario 3: Large Production (100 concurrent students)

```
Fixed Infrastructure:        $90-180
AttackBox Pool (20 avg):    $687-1,720
Data Transfer:              $250-500
Monitoring & Logs:          $60-120
──────────────────────────────────
TOTAL:                      $1,087-2,520/month
RECOMMENDED:                $1,150-1,400/month
```

### Scenario 4: Enterprise (200+ concurrent students)

```
Fixed Infrastructure:        $100-200
AttackBox Pool (40 avg):    $1,375-3,440
Data Transfer:              $400-800
Monitoring & Logs:          $100-200
──────────────────────────────────
TOTAL:                      $1,975-4,640/month
RECOMMENDED:                $2,200-2,800/month
```

---

## Cost Optimization Strategies

### 1. **Spot Instances for AttackBox Pool** (70-80% savings)

- Use Spot Instances for non-critical sessions
- Mix: 50% On-Demand (reliable) + 50% Spot (cost-effective)
- **Savings:** $300-1,500/month depending on scale

### 2. **Reserved Instances** (38% savings for 1-year commitment)

- Reserve minimum capacity (e.g., 10 instances for 50-student deployment)
- Use on-demand/spot for burst capacity
- **Savings:** $150-600/month depending on reserved count

### 3. **Savings Plans** (Up to 72% savings for 3-year commitment)

- Commit to $50-200/month compute usage
- Flexible across instance types and regions
- **Savings:** $200-800/month depending on commitment

### 4. **Auto-Scaling Optimization**

- Scale down aggressively during off-hours
- Use scheduled scaling for predictable patterns
- **Savings:** 20-40% on compute costs

### 5. **Data Transfer Optimization**

- Enable VPC endpoints for DynamoDB/S3 (saves inter-AZ transfer)
- Use CloudFront CDN for static assets
- Compress RDP/VNC traffic
- **Savings:** $50-200/month

### 6. **Storage Optimization**

- Use S3 lifecycle policies (Glacier after 30 days)
- Enable DynamoDB TTL for old sessions
- Use gp3 instead of gp2 EBS volumes
- **Savings:** $10-50/month

### 7. **Monitoring Optimization**

- Reduce log retention (7 days vs 30 days)
- Filter unnecessary logs
- Use metric filters instead of detailed logging
- **Savings:** $10-100/month

---

## Annual Cost Projections

| Scenario                       | Unoptimized (On-Demand) | Optimized (Spot + Reserved) | Annual Savings |
| ------------------------------ | ----------------------- | --------------------------- | -------------- |
| **Small (10 students)**        | $6,720                  | $3,420                      | $3,300 (49%)   |
| **Medium (50 students)**       | $17,040                 | $7,800                      | $9,240 (54%)   |
| **Large (100 students)**       | $30,240                 | $13,800                     | $16,440 (54%)  |
| **Enterprise (200+ students)** | $55,680                 | $26,400                     | $29,280 (53%)  |

---

## Scaling Economics

### Cost Per Student Hour

| Scale                 | On-Demand  | Spot/Reserved | Optimized  |
| --------------------- | ---------- | ------------- | ---------- |
| **Small (10)**        | $0.65/hour | $0.32/hour    | $0.28/hour |
| **Medium (50)**       | $0.52/hour | $0.26/hour    | $0.22/hour |
| **Large (100)**       | $0.48/hour | $0.23/hour    | $0.19/hour |
| **Enterprise (200+)** | $0.43/hour | $0.19/hour    | $0.15/hour |

**Economies of Scale:** Cost per student decreases by ~40% from small to enterprise scale.

---

## Hidden Costs to Consider

### 1. **One-Time Setup Costs**

- Domain registration: $12-50/year
- SSL certificates: $0 (Let's Encrypt) or $50-200/year (commercial)
- Professional services: $2,000-10,000 (initial setup)

### 2. **Operational Costs**

- DevOps engineer: $60,000-120,000/year (0.25-0.5 FTE)
- Support staff: $40,000-80,000/year (0.25-0.5 FTE)
- Security audits: $5,000-20,000/year

### 3. **Disaster Recovery**

- Multi-region backup: +30-50% of infrastructure cost
- Snapshot storage: $10-100/month

### 4. **Compliance & Security**

- AWS Shield Advanced: $3,000/month (DDoS protection)
- AWS WAF: $5-50/month (web firewall)
- GuardDuty: $4-50/month (threat detection)
- Security Hub: $0.0010 per check

---

## ROI Analysis

### Break-Even Analysis (vs Traditional Lab)

**Traditional Physical Lab Costs:**

- Hardware (50 workstations): $50,000-100,000
- Networking equipment: $10,000-20,000
- Physical space: $2,000-5,000/month
- Maintenance: $10,000-20,000/year
- Power/cooling: $500-1,500/month
- **Total Year 1:** $150,000-250,000
- **Annual operating:** $50,000-100,000

**CyberLab Cloud Solution (50 students):**

- Setup: $2,000-5,000 (one-time)
- Monthly: $650-780
- **Total Year 1:** $9,800-14,360
- **Annual operating (Year 2+):** $7,800-9,360

**Savings Year 1:** $135,000-235,000 (88-94%)  
**Savings Year 2+:** $42,000-90,000 per year (82-90%)

---

## Recommendations

### For Small Deployments (10-25 students)

1. Start with 2-3 on-demand instances
2. Use CloudWatch basic monitoring (free tier)
3. 7-day log retention
4. **Budget:** $300-400/month

### For Medium Deployments (50-100 students)

1. Mix: 5 reserved + auto-scaling to 25
2. Use Spot Instances for 50% of burst capacity
3. Enable detailed monitoring
4. 30-day log retention
5. **Budget:** $700-1,000/month

### For Large Deployments (100-200 students)

1. Reserve 15-20 instances (1-year commitment)
2. Use Spot Instances for burst (up to 50)
3. Multi-AZ for high availability
4. CloudFront for content delivery
5. 90-day log retention
6. **Budget:** $1,400-2,000/month

### For Enterprise (200+ students)

1. Reserve 30-40 instances (3-year Savings Plan)
2. Multi-region for disaster recovery
3. Premium support ($100+/month)
4. Advanced security (WAF, Shield)
5. Dedicated support team
6. **Budget:** $3,000-4,000/month

---

## Cost Alerts & Monitoring

### Recommended Budget Alerts

1. **Daily budget:** Set at 110% of expected daily spend
2. **Monthly budget:** Set at expected monthly + 20% buffer
3. **Anomaly detection:** Enable AWS Cost Anomaly Detection (free)

### Key Metrics to Monitor

- AttackBox instance hours
- Data transfer (outbound)
- DynamoDB read/write capacity
- Lambda invocations
- API Gateway requests

---

## Conclusion

The CyberLab infrastructure offers **significant cost savings** (82-94%) compared to traditional physical labs while providing:

- ✅ **Scalability:** Handle 10-200+ concurrent students
- ✅ **Flexibility:** Pay only for what you use
- ✅ **High availability:** 99.9% uptime
- ✅ **Global access:** Students anywhere, anytime
- ✅ **Low maintenance:** Automated scaling and management

**Recommended Starting Point:** Begin with small deployment ($300-400/month), measure actual usage, then optimize based on patterns.

**Key Success Factors:**

1. Implement auto-scaling with aggressive scale-down policies
2. Use Spot Instances for 30-50% of capacity
3. Monitor and optimize data transfer costs
4. Right-size instances based on actual utilization
5. Enable cost anomaly detection and budget alerts

---

**Questions or Need Custom Estimation?**  
Contact: AWS Cost Explorer or AWS Pricing Calculator  
Updated: December 2025
