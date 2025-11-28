# modules/security/outputs.tf

output "guacamole_security_group_id" {
  description = "ID of Guacamole security group"
  value       = aws_security_group.guacamole.id
}

output "vpn_security_group_id" {
  description = "ID of VPN security group"
  value       = aws_security_group.vpn.id
}

output "attackbox_security_group_id" {
  description = "ID of AttackBox security group"
  value       = aws_security_group.attackbox.id
}

output "lab_vms_security_group_id" {
  description = "ID of Lab VMs security group"
  value       = aws_security_group.lab_vms.id
}

output "ec2_iam_role_arn" {
  description = "ARN of EC2 IAM role"
  value       = aws_iam_role.ec2_role.arn
}

output "ec2_iam_role_name" {
  description = "Name of EC2 IAM role"
  value       = aws_iam_role.ec2_role.name
}

output "ec2_instance_profile_name" {
  description = "Name of EC2 instance profile"
  value       = aws_iam_instance_profile.ec2_profile.name
}

output "ec2_instance_profile_arn" {
  description = "ARN of EC2 instance profile"
  value       = aws_iam_instance_profile.ec2_profile.arn
}

output "key_pair_name" {
  description = "Name of SSH key pair"
  value       = data.aws_key_pair.existing.key_name
}

output "key_pair_id" {
  description = "ID of SSH key pair"
  value       = data.aws_key_pair.existing.id
}

output "lambda_security_group_id" {
  description = "ID of Lambda security group"
  value       = aws_security_group.lambda.id
}