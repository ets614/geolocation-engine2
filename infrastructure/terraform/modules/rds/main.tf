# RDS PostgreSQL Module for Detection API
# Provides HA PostgreSQL with automated backups, WAL archiving, and read replicas

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# --------------------------------------------------------------------------
# KMS Key for RDS Encryption
# --------------------------------------------------------------------------

resource "aws_kms_key" "rds" {
  description             = "KMS key for RDS encryption"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  tags = merge(var.tags, {
    Name = "${var.project_name}-${var.environment}-rds-kms"
  })
}

# --------------------------------------------------------------------------
# Security Group for RDS
# --------------------------------------------------------------------------

resource "aws_security_group" "rds" {
  name_prefix = "${var.project_name}-${var.environment}-rds-"
  description = "Security group for RDS PostgreSQL"
  vpc_id      = var.vpc_id

  ingress {
    description     = "PostgreSQL from EKS nodes"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = var.allowed_security_group_ids
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name = "${var.project_name}-${var.environment}-rds-sg"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# --------------------------------------------------------------------------
# RDS Parameter Group
# --------------------------------------------------------------------------

resource "aws_db_parameter_group" "main" {
  name_prefix = "${var.project_name}-${var.environment}-"
  family      = "postgres${var.engine_major_version}"
  description = "Custom parameter group for detection API PostgreSQL"

  # Performance tuning
  parameter {
    name  = "shared_buffers"
    value = "{DBInstanceClassMemory/4}"
  }

  parameter {
    name  = "effective_cache_size"
    value = "{DBInstanceClassMemory*3/4}"
  }

  parameter {
    name  = "work_mem"
    value = "65536"  # 64MB
  }

  parameter {
    name  = "maintenance_work_mem"
    value = "524288"  # 512MB
  }

  # WAL configuration for archiving
  parameter {
    name  = "wal_buffers"
    value = "16384"  # 16MB
  }

  parameter {
    name  = "checkpoint_completion_target"
    value = "0.9"
  }

  parameter {
    name  = "max_wal_size"
    value = "2048"  # 2GB
  }

  # Logging
  parameter {
    name  = "log_min_duration_statement"
    value = "1000"  # Log queries > 1s
  }

  parameter {
    name  = "log_connections"
    value = "1"
  }

  parameter {
    name  = "log_disconnections"
    value = "1"
  }

  parameter {
    name  = "log_statement"
    value = "ddl"
  }

  # Connection settings
  parameter {
    name  = "max_connections"
    value = var.max_connections
  }

  # SSL
  parameter {
    name  = "rds.force_ssl"
    value = "1"
  }

  tags = var.tags

  lifecycle {
    create_before_destroy = true
  }
}

# --------------------------------------------------------------------------
# RDS Primary Instance (Multi-AZ)
# --------------------------------------------------------------------------

resource "aws_db_instance" "primary" {
  identifier = "${var.project_name}-${var.environment}-primary"

  engine               = "postgres"
  engine_version       = var.engine_version
  instance_class       = var.instance_class
  allocated_storage    = var.allocated_storage
  max_allocated_storage = var.max_allocated_storage
  storage_type         = "gp3"
  storage_encrypted    = true
  kms_key_id           = aws_kms_key.rds.arn

  db_name  = var.database_name
  username = var.master_username
  password = var.master_password
  port     = 5432

  multi_az               = var.multi_az
  db_subnet_group_name   = var.db_subnet_group_name
  vpc_security_group_ids = [aws_security_group.rds.id]
  parameter_group_name   = aws_db_parameter_group.main.name

  # Backup configuration
  backup_retention_period   = var.backup_retention_period
  backup_window             = "02:00-03:00"
  maintenance_window        = "sun:04:00-sun:05:00"
  copy_tags_to_snapshot     = true
  delete_automated_backups  = false
  final_snapshot_identifier = "${var.project_name}-${var.environment}-final-${formatdate("YYYY-MM-DD", timestamp())}"
  skip_final_snapshot       = false

  # Monitoring
  monitoring_interval          = 60
  monitoring_role_arn          = var.monitoring_role_arn
  performance_insights_enabled = true
  performance_insights_retention_period = var.performance_insights_retention

  # Security
  publicly_accessible    = false
  deletion_protection    = var.deletion_protection
  auto_minor_version_upgrade = true
  ca_cert_identifier     = "rds-ca-rsa2048-g1"

  # IAM authentication
  iam_database_authentication_enabled = true

  enabled_cloudwatch_logs_exports = [
    "postgresql",
    "upgrade"
  ]

  tags = merge(var.tags, {
    Name = "${var.project_name}-${var.environment}-primary"
  })

  lifecycle {
    ignore_changes = [
      final_snapshot_identifier,
      password
    ]
  }
}

# --------------------------------------------------------------------------
# Read Replica
# --------------------------------------------------------------------------

resource "aws_db_instance" "replica" {
  count = var.create_read_replica ? 1 : 0

  identifier          = "${var.project_name}-${var.environment}-replica"
  replicate_source_db = aws_db_instance.primary.identifier

  instance_class    = var.replica_instance_class
  storage_encrypted = true
  kms_key_id        = aws_kms_key.rds.arn

  multi_az               = false
  vpc_security_group_ids = [aws_security_group.rds.id]
  parameter_group_name   = aws_db_parameter_group.main.name

  monitoring_interval          = 60
  monitoring_role_arn          = var.monitoring_role_arn
  performance_insights_enabled = true

  publicly_accessible    = false
  auto_minor_version_upgrade = true
  skip_final_snapshot    = true

  tags = merge(var.tags, {
    Name = "${var.project_name}-${var.environment}-replica"
  })
}

# --------------------------------------------------------------------------
# CloudWatch Alarms for RDS
# --------------------------------------------------------------------------

resource "aws_cloudwatch_metric_alarm" "cpu_high" {
  alarm_name          = "${var.project_name}-${var.environment}-rds-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "RDS CPU utilization is above 80% for 15 minutes"
  alarm_actions       = var.alarm_sns_topic_arns

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.primary.identifier
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "free_storage" {
  alarm_name          = "${var.project_name}-${var.environment}-rds-free-storage-low"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 1
  metric_name         = "FreeStorageSpace"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = var.allocated_storage * 1073741824 * 0.2  # 20% of allocated
  alarm_description   = "RDS free storage is below 20%"
  alarm_actions       = var.alarm_sns_topic_arns

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.primary.identifier
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "replica_lag" {
  count               = var.create_read_replica ? 1 : 0
  alarm_name          = "${var.project_name}-${var.environment}-rds-replica-lag"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "ReplicaLag"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 30  # seconds
  alarm_description   = "RDS replica lag exceeds 30 seconds"
  alarm_actions       = var.alarm_sns_topic_arns

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.replica[0].identifier
  }

  tags = var.tags
}
