# modules/security/main.tf

terraform {
  required_version = ">= 1.0"
}

# Security Group - Guacamole
resource "aws_security_group" "guacamole" {
  name        = "${var.project_name}-${var.environment}-guacamole-sg"
  description = "Security group for Guacamole server"
  vpc_id      = var.vpc_id

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-${var.environment}-guacamole-sg"
    }
  )
}

resource "aws_vpc_security_group_ingress_rule" "guacamole_https" {
  security_group_id = aws_security_group.guacamole.id
  description       = "HTTPS access"
  from_port         = 443
  to_port           = 443
  ip_protocol       = "tcp"
  cidr_ipv4         = "0.0.0.0/0"
}

resource "aws_vpc_security_group_ingress_rule" "guacamole_http" {
  security_group_id = aws_security_group.guacamole.id
  description       = "HTTP access (redirect to HTTPS)"
  from_port         = 80
  to_port           = 80
  ip_protocol       = "tcp"
  cidr_ipv4         = "0.0.0.0/0"
}

resource "aws_vpc_security_group_ingress_rule" "guacamole_ssh" {
  security_group_id = aws_security_group.guacamole.id
  description       = "SSH access"
  from_port         = 22
  to_port           = 22
  ip_protocol       = "tcp"
  cidr_ipv4         = var.allowed_ssh_cidr
}

resource "aws_vpc_security_group_egress_rule" "guacamole_all" {
  security_group_id = aws_security_group.guacamole.id
  description       = "Allow all outbound"
  ip_protocol       = "-1"
  cidr_ipv4         = "0.0.0.0/0"
}

# Security Group - VPN
resource "aws_security_group" "vpn" {
  name        = "${var.project_name}-${var.environment}-vpn-sg"
  description = "Security group for WireGuard VPN server"
  vpc_id      = var.vpc_id

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-${var.environment}-vpn-sg"
    }
  )
}

resource "aws_vpc_security_group_ingress_rule" "vpn_wireguard" {
  security_group_id = aws_security_group.vpn.id
  description       = "WireGuard VPN"
  from_port         = var.vpn_port
  to_port           = var.vpn_port
  ip_protocol       = "udp"
  cidr_ipv4         = "0.0.0.0/0"
}

resource "aws_vpc_security_group_ingress_rule" "vpn_http" {
  security_group_id = aws_security_group.vpn.id
  description       = "HTTP for config portal"
  from_port         = 80
  to_port           = 80
  ip_protocol       = "tcp"
  cidr_ipv4         = var.allowed_ssh_cidr
}

resource "aws_vpc_security_group_ingress_rule" "vpn_ssh" {
  security_group_id = aws_security_group.vpn.id
  description       = "SSH access"
  from_port         = 22
  to_port           = 22
  ip_protocol       = "tcp"
  cidr_ipv4         = var.allowed_ssh_cidr
}

resource "aws_vpc_security_group_egress_rule" "vpn_all" {
  security_group_id = aws_security_group.vpn.id
  description       = "Allow all outbound"
  ip_protocol       = "-1"
  cidr_ipv4         = "0.0.0.0/0"
}

# Security Group - AttackBox
resource "aws_security_group" "attackbox" {
  name        = "${var.project_name}-${var.environment}-attackbox-sg"
  description = "Security group for AttackBox instances"
  vpc_id      = var.vpc_id

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-${var.environment}-attackbox-sg"
    }
  )
}

resource "aws_vpc_security_group_ingress_rule" "attackbox_rdp_guacamole" {
  security_group_id            = aws_security_group.attackbox.id
  description                  = "RDP from Guacamole"
  from_port                    = 3389
  to_port                      = 3389
  ip_protocol                  = "tcp"
  referenced_security_group_id = aws_security_group.guacamole.id
}

resource "aws_vpc_security_group_ingress_rule" "attackbox_vnc_guacamole" {
  security_group_id            = aws_security_group.attackbox.id
  description                  = "VNC from Guacamole"
  from_port                    = 5901
  to_port                      = 5901
  ip_protocol                  = "tcp"
  referenced_security_group_id = aws_security_group.guacamole.id
}

resource "aws_vpc_security_group_ingress_rule" "attackbox_ssh_guacamole" {
  security_group_id            = aws_security_group.attackbox.id
  description                  = "SSH from Guacamole"
  from_port                    = 22
  to_port                      = 22
  ip_protocol                  = "tcp"
  referenced_security_group_id = aws_security_group.guacamole.id
}

