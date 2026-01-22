# environments/prod/main.tf

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = "production"
      ManagedBy   = "Terraform"
      Owner       = var.owner
      CostCenter  = var.cost_center
    }
  }
}

# Data sources
data "aws_caller_identity" "current" {}

# Local variables
locals {
  environment = "production"

  common_tags = {
    Project     = var.project_name
    Environment = local.environment
    ManagedBy   = "Terraform"
  }
}

# Networking Module
module "networking" {
  source = "../../modules/networking"

  project_name              = var.project_name
  environment               = local.environment
  aws_region                = var.aws_region
  vpc_cidr                  = var.vpc_cidr
  management_subnet_cidr    = var.management_subnet_cidr
  attackbox_subnet_cidr     = var.attackbox_subnet_cidr
  student_labs_cidr         = var.student_labs_cidr
  student_lab_subnet_count  = var.student_lab_subnet_count
  enable_nat_gateway        = var.enable_nat_gateway
  attackbox_public_subnet   = var.attackbox_public_subnet
  enable_flow_logs          = var.enable_flow_logs
  flow_logs_role_arn        = module.monitoring.flow_logs_role_arn
  flow_logs_destination_arn = module.monitoring.flow_logs_log_group_arn
  enable_vpc_endpoints      = var.enable_vpc_endpoints

  tags = local.common_tags
}

# Security Module
module "security" {
  source = "../../modules/security"

  project_name           = var.project_name
  environment            = local.environment
  vpc_id                 = module.networking.vpc_id
  allowed_ssh_cidr       = var.allowed_ssh_cidr
  vpn_port               = var.vpn_port
  vpn_subnet_cidr        = var.vpn_subnet_cidr
  attackbox_subnet_cidr  = module.networking.attackbox_pool_subnet_cidr
  existing_key_pair_name = var.existing_key_pair_name

  tags = local.common_tags
}

# Monitoring Module
module "monitoring" {
  source = "../../modules/monitoring"

  project_name                  = var.project_name
  environment                   = local.environment
  vpc_id                        = module.networking.vpc_id
  enable_sns_alarms             = var.enable_sns_alarms
  alarm_email                   = var.alarm_email
  log_retention_days            = var.log_retention_days
  enable_cost_anomaly_detection = var.enable_cost_anomaly_detection
  cost_anomaly_threshold        = var.cost_anomaly_threshold
  aws_region                    = var.aws_region
  tags                          = local.common_tags
}

# Guacamole Module
module "guacamole" {
  source = "../../modules/guacamole"

  project_name               = var.project_name
  environment                = local.environment
  instance_type              = var.guacamole_instance_type
  subnet_id                  = module.networking.management_subnet_id
  security_group_id          = module.security.guacamole_security_group_id
  iam_instance_profile_name  = module.security.ec2_instance_profile_name
  key_name                   = module.security.key_pair_name
  root_volume_size           = 50
  enable_detailed_monitoring = true
  domain_name                = var.guacamole_domain_name
  admin_email                = var.admin_email
  enable_lets_encrypt        = var.enable_lets_encrypt
  log_retention_days         = var.log_retention_days
  cpu_alarm_threshold        = 80
  memory_alarm_threshold     = 85
  alarm_sns_topic_arns       = compact([module.monitoring.sns_topic_arn])

  tags = local.common_tags
}

# AttackBox Module - Freemium Tier
module "attackbox_freemium" {
  source = "../../modules/attackbox"

  project_name              = var.project_name
  environment               = local.environment
  tier                      = "freemium"
  instance_type             = var.attackbox_tiers["freemium"].instance_type
  subnet_ids                = [module.networking.attackbox_pool_subnet_id]
  security_group_id         = module.security.attackbox_security_group_id
  iam_instance_profile_name = module.security.ec2_instance_profile_name
  key_name                  = module.security.key_pair_name
  guacamole_private_ip      = module.guacamole.private_ip

  pool_size     = var.attackbox_tiers["freemium"].pool_size
  min_pool_size = var.attackbox_tiers["freemium"].min_pool_size
  max_pool_size = var.attackbox_tiers["freemium"].max_pool_size

  warm_pool_min_size                    = var.attackbox_tiers["freemium"].warm_pool_min
  warm_pool_max_group_prepared_capacity = var.attackbox_tiers["freemium"].warm_pool_max

  # Use explicit AMI ID from environment tfvars (skip custom lookup)
  use_custom_ami = false
  custom_ami_id  = var.attackbox_ami_id

  enable_auto_scaling     = true
  enable_session_tracking = false
  enable_notifications    = true

  tags = local.common_tags
}

# AttackBox Module - Starter Tier
module "attackbox_starter" {
  source = "../../modules/attackbox"

  project_name              = var.project_name
  environment               = local.environment
  tier                      = "starter"
  instance_type             = var.attackbox_tiers["starter"].instance_type
  subnet_ids                = [module.networking.attackbox_pool_subnet_id]
  security_group_id         = module.security.attackbox_security_group_id
  iam_instance_profile_name = module.security.ec2_instance_profile_name
  key_name                  = module.security.key_pair_name
  guacamole_private_ip      = module.guacamole.private_ip

