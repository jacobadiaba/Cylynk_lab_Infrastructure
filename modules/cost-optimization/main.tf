# modules/cost-optimization/main.tf
# Cost Optimization - Budgets, Compute Optimizer, and Cost Anomaly Detection

terraform {
  required_version = ">= 1.0"
}

locals {
  common_tags = merge(
    var.tags,
    {
      Component   = "CostOptimization"
      Environment = var.environment
    }
  )
}

# =============================================================================
# AWS Budgets - Daily and Monthly Cost Tracking
# =============================================================================

# Daily Budget Alert
resource "aws_budgets_budget" "daily" {
  count = var.enable_daily_budget ? 1 : 0

  name              = "${var.project_name}-${var.environment}-daily-budget"
  budget_type       = "COST"
  limit_amount      = var.daily_budget_limit
  limit_unit        = "USD"
  time_unit         = "DAILY"
  time_period_start = formatdate("YYYY-MM-01_00:00", timestamp())

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = var.budget_alert_emails
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = var.budget_alert_emails
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 110
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = var.budget_alert_emails
  }

  depends_on = [aws_sns_topic.budget_alerts]
}

# Monthly Budget Alert
resource "aws_budgets_budget" "monthly" {
  count = var.enable_monthly_budget ? 1 : 0

  name              = "${var.project_name}-${var.environment}-monthly-budget"
  budget_type       = "COST"
  limit_amount      = var.monthly_budget_limit
  limit_unit        = "USD"
  time_unit         = "MONTHLY"
  time_period_start = formatdate("YYYY-MM-01_00:00", timestamp())

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 50
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = var.budget_alert_emails
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = var.budget_alert_emails
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = var.budget_alert_emails
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 120
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = var.budget_alert_emails
  }

  depends_on = [aws_sns_topic.budget_alerts]
}

# EC2 Instance Usage Budget (Hours)
resource "aws_budgets_budget" "ec2_usage" {
  count = var.enable_ec2_usage_budget ? 1 : 0

  name              = "${var.project_name}-${var.environment}-ec2-hours"
  budget_type       = "USAGE"
  limit_amount      = var.ec2_usage_hours_limit
  limit_unit        = "hrs"
  time_unit         = "MONTHLY"
  time_period_start = formatdate("YYYY-MM-01_00:00", timestamp())

  cost_types {
    include_credit             = false
    include_discount           = true
    include_other_subscription = true
    include_recurring          = true
    include_refund             = false
    include_subscription       = true
    include_support            = true
    include_tax                = true
    include_upfront            = true
    use_blended                = false
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = var.budget_alert_emails
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = var.budget_alert_emails
  }

  depends_on = [aws_sns_topic.budget_alerts]
}

# =============================================================================
# SNS Topic for Budget Alerts
# =============================================================================

resource "aws_sns_topic" "budget_alerts" {
  name              = "${var.project_name}-${var.environment}-budget-alerts"
  display_name      = "Budget Alerts for ${var.project_name} ${var.environment}"
  kms_master_key_id = var.enable_sns_encryption ? aws_kms_key.budget_alerts[0].id : null

  tags = local.common_tags
}

resource "aws_sns_topic_subscription" "budget_alerts_email" {
  count     = length(var.budget_alert_emails)
  topic_arn = aws_sns_topic.budget_alerts.arn
  protocol  = "email"
  endpoint  = var.budget_alert_emails[count.index]
}

# KMS Key for SNS Encryption (optional)
resource "aws_kms_key" "budget_alerts" {
  count = var.enable_sns_encryption ? 1 : 0

  description             = "KMS key for budget alert SNS topic encryption"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  tags = merge(
    local.common_tags,
    {
      Name = "${var.project_name}-${var.environment}-budget-alerts-kms"
    }
  )
}

resource "aws_kms_alias" "budget_alerts" {
  count         = var.enable_sns_encryption ? 1 : 0
  name          = "alias/${var.project_name}-${var.environment}-budget-alerts"
  target_key_id = aws_kms_key.budget_alerts[0].key_id
}

# =============================================================================
# AWS Compute Optimizer
# =============================================================================

# Compute Optimizer Enrollment (Account-level setting)
resource "aws_computeoptimizer_enrollment_status" "this" {
  count  = var.enable_compute_optimizer ? 1 : 0
  status = "Active"
}

# =============================================================================
# Cost Anomaly Detection
# =============================================================================

# Cost Anomaly Monitor - Overall Spend
resource "aws_ce_anomaly_monitor" "service_monitor" {
  count = var.enable_cost_anomaly_detection ? 1 : 0

  name              = "${var.project_name}-${var.environment}-service-anomaly-monitor"
  monitor_type      = "DIMENSIONAL"
  monitor_dimension = "SERVICE"

  tags = local.common_tags
}

