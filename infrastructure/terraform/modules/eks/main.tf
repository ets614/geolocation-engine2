# EKS Cluster Module for Detection API
# Provides managed Kubernetes with auto-scaling node groups

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }
}

# --------------------------------------------------------------------------
# KMS Key for EKS Secrets Encryption
# --------------------------------------------------------------------------

resource "aws_kms_key" "eks" {
  description             = "KMS key for EKS secrets encryption"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  tags = merge(var.tags, {
    Name = "${var.cluster_name}-eks-kms"
  })
}

resource "aws_kms_alias" "eks" {
  name          = "alias/${var.cluster_name}-eks"
  target_key_id = aws_kms_key.eks.key_id
}

# --------------------------------------------------------------------------
# EKS Cluster
# --------------------------------------------------------------------------

resource "aws_eks_cluster" "main" {
  name     = var.cluster_name
  version  = var.cluster_version
  role_arn = var.cluster_role_arn

  vpc_config {
    subnet_ids              = concat(var.private_subnet_ids, var.public_subnet_ids)
    endpoint_private_access = true
    endpoint_public_access  = var.endpoint_public_access
    public_access_cidrs     = var.public_access_cidrs
    security_group_ids      = [aws_security_group.cluster.id]
  }

  encryption_config {
    provider {
      key_arn = aws_kms_key.eks.arn
    }
    resources = ["secrets"]
  }

  enabled_cluster_log_types = [
    "api",
    "audit",
    "authenticator",
    "controllerManager",
    "scheduler"
  ]

  tags = merge(var.tags, {
    Name = var.cluster_name
  })

  depends_on = [
    aws_cloudwatch_log_group.eks
  ]
}

# --------------------------------------------------------------------------
# CloudWatch Log Group for EKS Control Plane Logs
# --------------------------------------------------------------------------

resource "aws_cloudwatch_log_group" "eks" {
  name              = "/aws/eks/${var.cluster_name}/cluster"
  retention_in_days = var.log_retention_days

  tags = var.tags
}

# --------------------------------------------------------------------------
# EKS Node Groups
# --------------------------------------------------------------------------

# Application node group (detection-api workloads)
resource "aws_eks_node_group" "application" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "${var.cluster_name}-application"
  node_role_arn   = var.node_role_arn
  subnet_ids      = var.private_subnet_ids

  instance_types = var.application_instance_types
  capacity_type  = "ON_DEMAND"
  disk_size      = var.application_disk_size

  scaling_config {
    desired_size = var.application_desired_size
    min_size     = var.application_min_size
    max_size     = var.application_max_size
  }

  update_config {
    max_unavailable = 1
  }

  labels = {
    "node-type" = "worker"
    "workload"  = "detection-engine"
  }

  taint {
    key    = "workload"
    value  = "detection"
    effect = "NO_SCHEDULE"
  }

  tags = merge(var.tags, {
    Name                                       = "${var.cluster_name}-application"
    "k8s.io/cluster-autoscaler/${var.cluster_name}" = "owned"
    "k8s.io/cluster-autoscaler/enabled"        = "true"
  })

  lifecycle {
    ignore_changes = [scaling_config[0].desired_size]
  }
}

# Monitoring node group (Prometheus, Grafana, Loki)
resource "aws_eks_node_group" "monitoring" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "${var.cluster_name}-monitoring"
  node_role_arn   = var.node_role_arn
  subnet_ids      = var.private_subnet_ids

  instance_types = var.monitoring_instance_types
  capacity_type  = "ON_DEMAND"
  disk_size      = var.monitoring_disk_size

  scaling_config {
    desired_size = var.monitoring_desired_size
    min_size     = var.monitoring_min_size
    max_size     = var.monitoring_max_size
  }

  update_config {
    max_unavailable = 1
  }

  labels = {
    "node-type" = "monitoring"
    "workload"  = "observability"
  }

  tags = merge(var.tags, {
    Name = "${var.cluster_name}-monitoring"
  })

  lifecycle {
    ignore_changes = [scaling_config[0].desired_size]
  }
}

# --------------------------------------------------------------------------
# Cluster Security Group
# --------------------------------------------------------------------------

resource "aws_security_group" "cluster" {
  name_prefix = "${var.cluster_name}-cluster-"
  description = "Security group for EKS cluster control plane"
  vpc_id      = var.vpc_id

  ingress {
    description = "HTTPS from VPC"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name = "${var.cluster_name}-cluster-sg"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# --------------------------------------------------------------------------
# OIDC Provider for IAM Roles for Service Accounts (IRSA)
# --------------------------------------------------------------------------

data "tls_certificate" "eks" {
  url = aws_eks_cluster.main.identity[0].oidc[0].issuer
}

resource "aws_iam_openid_connect_provider" "eks" {
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.eks.certificates[0].sha1_fingerprint]
  url             = aws_eks_cluster.main.identity[0].oidc[0].issuer

  tags = var.tags
}

# --------------------------------------------------------------------------
# EKS Addons
# --------------------------------------------------------------------------

resource "aws_eks_addon" "vpc_cni" {
  cluster_name                = aws_eks_cluster.main.name
  addon_name                  = "vpc-cni"
  addon_version               = var.vpc_cni_version
  resolve_conflicts_on_update = "OVERWRITE"

  tags = var.tags
}

resource "aws_eks_addon" "coredns" {
  cluster_name                = aws_eks_cluster.main.name
  addon_name                  = "coredns"
  addon_version               = var.coredns_version
  resolve_conflicts_on_update = "OVERWRITE"

  depends_on = [aws_eks_node_group.application]

  tags = var.tags
}

resource "aws_eks_addon" "kube_proxy" {
  cluster_name                = aws_eks_cluster.main.name
  addon_name                  = "kube-proxy"
  addon_version               = var.kube_proxy_version
  resolve_conflicts_on_update = "OVERWRITE"

  tags = var.tags
}

resource "aws_eks_addon" "ebs_csi" {
  cluster_name                = aws_eks_cluster.main.name
  addon_name                  = "aws-ebs-csi-driver"
  addon_version               = var.ebs_csi_version
  service_account_role_arn    = var.ebs_csi_role_arn
  resolve_conflicts_on_update = "OVERWRITE"

  tags = var.tags
}