  pool_size     = var.attackbox_tiers["starter"].pool_size
  min_pool_size = var.attackbox_tiers["starter"].min_pool_size
  max_pool_size = var.attackbox_tiers["starter"].max_pool_size

  warm_pool_min_size                    = var.attackbox_tiers["starter"].warm_pool_min
  warm_pool_max_group_prepared_capacity = var.attackbox_tiers["starter"].warm_pool_max

  # Use explicit AMI ID from environment tfvars (skip custom lookup)
  use_custom_ami = false
  custom_ami_id  = var.attackbox_ami_id

  enable_auto_scaling     = true
  enable_session_tracking = false
  enable_notifications    = true

  tags = local.common_tags
}

# AttackBox Module - Pro Tier
module "attackbox_pro" {
  source = "../../modules/attackbox"

  project_name              = var.project_name
  environment               = local.environment
  tier                      = "pro"
  instance_type             = var.attackbox_tiers["pro"].instance_type
  subnet_ids                = [module.networking.attackbox_pool_subnet_id]
  security_group_id         = module.security.attackbox_security_group_id
  iam_instance_profile_name = module.security.ec2_instance_profile_name
  key_name                  = module.security.key_pair_name
  guacamole_private_ip      = module.guacamole.private_ip

  pool_size     = var.attackbox_tiers["pro"].pool_size
  min_pool_size = var.attackbox_tiers["pro"].min_pool_size
  max_pool_size = var.attackbox_tiers["pro"].max_pool_size

  warm_pool_min_size                    = var.attackbox_tiers["pro"].warm_pool_min
  warm_pool_max_group_prepared_capacity = var.attackbox_tiers["pro"].warm_pool_max

  # Use explicit AMI ID from environment tfvars (skip custom lookup)
  use_custom_ami = false
  custom_ami_id  = var.attackbox_ami_id

  enable_auto_scaling     = true
  enable_session_tracking = false
  enable_notifications    = true

  tags = local.common_tags
}

# Orchestrator Module - Session Management API
module "orchestrator" {
  source = "../../modules/orchestrator"

  project_name = var.project_name
  environment  = local.environment
  aws_region   = var.aws_region

  # Networking
  enable_vpc_config        = false
  vpc_id                   = module.networking.vpc_id
  subnet_ids               = [module.networking.management_subnet_id]
  lambda_security_group_id = module.security.lambda_security_group_id

  # AttackBox Integration - Multi-tier pools
  attackbox_pools = {
    freemium = {
      asg_name = module.attackbox_freemium.autoscaling_group_name
      asg_arn  = module.attackbox_freemium.autoscaling_group_arn
    }
    starter = {
      asg_name = module.attackbox_starter.autoscaling_group_name
      asg_arn  = module.attackbox_starter.autoscaling_group_arn
    }
    pro = {
      asg_name = module.attackbox_pro.autoscaling_group_name
      asg_arn  = module.attackbox_pro.autoscaling_group_arn
    }
  }
  attackbox_security_group_id = module.security.attackbox_security_group_id

  # Guacamole Integration
  guacamole_private_ip     = module.guacamole.private_ip
  guacamole_public_ip      = module.guacamole.public_ip
  guacamole_api_url        = var.guacamole_domain_name != "" ? "https://${var.guacamole_domain_name}/guacamole" : ""
  guacamole_admin_username = var.guacamole_admin_username
  guacamole_admin_password = var.guacamole_admin_password

  # RDP credentials (must match AttackBox AMI)
  rdp_username = var.rdp_username
  rdp_password = var.rdp_password

  # Session Configuration
  session_ttl_hours        = var.session_ttl_hours
  max_sessions_per_student = var.max_sessions_per_student

  # API Configuration
  api_stage_name  = "v1"
  enable_api_key  = var.enable_orchestrator_api_key
  allowed_origins = var.orchestrator_allowed_origins

  # Moodle Integration
  moodle_webhook_secret = var.moodle_webhook_secret

  # Monitoring
  log_retention_days   = var.log_retention_days
  enable_xray_tracing  = false
  alarm_sns_topic_arns = compact([module.monitoring.sns_topic_arn])

  tags = local.common_tags
}

# Cost Optimization Module
module "cost_optimization" {
  source = "../../modules/cost-optimization"

  project_name = var.project_name
  environment  = local.environment
  aws_region   = var.aws_region

  enable_daily_budget   = false
  enable_monthly_budget = false
  budget_alert_emails   = [var.admin_email]

  enable_ec2_usage_budget     = false
  enable_compute_optimizer    = true
  enable_cost_dashboard       = true
  enable_cost_alarms          = true
  enable_cost_anomaly_detection = var.enable_cost_anomaly_detection
  anomaly_alert_emails          = [var.admin_email]

  log_retention_days = var.log_retention_days
  tags               = local.common_tags
}

