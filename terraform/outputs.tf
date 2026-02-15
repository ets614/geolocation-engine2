# Output Values - Phase 05

output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "vpc_cidr" {
  description = "VPC CIDR block"
  value       = aws_vpc.main.cidr_block
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = aws_subnet.private[*].id
}

output "nat_gateway_ips" {
  description = "NAT Gateway public IPs"
  value       = aws_eip.nat[*].public_ip
}

output "alb_security_group_id" {
  description = "ALB security group ID"
  value       = aws_security_group.alb.id
}

output "eks_node_security_group_id" {
  description = "EKS node security group ID"
  value       = aws_security_group.eks_node.id
}

output "rds_security_group_id" {
  description = "RDS security group ID"
  value       = aws_security_group.rds.id
}

output "redis_security_group_id" {
  description = "Redis security group ID"
  value       = aws_security_group.redis.id
}

# Summary output for deployment
output "infrastructure_summary" {
  description = "Summary of deployed infrastructure"
  value = {
    environment    = var.environment
    region         = var.aws_region
    vpc            = aws_vpc.main.id
    eks_cluster    = aws_eks_cluster.main.name
    eks_endpoint   = aws_eks_cluster.main.endpoint
    rds_endpoint   = aws_db_instance.main.endpoint
    redis_endpoint = "${aws_elasticache_cluster.main.cache_nodes[0].address}:${aws_elasticache_cluster.main.port}"
    alb_dns        = aws_lb.main.dns_name
    k8s_version    = aws_eks_cluster.main.version
  }
}