resource "aws_vpc_security_group_ingress_rule" "attackbox_vpn" {
  security_group_id = aws_security_group.attackbox.id
  description       = "All traffic from VPN users"
  ip_protocol       = "-1"
  cidr_ipv4         = var.vpn_subnet_cidr
}

resource "aws_vpc_security_group_egress_rule" "attackbox_all" {
  security_group_id = aws_security_group.attackbox.id
  description       = "Allow all outbound"
  ip_protocol       = "-1"
  cidr_ipv4         = "0.0.0.0/0"
}

# Security Group - Lab VMs
resource "aws_security_group" "lab_vms" {
  name        = "${var.project_name}-${var.environment}-lab-vms-sg"
  description = "Security group for lab target VMs"
  vpc_id      = var.vpc_id

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-${var.environment}-lab-vms-sg"
    }
  )
}

resource "aws_vpc_security_group_ingress_rule" "lab_vms_attackbox" {
  security_group_id = aws_security_group.lab_vms.id
  description       = "All traffic from AttackBox pool"
  ip_protocol       = "-1"
  cidr_ipv4         = var.attackbox_subnet_cidr
}

resource "aws_vpc_security_group_ingress_rule" "lab_vms_vpn" {
  security_group_id = aws_security_group.lab_vms.id
  description       = "All traffic from VPN users"
  ip_protocol       = "-1"
  cidr_ipv4         = var.vpn_subnet_cidr
}

resource "aws_vpc_security_group_ingress_rule" "lab_vms_self" {
  security_group_id            = aws_security_group.lab_vms.id
  description                  = "Allow inter-VM communication in same lab"
  ip_protocol                  = "-1"
  referenced_security_group_id = aws_security_group.lab_vms.id
}

resource "aws_vpc_security_group_egress_rule" "lab_vms_all" {
  security_group_id = aws_security_group.lab_vms.id
  description       = "Allow all outbound"
  ip_protocol       = "-1"
  cidr_ipv4         = "0.0.0.0/0"
}

# IAM Role for EC2 Instances
resource "aws_iam_role" "ec2_role" {
  name = "${var.project_name}-${var.environment}-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-${var.environment}-ec2-role"
    }
  )
}

# IAM Policy for EC2 Instances
resource "aws_iam_role_policy" "ec2_policy" {
  name = "${var.project_name}-${var.environment}-ec2-policy"
  role = aws_iam_role.ec2_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ec2:DescribeInstances",
          "ec2:DescribeTags",
          "ec2:DescribeVolumes"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::${var.project_name}-${var.environment}-*",
          "arn:aws:s3:::${var.project_name}-${var.environment}-*/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogStreams"
        ]
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

# Attach SSM policy for Systems Manager
resource "aws_iam_role_policy_attachment" "ssm_policy" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# Attach CloudWatch agent policy
resource "aws_iam_role_policy_attachment" "cloudwatch_policy" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
}

# IAM Instance Profile
resource "aws_iam_instance_profile" "ec2_profile" {
  name = "${var.project_name}-${var.environment}-ec2-profile"
  role = aws_iam_role.ec2_role.name

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-${var.environment}-ec2-profile"
    }
  )
}

# Security Group - Lambda (Orchestrator)
resource "aws_security_group" "lambda" {
  name        = "${var.project_name}-${var.environment}-lambda-sg"
  description = "Security group for Lambda functions (orchestrator)"
  vpc_id      = var.vpc_id

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-${var.environment}-lambda-sg"
    }
  )
}

# Lambda needs to access DynamoDB, EC2 API, and Guacamole
resource "aws_vpc_security_group_egress_rule" "lambda_https" {
  security_group_id = aws_security_group.lambda.id
  description       = "HTTPS for AWS API calls"
  from_port         = 443
  to_port           = 443
  ip_protocol       = "tcp"
  cidr_ipv4         = "0.0.0.0/0"
}

resource "aws_vpc_security_group_egress_rule" "lambda_guacamole" {
  security_group_id            = aws_security_group.lambda.id
  description                  = "Access to Guacamole API"
  from_port                    = 443
  to_port                      = 443
  ip_protocol                  = "tcp"
  referenced_security_group_id = aws_security_group.guacamole.id
}

# SSH Key Pair
data "aws_key_pair" "existing" {
  key_name = var.existing_key_pair_name
}