# S3 Module for Detection API Infrastructure
# Provides backup storage with versioning, encryption, lifecycle policies

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
# KMS Key for S3 Encryption
# --------------------------------------------------------------------------

resource "aws_kms_key" "s3" {
  description             = "KMS key for S3 bucket encryption"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  tags = merge(var.tags, {
    Name = "${var.project_name}-${var.environment}-s3-kms"
  })
}

# --------------------------------------------------------------------------
# Backup Bucket
# --------------------------------------------------------------------------

resource "aws_s3_bucket" "backup" {
  bucket = "${var.project_name}-${var.environment}-backups-${var.aws_account_id}"

  tags = merge(var.tags, {
    Name = "${var.project_name}-${var.environment}-backups"
  })
}

resource "aws_s3_bucket_versioning" "backup" {
  bucket = aws_s3_bucket.backup.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "backup" {
  bucket = aws_s3_bucket.backup.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.s3.arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "backup" {
  bucket = aws_s3_bucket.backup.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "backup" {
  bucket = aws_s3_bucket.backup.id

  rule {
    id     = "database-backups"
    status = "Enabled"

    filter {
      prefix = "database/"
    }

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    expiration {
      days = var.backup_retention_days
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }

  rule {
    id     = "audit-logs"
    status = "Enabled"

    filter {
      prefix = "audit/"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    expiration {
      days = var.audit_retention_days
    }
  }

  rule {
    id     = "queue-snapshots"
    status = "Enabled"

    filter {
      prefix = "queue/"
    }

    transition {
      days          = 7
      storage_class = "STANDARD_IA"
    }

    expiration {
      days = 30
    }
  }
}

# --------------------------------------------------------------------------
# Replication Bucket (for DR)
# --------------------------------------------------------------------------

resource "aws_s3_bucket" "backup_replica" {
  count    = var.enable_cross_region_replication ? 1 : 0
  provider = aws.replica
  bucket   = "${var.project_name}-${var.environment}-backups-replica-${var.aws_account_id}"

  tags = merge(var.tags, {
    Name = "${var.project_name}-${var.environment}-backups-replica"
  })
}

resource "aws_s3_bucket_versioning" "backup_replica" {
  count    = var.enable_cross_region_replication ? 1 : 0
  provider = aws.replica
  bucket   = aws_s3_bucket.backup_replica[0].id
  versioning_configuration {
    status = "Enabled"
  }
}

# --------------------------------------------------------------------------
# Terraform State Bucket
# --------------------------------------------------------------------------

resource "aws_s3_bucket" "terraform_state" {
  count  = var.create_state_bucket ? 1 : 0
  bucket = "${var.project_name}-terraform-state-${var.aws_account_id}"

  tags = merge(var.tags, {
    Name = "${var.project_name}-terraform-state"
  })
}

resource "aws_s3_bucket_versioning" "terraform_state" {
  count  = var.create_state_bucket ? 1 : 0
  bucket = aws_s3_bucket.terraform_state[0].id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "terraform_state" {
  count  = var.create_state_bucket ? 1 : 0
  bucket = aws_s3_bucket.terraform_state[0].id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "terraform_state" {
  count  = var.create_state_bucket ? 1 : 0
  bucket = aws_s3_bucket.terraform_state[0].id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# DynamoDB table for Terraform state locking
resource "aws_dynamodb_table" "terraform_lock" {
  count    = var.create_state_bucket ? 1 : 0
  name     = "${var.project_name}-terraform-lock"
  hash_key = "LockID"

  billing_mode = "PAY_PER_REQUEST"

  attribute {
    name = "LockID"
    type = "S"
  }

  tags = var.tags
}