# Cost Anomaly Subscription
resource "aws_ce_anomaly_subscription" "anomaly_alerts" {
  count = var.enable_cost_anomaly_detection ? 1 : 0

  name      = "${var.project_name}-${var.environment}-anomaly-subscription"
  frequency = "DAILY" # IMMEDIATE or DAILY

  monitor_arn_list = [
    aws_ce_anomaly_monitor.service_monitor[0].arn
  ]

  subscriber {
    type    = "EMAIL"
    address = var.anomaly_alert_emails[0]
  }

  dynamic "subscriber" {
    for_each = length(var.anomaly_alert_emails) > 1 ? slice(var.anomaly_alert_emails, 1, length(var.anomaly_alert_emails)) : []
    content {
      type    = "EMAIL"
      address = subscriber.value
    }
  }

  dynamic "subscriber" {
    for_each = var.anomaly_alert_sns_arn != "" ? [1] : []
    content {
      type    = "SNS"
      address = var.anomaly_alert_sns_arn
    }
  }

  threshold_expression {
    dimension {
      key           = "ANOMALY_TOTAL_IMPACT_ABSOLUTE"
      values        = [var.anomaly_threshold_amount]
      match_options = ["GREATER_THAN_OR_EQUAL"]
    }
  }

  tags = local.common_tags
}

# =============================================================================
# CloudWatch Dashboard for Cost Monitoring
# =============================================================================

resource "aws_cloudwatch_dashboard" "cost_overview" {
  count          = var.enable_cost_dashboard ? 1 : 0
  dashboard_name = "${var.project_name}-${var.environment}-cost-overview"

  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/Billing", "EstimatedCharges", { stat = "Maximum", label = "Estimated Charges" }]
          ]
          period = 21600
          stat   = "Maximum"
          region = "us-east-1" # Billing metrics are only in us-east-1
          title  = "Estimated AWS Charges"
          yAxis = {
            left = {
              min = 0
            }
          }
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/EC2", "CPUUtilization", { stat = "Average", label = "Average CPU" }]
          ]
          period = 300
          stat   = "Average"
          region = var.aws_region
          title  = "EC2 CPU Utilization"
          yAxis = {
            left = {
              min = 0
              max = 100
            }
          }
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/DynamoDB", "ConsumedReadCapacityUnits", { stat = "Sum", label = "Read Capacity" }],
            ["AWS/DynamoDB", "ConsumedWriteCapacityUnits", { stat = "Sum", label = "Write Capacity" }]
          ]
          period = 300
          stat   = "Sum"
          region = var.aws_region
          title  = "DynamoDB Capacity Usage"
        }
      },
      {
        type = "log"
        properties = {
          query   = "SOURCE '/aws/lambda/${var.project_name}-${var.environment}-pool-manager' | fields @timestamp, @message | sort @timestamp desc | limit 20"
          region  = var.aws_region
          title   = "Recent Pool Manager Logs"
          stacked = false
        }
      }
    ]
  })
}

# =============================================================================
# CloudWatch Alarms for Cost Thresholds
# =============================================================================

# Daily Cost Threshold Alarm
resource "aws_cloudwatch_metric_alarm" "daily_cost_threshold" {
  count = var.enable_cost_alarms ? 1 : 0

  alarm_name          = "${var.project_name}-${var.environment}-daily-cost-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "EstimatedCharges"
  namespace           = "AWS/Billing"
  period              = 21600 # 6 hours
  statistic           = "Maximum"
  threshold           = var.daily_budget_limit * 0.9 # Alert at 90% of daily budget
  alarm_description   = "This metric monitors daily AWS costs"
  alarm_actions       = var.cost_alarm_sns_arn != "" ? [var.cost_alarm_sns_arn] : []

  dimensions = {
    Currency = "USD"
  }

  tags = local.common_tags
}

# =============================================================================
# Right-Sizing Recommendations (Lambda for scheduled reports)
# =============================================================================

# Lambda Execution Role
resource "aws_iam_role" "cost_optimizer_lambda" {
  count = var.enable_cost_optimizer_lambda ? 1 : 0

  name = "${var.project_name}-${var.environment}-cost-optimizer-lambda"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "cost_optimizer_lambda_basic" {
  count      = var.enable_cost_optimizer_lambda ? 1 : 0
  role       = aws_iam_role.cost_optimizer_lambda[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "cost_optimizer_lambda_permissions" {
  count = var.enable_cost_optimizer_lambda ? 1 : 0
  name  = "${var.project_name}-${var.environment}-cost-optimizer-permissions"
  role  = aws_iam_role.cost_optimizer_lambda[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "compute-optimizer:GetEC2InstanceRecommendations",
          "compute-optimizer:GetEBSVolumeRecommendations",
          "compute-optimizer:GetLambdaFunctionRecommendations",
          "ec2:DescribeInstances",
          "cloudwatch:GetMetricStatistics",
          "ce:GetCostAndUsage",
          "ce:GetCostForecast"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = aws_sns_topic.budget_alerts.arn
      }
    ]
  })
}

# CloudWatch Log Group for Cost Optimizer Lambda
resource "aws_cloudwatch_log_group" "cost_optimizer_lambda" {
  count             = var.enable_cost_optimizer_lambda ? 1 : 0
  name              = "/aws/lambda/${var.project_name}-${var.environment}-cost-optimizer"
  retention_in_days = var.log_retention_days
  tags              = local.common_tags
}

# Note: Lambda function code needs to be created separately
# This is a placeholder for the Lambda function that would generate cost reports
# The actual Lambda function would:
# 1. Query Compute Optimizer for recommendations
# 2. Analyze current spending patterns
# 3. Generate a report
# 4. Send via SNS or email
