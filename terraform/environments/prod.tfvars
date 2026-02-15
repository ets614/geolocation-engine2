# Production Environment Configuration
environment                = "prod"
aws_region                 = "us-east-1"
vpc_cidr                   = "10.0.0.0/16"
kubernetes_version         = "1.28"
eks_node_count_min         = 3
eks_node_count_max         = 20
eks_node_instance_types    = ["t3.large", "t3a.large"]
enable_spot_instances      = true
spot_max_price             = "0.05"
rds_instance_class         = "db.t4g.large"
rds_allocated_storage      = 500
rds_backup_retention_days  = 30
rds_enable_multi_az        = true
redis_node_type            = "cache.t4g.medium"
redis_num_cache_nodes      = 3
redis_automatic_failover_enabled = true
redis_encryption_enabled   = true
alb_enable_https           = true
enable_cloudwatch_detailed_monitoring = true
log_retention_days         = 30
enable_nat_gateway         = true

tags = {
  Environment = "prod"
  CostCenter  = "operations"
  Compliance  = "required"
}
