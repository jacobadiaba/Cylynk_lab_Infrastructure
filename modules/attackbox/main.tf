# modules/attackbox/main.tf
# AttackBox Pool Management Module

terraform {
  required_version = ">= 1.0"
}

# Local variables
locals {
  ami_id = var.custom_ami_id != "" ? var.custom_ami_id : data.aws_ami.kali.id
  
  # Include tier in naming for multi-pool support
  name_prefix = "${var.project_name}-${var.environment}-attackbox-${var.tier}"
  
  common_tags = merge(
    var.tags,
    {
      Name        = "${local.name_prefix}-pool"
      Component   = "AttackBox"
      Environment = var.environment
      Tier        = var.tier
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
  name              = "/cyberlab/${var.environment}/attackbox-${var.tier}"
  retention_in_days = var.log_retention_days

  tags = merge(
    var.tags,
    {
      Name = "${local.name_prefix}-logs"
      Tier = var.tier
    }
  )
}

# Launch Template for AttackBox instances
resource "aws_launch_template" "attackbox" {
  name_prefix   = "${local.name_prefix}-"
  description   = "Launch template for AttackBox ${var.tier} tier instances"
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
        Tier = var.tier
      }
    )
  }

  tag_specifications {
    resource_type = "volume"
    tags = merge(
      local.common_tags,
      {
        Role = "AttackBox"
        Tier = var.tier
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
  name                = "${local.name_prefix}-pool"
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
    "GroupTotalInstances",
    "GroupAndWarmPoolDesiredCapacity",
    "GroupAndWarmPoolTotalCapacity",
    "WarmPoolDesiredCapacity",
    "WarmPoolMinSize",
    "WarmPoolPendingCapacity",
    "WarmPoolTerminatingCapacity",
    "WarmPoolTotalCapacity",
    "WarmPoolWarmedCapacity"
  ]

  launch_template {
    id      = aws_launch_template.attackbox.id
    version = "$Latest"
  }

  # Warm Pool Configuration
  # Pre-started instances in stopped state for fast launches (30-60 seconds)
  warm_pool {
    pool_state                  = "Stopped"  # Instances stopped to save cost
    min_size                    = var.warm_pool_min_size
    max_group_prepared_capacity = var.warm_pool_max_group_prepared_capacity
    
    instance_reuse_policy {
      reuse_on_scale_in = true  # Recycle instances back to warm pool
    }
  }

  instance_refresh {
    strategy = "Rolling"
    preferences {
      min_healthy_percentage = 50
    }
  }

  tag {
    key                 = "Name"
    value               = "${local.name_prefix}"
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
    key                 = "Tier"
    value               = var.tier
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
  name                   = "${local.name_prefix}-scale-up"
  scaling_adjustment     = var.scale_up_adjustment
  adjustment_type        = "ChangeInCapacity"
  cooldown               = var.scale_up_cooldown
  autoscaling_group_name = aws_autoscaling_group.attackbox_pool.name
}

# Auto Scaling Policy - Scale Down
resource "aws_autoscaling_policy" "scale_down" {
  count                  = var.enable_auto_scaling ? 1 : 0
  name                   = "${local.name_prefix}-scale-down"
  scaling_adjustment     = var.scale_down_adjustment
  adjustment_type        = "ChangeInCapacity"
  cooldown               = var.scale_down_cooldown
  autoscaling_group_name = aws_autoscaling_group.attackbox_pool.name
}

# CloudWatch Alarm - High CPU (trigger scale up)
resource "aws_cloudwatch_metric_alarm" "cpu_high" {
  count               = var.enable_auto_scaling ? 1 : 0
  alarm_name          = "${local.name_prefix}-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = "300"
  statistic           = "Average"
  threshold           = "70"
  alarm_description   = "Trigger scale up when CPU is high for ${var.tier} tier"
  alarm_actions       = [aws_autoscaling_policy.scale_up[0].arn]

  dimensions = {
    AutoScalingGroupName = aws_autoscaling_group.attackbox_pool.name
  }

  tags = merge(var.tags, { Tier = var.tier })
}

# CloudWatch Alarm - Low CPU (trigger scale down)
resource "aws_cloudwatch_metric_alarm" "cpu_low" {
  count               = var.enable_auto_scaling ? 1 : 0
  alarm_name          = "${local.name_prefix}-cpu-low"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = "300"
  statistic           = "Average"
  threshold           = "20"
  alarm_description   = "Trigger scale down when CPU is low for ${var.tier} tier"
  alarm_actions       = [aws_autoscaling_policy.scale_down[0].arn]

  dimensions = {
    AutoScalingGroupName = aws_autoscaling_group.attackbox_pool.name
  }

  tags = merge(var.tags, { Tier = var.tier })
}

# Scheduled scaling removed - users are global with different timezones
# Rely on dynamic scaling based on demand instead

# SNS Topic for AttackBox notifications (optional)
resource "aws_sns_topic" "attackbox_notifications" {
  count = var.enable_notifications ? 1 : 0
  name  = "${local.name_prefix}-notifications"

  tags = merge(
    var.tags,
    {
      Name = "${local.name_prefix}-notifications"
      Tier = var.tier
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
# Note: This is a legacy table - main session tracking is done via orchestrator module
resource "aws_dynamodb_table" "sessions" {
  count          = var.enable_session_tracking ? 1 : 0
  name           = "${local.name_prefix}-sessions"
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
      Name = "${local.name_prefix}-sessions"
      Tier = var.tier
    }
  )
}