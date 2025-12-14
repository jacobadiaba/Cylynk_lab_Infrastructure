# modules/cost-optimization/outputs.tf

output "budget_alerts_sns_topic_arn" {
  description = "ARN of the SNS topic for budget alerts"
  value       = aws_sns_topic.budget_alerts.arn
}

output "daily_budget_name" {
  description = "Name of the daily budget"
  value       = var.enable_daily_budget ? aws_budgets_budget.daily[0].name : null
}

output "monthly_budget_name" {
  description = "Name of the monthly budget"
  value       = var.enable_monthly_budget ? aws_budgets_budget.monthly[0].name : null
}

output "cost_anomaly_monitor_arns" {
  description = "ARNs of cost anomaly monitors"
  value       = aws_ce_anomaly_monitor.service_monitor[*].arn
}

output "cost_dashboard_name" {
  description = "Name of the CloudWatch cost dashboard"
  value       = var.enable_cost_dashboard ? aws_cloudwatch_dashboard.cost_overview[0].dashboard_name : null
}

output "compute_optimizer_status" {
  description = "Status of AWS Compute Optimizer enrollment"
  value       = var.enable_compute_optimizer ? aws_computeoptimizer_enrollment_status.this[0].status : "Not Enabled"
}
