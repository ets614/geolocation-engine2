# Staging Environment Configuration
environment                = "staging"
aws_region                 = "us-east-1"
vpc_cidr                   = "10.0.0.0/16"
kubernetes_version         = "1.28"
eks_node_count_min         = 2
eks_node_count_max         = 10
eks_node_instance_types    = ["t3.medium", "t3a.medium"]
enable_spot_instances      = true
rds_instance_class         = "db.t4g.medium"
rds_allocated_storage      = 100
rds_backup_retention_days  = 14
rds_enable_multi_az        = true
redis_node_type            = "cache.t4g.small"
redis_num_cache_nodes      = 2
redis_automatic_failover_enabled = true
redis_encryption_enabled   = true
alb_enable_https           = true
enable_cloudwatch_detailed_monitoring = true
log_retention_days         = 14
enable_nat_gateway         = true

tags = {
  Environment = "staging"
  CostCenter  = "operations"
}
