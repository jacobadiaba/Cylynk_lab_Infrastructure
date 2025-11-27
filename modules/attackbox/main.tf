# modules/attackbox/main.tf
# AttackBox Pool Management Module

terraform {
  required_version = ">= 1.0"
}

# Local variables
locals {
  ami_id = var.custom_ami_id != "" ? var.custom_ami_id : data.aws_ami.kali.id
  
  common_tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-attackbox-pool"
      Component   = "AttackBox"
      Environment = var.environment
    }
  )
}

# Data source: Find latest Kali Linux AMI (if custom AMI not provided)
data "aws_ami" "kali" {
  most_recent = true
  owners      = ["679593333241"] # Offensive Security (Kali Linux)

  filter {
    name   = "name"
    values = ["kali-last-snapshot-amd64-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  filter {
    name   = "root-device-type"
    values = ["ebs"]
  }
}

# Data source: Find custom built AMI from Packer
data "aws_ami" "custom_attackbox" {
  count       = var.use_custom_ami ? 1 : 0
  most_recent = true
  owners      = ["self"]

  filter {
    name   = "name"
    values = ["${var.project_name}-attackbox-kali-*"]
  }

  filter {
    name   = "tag:Project"
    values = [var.project_name]
  }

  filter {
    name   = "tag:Component"
    values = ["AttackBox"]
  }
}

# CloudWatch Log Group for AttackBox
resource "aws_cloudwatch_log_group" "attackbox" {
  name              = "/cyberlab/${var.environment}/attackbox"
  retention_in_days = var.log_retention_days

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-${var.environment}-attackbox-logs"
    }
  )
}

# Launch Template for AttackBox instances
resource "aws_launch_template" "attackbox" {
  name_prefix   = "${var.project_name}-${var.environment}-attackbox-"
  description   = "Launch template for AttackBox instances"
  image_id      = var.use_custom_ami && length(data.aws_ami.custom_attackbox) > 0 ? data.aws_ami.custom_attackbox[0].id : local.ami_id
  instance_type = var.instance_type
  key_name      = var.key_name

  iam_instance_profile {
    name = var.iam_instance_profile_name
  }

  vpc_security_group_ids = [var.security_group_id]

  block_device_mappings {
    device_name = "/dev/sda1"

    ebs {
      volume_size           = var.root_volume_size
      volume_type           = "gp3"
      iops                  = var.root_volume_iops
      throughput            = var.root_volume_throughput
      encrypted             = true
      delete_on_termination = true
    }
  }

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
    instance_metadata_tags      = "enabled"
  }

  monitoring {
    enabled = var.enable_detailed_monitoring
  }

  tag_specifications {
    resource_type = "instance"
    tags = merge(
      local.common_tags,
      {
        Role = "AttackBox"
      }
    )
  }

  tag_specifications {
    resource_type = "volume"
    tags = merge(
      local.common_tags,
      {
        Role = "AttackBox"
      }
    )
  }

  tags = local.common_tags

  lifecycle {
    create_before_destroy = true
  }
}

# Auto Scaling Group for AttackBox pool
resource "aws_autoscaling_group" "attackbox_pool" {
  name                = "${var.project_name}-${var.environment}-attackbox-pool"
  vpc_zone_identifier = var.subnet_ids
  
  desired_capacity = var.pool_size
  min_size         = var.min_pool_size
  max_size         = var.max_pool_size

  health_check_type         = "EC2"
  health_check_grace_period = 300
  default_cooldown          = 300
  
  enabled_metrics = [
    "GroupDesiredCapacity",
    "GroupInServiceInstances",
    "GroupMinSize",
    "GroupMaxSize",
    "GroupTotalInstances"
  ]

  launch_template {
    id      = aws_launch_template.attackbox.id
    version = "$Latest"
  }

  instance_refresh {
    strategy = "Rolling"
    preferences {
      min_healthy_percentage = 50
    }
  }

  tag {
    key                 = "Name"
    value               = "${var.project_name}-${var.environment}-attackbox"
    propagate_at_launch = true
  }

  tag {
    key                 = "Project"
    value               = var.project_name
    propagate_at_launch = true
  }

  tag {
    key                 = "Environment"
    value               = var.environment
    propagate_at_launch = true
  }

  tag {
    key                 = "Role"
    value               = "AttackBox"
    propagate_at_launch = true
  }

  tag {
    key                 = "ManagedBy"
    value               = "Terraform"
    propagate_at_launch = true
  }

  lifecycle {
    create_before_destroy = true
    ignore_changes        = [desired_capacity]
  }
}

# Auto Scaling Policy - Scale Up
resource "aws_autoscaling_policy" "scale_up" {
  count                  = var.enable_auto_scaling ? 1 : 0
  name                   = "${var.project_name}-${var.environment}-attackbox-scale-up"
  scaling_adjustment     = var.scale_up_adjustment
  adjustment_type        = "ChangeInCapacity"
  cooldown               = var.scale_up_cooldown
  autoscaling_group_name = aws_autoscaling_group.attackbox_pool.name
}

