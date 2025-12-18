# modules/attackbox/outputs.tf

output "tier" {
  description = "Plan tier for this AttackBox pool"
  value       = var.tier
}

output "autoscaling_group_name" {
  description = "Name of the Auto Scaling Group"
  value       = aws_autoscaling_group.attackbox_pool.name
}

output "autoscaling_group_arn" {
  description = "ARN of the Auto Scaling Group"
  value       = aws_autoscaling_group.attackbox_pool.arn
}

output "launch_template_id" {
  description = "ID of the launch template"
  value       = aws_launch_template.attackbox.id
}

output "launch_template_latest_version" {
  description = "Latest version of the launch template"
  value       = aws_launch_template.attackbox.latest_version
}

output "ami_id" {
  description = "AMI ID being used for AttackBox instances"
  value       = var.use_custom_ami && length(data.aws_ami.custom_attackbox) > 0 ? data.aws_ami.custom_attackbox[0].id : data.aws_ami.kali.id
}

output "ami_name" {
  description = "AMI name being used"
  value       = var.use_custom_ami && length(data.aws_ami.custom_attackbox) > 0 ? data.aws_ami.custom_attackbox[0].name : data.aws_ami.kali.name
}

output "pool_configuration" {
  description = "Current pool configuration"
  value = {
    tier             = var.tier
    desired_capacity = aws_autoscaling_group.attackbox_pool.desired_capacity
    min_size         = aws_autoscaling_group.attackbox_pool.min_size
    max_size         = aws_autoscaling_group.attackbox_pool.max_size
    instance_type    = var.instance_type
  }
}

output "log_group_name" {
  description = "CloudWatch log group name"
  value       = aws_cloudwatch_log_group.attackbox.name
}

output "log_group_arn" {
  description = "CloudWatch log group ARN"
  value       = aws_cloudwatch_log_group.attackbox.arn
}

output "sns_topic_arn" {
  description = "SNS topic ARN for notifications"
  value       = var.enable_notifications ? aws_sns_topic.attackbox_notifications[0].arn : null
}

output "session_table_name" {
  description = "DynamoDB table name for session tracking"
  value       = var.enable_session_tracking ? aws_dynamodb_table.sessions[0].name : null
}

output "session_table_arn" {
  description = "DynamoDB table ARN for session tracking"
  value       = var.enable_session_tracking ? aws_dynamodb_table.sessions[0].arn : null
}

output "scale_up_policy_arn" {
  description = "ARN of scale up policy"
  value       = var.enable_auto_scaling ? aws_autoscaling_policy.scale_up[0].arn : null
}

output "scale_down_policy_arn" {
  description = "ARN of scale down policy"
  value       = var.enable_auto_scaling ? aws_autoscaling_policy.scale_down[0].arn : null
}

output "management_commands" {
  description = "Useful AWS CLI commands for managing the AttackBox pool"
  value = {
    list_instances        = "aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names ${aws_autoscaling_group.attackbox_pool.name} --query 'AutoScalingGroups[0].Instances[*].[InstanceId,LifecycleState,HealthStatus]' --output table"
    scale_up              = "aws autoscaling set-desired-capacity --auto-scaling-group-name ${aws_autoscaling_group.attackbox_pool.name} --desired-capacity $((${var.pool_size} + 5))"
    scale_down            = "aws autoscaling set-desired-capacity --auto-scaling-group-name ${aws_autoscaling_group.attackbox_pool.name} --desired-capacity ${var.min_pool_size}"
    terminate_instance    = "aws autoscaling terminate-instance-in-auto-scaling-group --instance-id INSTANCE_ID --should-decrement-desired-capacity"
    get_activity          = "aws autoscaling describe-scaling-activities --auto-scaling-group-name ${aws_autoscaling_group.attackbox_pool.name} --max-records 10"
    update_launch_template = "aws autoscaling update-auto-scaling-group --auto-scaling-group-name ${aws_autoscaling_group.attackbox_pool.name} --launch-template LaunchTemplateId=${aws_launch_template.attackbox.id},Version='$Latest'"
  }
}

output "cost_estimation" {
  description = "Monthly cost estimation for the AttackBox pool"
  value = {
    tier                  = var.tier
    stopped_storage       = "~$${var.pool_size * 0.10 * var.root_volume_size}/month (EBS storage)"
    running_instance_cost = "$${var.instance_type == \"t3.large\" ? \"0.0832\" : var.instance_type == \"t3.medium\" ? \"0.0416\" : var.instance_type == \"t3.small\" ? \"0.0208\" : \"0.0104\"}/hour per instance"
    pool_running_24x7     = "~$${var.pool_size * (var.instance_type == \"t3.large\" ? 60 : var.instance_type == \"t3.medium\" ? 30 : var.instance_type == \"t3.small\" ? 15 : 7.5)}/month (if all running)"
    note                  = "Actual costs depend on usage patterns and how long instances run"
  }
}