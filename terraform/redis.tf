# ElastiCache Redis Configuration - Phase 05
# Features: Multi-AZ, auto-failover, encryption, automatic backups

# Redis Subnet Group
resource "aws_elasticache_subnet_group" "main" {
  name       = "${var.project_name}-redis-subnet-group"
  subnet_ids = aws_subnet.private[*].id

  tags = {
    Name = "${var.project_name}-redis-subnet-group"
  }
}

# Redis Parameter Group
resource "aws_elasticache_parameter_group" "main" {
  name   = "${var.project_name}-redis-params"
  family = "redis7"

  parameter {
    name  = "maxmemory-policy"
    value = "allkeys-lru"  # LRU eviction policy
  }

  parameter {
    name  = "notify-keyspace-events"
    value = "Ex"  # Expire events
  }

  parameter {
    name  = "tcp-keepalive"
    value = "300"
  }

  tags = {
    Name = "${var.project_name}-redis-params"
  }
}

# KMS Key for Redis Encryption
resource "aws_kms_key" "redis" {
  description             = "KMS key for Redis encryption"
  deletion_window_in_days = 10
  enable_key_rotation     = true

  tags = {
    Name = "${var.project_name}-redis-key"
  }
}

resource "aws_kms_alias" "redis" {
  name          = "alias/${var.project_name}-redis"
  target_key_id = aws_kms_key.redis.key_id
}

# Redis Cluster (Multi-AZ with automatic failover)
resource "aws_elasticache_cluster" "main" {
  cluster_id           = "${var.project_name}-redis"
  engine               = "redis"
  engine_version       = var.redis_engine_version
  node_type            = var.redis_node_type
  num_cache_nodes      = var.redis_num_cache_nodes
  parameter_group_name = aws_elasticache_parameter_group.main.name
  port                 = 6379
  family               = "redis7"

  subnet_group_name          = aws_elasticache_subnet_group.main.name
  security_group_ids         = [aws_security_group.redis.id]
  automatic_failover_enabled = var.redis_automatic_failover_enabled

  # Encryption
  at_rest_encryption_enabled = var.redis_encryption_enabled
  kms_key_id                 = var.redis_encryption_enabled ? aws_kms_key.redis.arn : null
  transit_encryption_enabled = true

  # Backups and Maintenance
  snapshot_retention_limit = 30
  snapshot_window          = "03:00-05:00"
  maintenance_window       = "sun:05:00-sun:07:00"

  # Logs
  log_delivery_configuration {
    destination      = aws_cloudwatch_log_group.redis_slow_log.name
    destination_type = "cloudwatch-logs"
    log_format       = "json"
    log_type         = "slow-log"
    enabled          = true
  }

  log_delivery_configuration {
    destination      = aws_cloudwatch_log_group.redis_engine_log.name
    destination_type = "cloudwatch-logs"
    log_format       = "json"
    log_type         = "engine-log"
    enabled          = true
  }

  tags = {
    Name = "${var.project_name}-redis"
  }

  depends_on = [aws_security_group.redis]
}

# CloudWatch Log Groups for Redis
resource "aws_cloudwatch_log_group" "redis_slow_log" {
  name              = "/aws/elasticache/${var.project_name}/slow-log"
  retention_in_days = var.log_retention_days

  tags = {
    Name = "${var.project_name}-redis-slow-log"
  }
}

resource "aws_cloudwatch_log_group" "redis_engine_log" {
  name              = "/aws/elasticache/${var.project_name}/engine-log"
  retention_in_days = var.log_retention_days

  tags = {
    Name = "${var.project_name}-redis-engine-log"
  }
}

# IAM Role for Redis backup to S3
resource "aws_iam_role" "redis_backup" {
  name = "${var.project_name}-redis-backup-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "elasticache.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "redis_backup" {
  name = "${var.project_name}-redis-backup-policy"
  role = aws_iam_role.redis_backup.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:DeleteObject"
        ]
        Resource = "${aws_s3_bucket.redis_backups.arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = aws_s3_bucket.redis_backups.arn
      }
    ]
  })
}

# S3 bucket for Redis backups
resource "aws_s3_bucket" "redis_backups" {
  bucket = "${var.project_name}-redis-backups-${random_string.suffix.result}"

  tags = {
    Name = "${var.project_name}-redis-backups"
  }
}

resource "aws_s3_bucket_versioning" "redis_backups" {
  bucket = aws_s3_bucket.redis_backups.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "redis_backups" {
  bucket = aws_s3_bucket.redis_backups.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "redis_backups" {
  bucket                  = aws_s3_bucket.redis_backups.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "redis_backups" {
  bucket = aws_s3_bucket.redis_backups.id

  rule {
    id     = "archive-old-backups"
    status = "Enabled"

    transitions {
      days          = 30
      storage_class = "GLACIER"
    }

    expiration {
      days = 90
    }
  }
}

# Output Redis details
output "redis_endpoint" {
  description = "Redis cluster endpoint"
  value       = aws_elasticache_cluster.main.cache_nodes[0].address
}

output "redis_port" {
  description = "Redis port"
  value       = aws_elasticache_cluster.main.port
}

output "redis_cluster_id" {
  description = "Redis cluster ID"
  value       = aws_elasticache_cluster.main.cluster_id
}