# Auto Scaling Policy - Scale Down
resource "aws_autoscaling_policy" "scale_down" {
  count                  = var.enable_auto_scaling ? 1 : 0
  name                   = "${var.project_name}-${var.environment}-attackbox-scale-down"
  scaling_adjustment     = var.scale_down_adjustment
  adjustment_type        = "ChangeInCapacity"
  cooldown               = var.scale_down_cooldown
  autoscaling_group_name = aws_autoscaling_group.attackbox_pool.name
}

# CloudWatch Alarm - High CPU (trigger scale up)
resource "aws_cloudwatch_metric_alarm" "cpu_high" {
  count               = var.enable_auto_scaling ? 1 : 0
  alarm_name          = "${var.project_name}-${var.environment}-attackbox-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = "300"
  statistic           = "Average"
  threshold           = "70"
  alarm_description   = "Trigger scale up when CPU is high"
  alarm_actions       = [aws_autoscaling_policy.scale_up[0].arn]

  dimensions = {
    AutoScalingGroupName = aws_autoscaling_group.attackbox_pool.name
  }

  tags = var.tags
}

# CloudWatch Alarm - Low CPU (trigger scale down)
resource "aws_cloudwatch_metric_alarm" "cpu_low" {
  count               = var.enable_auto_scaling ? 1 : 0
  alarm_name          = "${var.project_name}-${var.environment}-attackbox-cpu-low"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = "300"
  statistic           = "Average"
  threshold           = "20"
  alarm_description   = "Trigger scale down when CPU is low"
  alarm_actions       = [aws_autoscaling_policy.scale_down[0].arn]

  dimensions = {
    AutoScalingGroupName = aws_autoscaling_group.attackbox_pool.name
  }

  tags = var.tags
}

# Scheduled Action - Scale down during off-hours (optional)
resource "aws_autoscaling_schedule" "scale_down_offhours" {
  count                  = var.enable_scheduled_scaling ? 1 : 0
  scheduled_action_name  = "${var.project_name}-${var.environment}-scale-down-offhours"
  min_size               = var.offhours_min_size
  max_size               = var.max_pool_size
  desired_capacity       = var.offhours_desired_size
  recurrence             = "0 22 * * *" # 10 PM daily
  autoscaling_group_name = aws_autoscaling_group.attackbox_pool.name
}

# Scheduled Action - Scale up during business hours (optional)
resource "aws_autoscaling_schedule" "scale_up_business" {
  count                  = var.enable_scheduled_scaling ? 1 : 0
  scheduled_action_name  = "${var.project_name}-${var.environment}-scale-up-business"
  min_size               = var.min_pool_size
  max_size               = var.max_pool_size
  desired_capacity       = var.pool_size
  recurrence             = "0 8 * * MON-FRI" # 8 AM weekdays
  autoscaling_group_name = aws_autoscaling_group.attackbox_pool.name
}

# SNS Topic for AttackBox notifications (optional)
resource "aws_sns_topic" "attackbox_notifications" {
  count = var.enable_notifications ? 1 : 0
  name  = "${var.project_name}-${var.environment}-attackbox-notifications"

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-${var.environment}-attackbox-notifications"
    }
  )
}

# Auto Scaling Notification
resource "aws_autoscaling_notification" "attackbox_notifications" {
  count       = var.enable_notifications ? 1 : 0
  group_names = [aws_autoscaling_group.attackbox_pool.name]

  notifications = [
    "autoscaling:EC2_INSTANCE_LAUNCH",
    "autoscaling:EC2_INSTANCE_TERMINATE",
    "autoscaling:EC2_INSTANCE_LAUNCH_ERROR",
    "autoscaling:EC2_INSTANCE_TERMINATE_ERROR",
  ]

  topic_arn = aws_sns_topic.attackbox_notifications[0].arn
}

# DynamoDB Table for Session Management (optional)
resource "aws_dynamodb_table" "sessions" {
  count          = var.enable_session_tracking ? 1 : 0
  name           = "${var.project_name}-${var.environment}-attackbox-sessions"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "session_id"
  range_key      = "timestamp"

  attribute {
    name = "session_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "N"
  }

  attribute {
    name = "student_id"
    type = "S"
  }

  attribute {
    name = "instance_id"
    type = "S"
  }

  global_secondary_index {
    name            = "StudentIndex"
    hash_key        = "student_id"
    range_key       = "timestamp"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "InstanceIndex"
    hash_key        = "instance_id"
    range_key       = "timestamp"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "expiration_time"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = var.environment == "production"
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-${var.environment}-attackbox-sessions"
    }
  )
}