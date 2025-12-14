# Cost Optimization Module

This module implements AWS cost optimization features including budget tracking, anomaly detection, and compute optimization recommendations.

## Features

### 1. AWS Budgets

- **Daily Budget**: Track daily spending with alerts at 80%, 100%, and 110% (forecasted) thresholds
- **Monthly Budget**: Track monthly spending with alerts at 50%, 80%, 100%, and 120% (forecasted) thresholds
- **EC2 Usage Budget**: Track EC2 instance hours to prevent runaway compute costs

### 2. AWS Compute Optimizer

- Automatic enrollment in AWS Compute Optimizer
- Provides right-sizing recommendations for:
  - EC2 instances
  - EBS volumes
  - Lambda functions
- ML-driven insights based on actual usage patterns

### 3. Cost Anomaly Detection

- **Service Monitor**: Detect unusual spending patterns by AWS service
- **Account Monitor**: Monitor linked accounts (for AWS Organizations)
- Daily or immediate alerts for spending anomalies
- Configurable threshold for anomaly impact

### 4. Cost Monitoring Dashboard

- CloudWatch dashboard with:
  - Estimated AWS charges
  - EC2 CPU utilization
  - DynamoDB capacity usage
  - Recent Lambda logs
- Real-time cost visibility

### 5. CloudWatch Alarms

- Daily cost threshold alarms
- SNS notifications for cost overruns
- Configurable thresholds

## Usage

```hcl
module "cost_optimization" {
  source = "../../modules/cost-optimization"

  project_name = "cyberlab"
  environment  = "dev"
  aws_region   = "us-east-1"

  # Budget Configuration
  enable_daily_budget    = true
  daily_budget_limit     = 15
  enable_monthly_budget  = true
  monthly_budget_limit   = 400
  budget_alert_emails    = ["admin@example.com", "finance@example.com"]

  # Compute Optimizer
  enable_compute_optimizer = true

  # Cost Anomaly Detection
  enable_cost_anomaly_detection = true
  anomaly_alert_emails          = ["admin@example.com"]
  anomaly_threshold_amount      = "10"

  # Monitoring
  enable_cost_dashboard = true
  enable_cost_alarms    = true
  log_retention_days    = 7

  tags = {
    ManagedBy = "Terraform"
  }
}
```

## Budget Alert Flow

```
Daily Spending > 80% threshold
    ↓
SNS Topic → Email Alert to budget_alert_emails
    ↓
Daily Spending > 100% threshold
    ↓
SNS Topic → Email Alert (CRITICAL)
    ↓
Forecasted Daily Spending > 110%
    ↓
SNS Topic → Email Alert (WARNING - Projected Overage)
```

## Cost Savings Impact

Based on the cost analysis presentation:

### Quick Wins (Implemented by this module):

- **Budget Tracking**: Prevent cost overruns through early alerts
- **Anomaly Detection**: Catch unexpected spending spikes immediately
- **Compute Optimizer**: Right-sizing recommendations can save 10-30%

### Expected Savings:

- **Budget Alerts**: Prevent $50-200/month in wasteful spending
- **Anomaly Detection**: Catch billing errors and anomalies
- **Compute Optimizer**: Identify over-provisioned instances (10-30% savings)

### Example Scenario (50-student deployment):

```
Without Optimization: $1,017/month
With Budget Management: $1,017/month (baseline)
  + Catch EC2 instances left running: -$60/month
  + Identify over-provisioned instances: -$80/month
  + Prevent data transfer spikes: -$30/month
──────────────────────────────────────────────
Optimized Cost: $847/month
Annual Savings: $2,040 (17% reduction)
```

## Inputs

| Name                          | Description                          | Type         | Default | Required |
| ----------------------------- | ------------------------------------ | ------------ | ------- | -------- |
| project_name                  | Project name for resource naming     | string       | n/a     | yes      |
| environment                   | Environment (dev/staging/production) | string       | n/a     | yes      |
| enable_daily_budget           | Enable daily budget alerts           | bool         | true    | no       |
| daily_budget_limit            | Daily budget limit in USD            | number       | 20      | no       |
| enable_monthly_budget         | Enable monthly budget alerts         | bool         | true    | no       |
| monthly_budget_limit          | Monthly budget limit in USD          | number       | 500     | no       |
| budget_alert_emails           | Email addresses for budget alerts    | list(string) | []      | yes      |
| enable_compute_optimizer      | Enable AWS Compute Optimizer         | bool         | true    | no       |
| enable_cost_anomaly_detection | Enable cost anomaly detection        | bool         | true    | no       |
| anomaly_threshold_amount      | Min anomaly amount to alert (USD)    | string       | "10"    | no       |
| log_retention_days            | CloudWatch log retention days        | number       | 7       | no       |

## Outputs

| Name                        | Description                         |
| --------------------------- | ----------------------------------- |
| budget_alerts_sns_topic_arn | ARN of SNS topic for budget alerts  |
| daily_budget_name           | Name of daily budget                |
| monthly_budget_name         | Name of monthly budget              |
| cost_anomaly_monitor_arns   | ARNs of anomaly monitors            |
| cost_dashboard_name         | Name of cost monitoring dashboard   |
| compute_optimizer_status    | Compute Optimizer enrollment status |

