# Development Environment Configuration
environment                = "dev"
aws_region                 = "us-east-1"
vpc_cidr                   = "10.0.0.0/16"
kubernetes_version         = "1.28"
eks_node_count_min         = 2
eks_node_count_max         = 5
eks_node_instance_types    = ["t3.medium"]
enable_spot_instances      = true
rds_instance_class         = "db.t4g.small"
rds_allocated_storage      = 50
rds_backup_retention_days  = 7
rds_enable_multi_az        = false
redis_node_type            = "cache.t4g.micro"
redis_num_cache_nodes      = 1
redis_automatic_failover_enabled = false
redis_encryption_enabled   = false
alb_enable_https           = false
enable_cloudwatch_detailed_monitoring = false
log_retention_days         = 7
enable_nat_gateway         = true

tags = {
  Environment = "dev"
  CostCenter  = "engineering"
}
