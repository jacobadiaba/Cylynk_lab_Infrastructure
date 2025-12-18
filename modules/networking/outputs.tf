# modules/networking/outputs.tf

output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "vpc_cidr" {
  description = "CIDR block of the VPC"
  value       = aws_vpc.main.cidr_block
}

output "internet_gateway_id" {
  description = "ID of the Internet Gateway"
  value       = aws_internet_gateway.main.id
}

output "nat_gateway_id" {
  description = "ID of the NAT Gateway"
  value       = var.enable_nat_gateway ? aws_nat_gateway.main[0].id : null
}

output "nat_gateway_ip" {
  description = "Public IP of the NAT Gateway"
  value       = var.enable_nat_gateway ? aws_eip.nat[0].public_ip : null
}

output "management_subnet_id" {
  description = "ID of the management subnet"
  value       = aws_subnet.management.id
}

output "management_subnet_cidr" {
  description = "CIDR block of the management subnet"
  value       = aws_subnet.management.cidr_block
}

output "attackbox_pool_subnet_id" {
  description = "ID of the AttackBox pool subnet"
  value       = aws_subnet.attackbox_pool.id
}

output "attackbox_pool_subnet_cidr" {
  description = "CIDR block of the AttackBox pool subnet"
  value       = aws_subnet.attackbox_pool.cidr_block
}

output "student_lab_subnet_ids" {
  description = "List of student lab subnet IDs"
  value       = aws_subnet.student_labs[*].id
}

output "student_lab_subnet_cidrs" {
  description = "List of student lab subnet CIDR blocks"
  value       = aws_subnet.student_labs[*].cidr_block
}

output "public_route_table_id" {
  description = "ID of the public route table"
  value       = aws_route_table.public.id
}

output "private_route_table_id" {
  description = "ID of the private route table"
  value       = aws_route_table.private.id
}

output "availability_zones" {
  description = "List of availability zones used"
  value       = distinct(aws_subnet.student_labs[*].availability_zone)
}

output "attackbox_subnet_is_public" {
  description = "Whether AttackBox subnet is configured as public (direct internet access)"
  value       = var.attackbox_public_subnet
}