## Setup Instructions

### 1. Configure Budget Alerts

Set budget limits based on your deployment size:

**Development (10 students):**

```hcl
daily_budget_limit   = 10  # ~$9.50/day expected
monthly_budget_limit = 300 # ~$285/month expected
```

**Medium (50 students):**

```hcl
daily_budget_limit   = 25  # ~$22/day expected
monthly_budget_limit = 700 # ~$674/month expected
```

**Large (100 students):**

```hcl
daily_budget_limit   = 40  # ~$39/day expected
monthly_budget_limit = 1200 # ~$1,177/month expected
```

### 2. Subscribe to Email Alerts

After deployment, check email inboxes for SNS subscription confirmation emails and click "Confirm subscription" links.

### 3. Enable Compute Optimizer

Compute Optimizer requires 30 hours of instance data before providing recommendations. After deployment:

1. Wait 30+ hours
2. Visit AWS Console → Compute Optimizer
3. Review recommendations for:
   - Under-utilized instances (downsize)
   - Over-utilized instances (upsize)
   - Alternative instance types

### 4. Review Cost Dashboard

Access the CloudWatch dashboard:

```
AWS Console → CloudWatch → Dashboards → cyberlab-{env}-cost-overview
```

### 5. Configure Anomaly Alerts

Adjust the anomaly threshold based on your typical daily variance:

- Small deployments: $10-20
- Medium deployments: $30-50
- Large deployments: $50-100

## Cost Anomaly Detection Examples

### Example 1: EC2 Instance Left Running

```
Normal Daily Spend: $22
Anomaly Detected: $58
Impact: +$36 (164% increase)
Action: Email alert sent → Investigate EC2 console → Terminate forgotten instance
```

### Example 2: Data Transfer Spike

```
Normal Daily Spend: $22
Anomaly Detected: $45
Impact: +$23 (105% increase)
Cause: Unusual data egress from AttackBox instances
Action: Review VPC Flow Logs → Identify cause → Implement VPC endpoints
```

### Example 3: DynamoDB On-Demand Spike

```
Normal Daily Spend: $22
Anomaly Detected: $35
Impact: +$13 (59% increase)
Cause: Increased read/write activity on sessions table
Action: Review application logs → Check for polling issues → Optimize query patterns
```

## Monitoring and Maintenance

### Weekly Tasks

- Review budget vs actual spending
- Check for any anomaly alerts
- Review cost dashboard trends

### Monthly Tasks

- Review Compute Optimizer recommendations
- Implement right-sizing changes
- Update budget limits if needed
- Generate cost report for stakeholders

### Quarterly Tasks

- Evaluate Reserved Instance opportunities
- Review Savings Plan options
- Analyze cost trends and forecast
- Update cost optimization strategy

## Integration with Other Modules

This module integrates with:

- **Networking Module**: Provides VPC endpoints to reduce data transfer costs
- **Monitoring Module**: Shares SNS topics for unified alerting
- **Orchestrator Module**: Monitors Lambda and DynamoDB costs
- **AttackBox Module**: Tracks EC2 compute spending

## Troubleshooting

### Budget Alerts Not Received

1. Check SNS subscription status in AWS Console
2. Confirm emails in spam/junk folders
3. Verify budget_alert_emails variable is set correctly

### Compute Optimizer Showing No Data

- Wait 30+ hours after first deployment
- Ensure EC2 instances are running
- Check Compute Optimizer enrollment status

### Anomaly Alerts Too Frequent

- Increase anomaly_threshold_amount
- Change frequency from IMMEDIATE to DAILY
- Review normal spending patterns

### Cost Dashboard Not Showing Data

- CloudWatch billing metrics require up to 24 hours
- Ensure detailed billing is enabled in AWS account
- Check dashboard is in correct region (billing metrics are us-east-1)

## Best Practices

1. **Set Realistic Budgets**: Base limits on expected costs + 20% buffer
2. **Multiple Alert Levels**: Use 50%, 80%, 100% thresholds for gradual warnings
3. **Daily Monitoring**: Check cost dashboard at least once per day
4. **Act on Recommendations**: Implement Compute Optimizer suggestions within 1 week
5. **Tag Resources**: Ensure all resources have proper cost allocation tags
6. **Review Weekly**: Schedule weekly cost review meetings
7. **Test Alerts**: Temporarily lower budget limits to test alert delivery

## Cost of This Module

The cost optimization module itself has minimal costs:

- **AWS Budgets**: Free (first 2 budgets), $0.02/day per additional budget
- **Cost Anomaly Detection**: Free
- **Compute Optimizer**: Free
- **SNS**: $0.50 per 1M notifications (negligible for alerts)
- **CloudWatch Dashboard**: Free (first 3 dashboards)

**Total Cost**: ~$0.60-2/month

**ROI**: This module can save 10-30% on infrastructure costs, paying for itself 50-100x over.

## References

- [AWS Budgets Documentation](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html)
- [AWS Compute Optimizer](https://aws.amazon.com/compute-optimizer/)
- [Cost Anomaly Detection](https://aws.amazon.com/aws-cost-management/aws-cost-anomaly-detection/)
- [Cost Optimization Best Practices](https://aws.amazon.com/architecture/cost-optimization/)
