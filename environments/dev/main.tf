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
      Environment = "dev"
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
  environment = "dev"

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

# Storage Module
module "storage" {
  source = "../../modules/storage"

  project_name              = var.project_name
  environment               = local.environment
  aws_region                = var.aws_region
  enable_versioning         = true
  enable_lifecycle_rules    = true
  lifecycle_transition_days = 90
  lifecycle_expiration_days = 365

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

