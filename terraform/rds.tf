# RDS PostgreSQL Configuration - Phase 05
# Features: Multi-AZ, automated backups (30d), encryption, enhanced monitoring

# RDS Subnet Group
resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-db-subnet-group"
  subnet_ids = aws_subnet.private[*].id

  tags = {
    Name = "${var.project_name}-db-subnet-group"
  }
}

# RDS Parameter Group
resource "aws_db_parameter_group" "main" {
  family = "postgres15"
  name   = "${var.project_name}-db-params"

  parameter {
    name  = "log_statement"
    value = "all"
  }

  parameter {
    name  = "log_min_duration_statement"
    value = "1000"
  }

  parameter {
    name  = "max_connections"
    value = "200"
  }

  parameter {
    name  = "shared_preload_libraries"
    value = "pg_stat_statements"
  }

  tags = {
    Name = "${var.project_name}-db-params"
  }
}

# Enhanced Monitoring Role for RDS
resource "aws_iam_role" "rds_monitoring" {
  name = "${var.project_name}-rds-monitoring-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "monitoring.rds.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "rds_monitoring" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
  role       = aws_iam_role.rds_monitoring.name
}

# RDS Instance (Primary)
resource "aws_db_instance" "main" {
  identifier           = "${var.project_name}-db"
  engine               = "postgres"
  engine_version       = var.rds_engine_version
  instance_class       = var.rds_instance_class
  allocated_storage    = var.rds_allocated_storage
  storage_type         = "gp3"
  storage_encrypted    = true
  kms_key_id           = aws_kms_key.rds.arn

  db_name  = "detectionapi"
  username = "admin"
  password = random_password.rds_master.result

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  parameter_group_name   = aws_db_parameter_group.main.name

  multi_az               = var.rds_enable_multi_az
  publicly_accessible    = false
  skip_final_snapshot    = false
  final_snapshot_identifier = "${var.project_name}-db-final-snapshot-${formatdate("YYYY-MM-DD-hhmm", timestamp())}"
  backup_retention_period = var.rds_backup_retention_days
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"
  copy_tags_to_snapshot  = true

  enabled_cloudwatch_logs_exports = [
    "postgresql"
  ]

  enable_iam_database_authentication = true
  monitoring_interval               = var.enable_cloudwatch_detailed_monitoring ? 60 : 0
  monitoring_role_arn               = aws_iam_role.rds_monitoring.arn

  enable_http_endpoint = false

  deletion_protection = var.environment == "prod" ? true : false

  tags = {
    Name = "${var.project_name}-db"
  }

  depends_on = [aws_security_group.rds]
}

# RDS Master Password (generated and stored in Secrets Manager)
resource "random_password" "rds_master" {
  length  = 32
  special = true
}

resource "aws_secretsmanager_secret" "rds_password" {
  name                    = "${var.project_name}-rds-password"
  recovery_window_in_days = 7

  tags = {
    Name = "${var.project_name}-rds-password"
  }
}

resource "aws_secretsmanager_secret_version" "rds_password" {
  secret_id     = aws_secretsmanager_secret.rds_password.id
  secret_string = jsonencode({
    username = "admin"
    password = random_password.rds_master.result
    engine   = "postgres"
    host     = aws_db_instance.main.endpoint
    port     = 5432
    dbname   = "detectionapi"
  })
}

# KMS Key for RDS Encryption
resource "aws_kms_key" "rds" {
  description             = "KMS key for RDS encryption"
  deletion_window_in_days = 10
  enable_key_rotation     = true

  tags = {
    Name = "${var.project_name}-rds-key"
  }
}

resource "aws_kms_alias" "rds" {
  name          = "alias/${var.project_name}-rds"
  target_key_id = aws_kms_key.rds.key_id
}

# RDS Read Replica (optional, for read scaling)
resource "aws_db_instance" "read_replica" {
  count                    = var.environment == "prod" ? 1 : 0
  identifier               = "${var.project_name}-db-replica"
  replicate_source_db      = aws_db_instance.main.identifier
  instance_class           = var.rds_instance_class
  publicly_accessible      = false
  auto_minor_version_upgrade = true
  skip_final_snapshot      = false
  final_snapshot_identifier = "${var.project_name}-db-replica-final-snapshot-${formatdate("YYYY-MM-DD-hhmm", timestamp())}"

  tags = {
    Name = "${var.project_name}-db-replica"
  }

  depends_on = [aws_db_instance.main]
}

# RDS Backup
resource "aws_db_snapshot" "main" {
  db_instance_identifier = aws_db_instance.main.id
  db_snapshot_identifier = "${var.project_name}-db-snapshot-${formatdate("YYYY-MM-DD-hhmm", timestamp())}"
  tags = {
    Name = "${var.project_name}-db-snapshot"
  }
}

# Output RDS details
output "rds_endpoint" {
  description = "RDS instance endpoint"
  value       = aws_db_instance.main.endpoint
}

output "rds_address" {
  description = "RDS instance address (hostname only)"
  value       = aws_db_instance.main.address
}

output "rds_port" {
  description = "RDS instance port"
  value       = aws_db_instance.main.port
}

output "rds_database_name" {
  description = "RDS database name"
  value       = aws_db_instance.main.db_name
}

output "rds_master_username" {
  description = "RDS master username"
  value       = aws_db_instance.main.username
  sensitive   = true
}
