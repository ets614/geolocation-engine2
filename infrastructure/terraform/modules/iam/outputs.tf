output "eks_cluster_role_arn" {
  description = "ARN of the EKS cluster IAM role"
  value       = aws_iam_role.eks_cluster.arn
}

output "eks_node_role_arn" {
  description = "ARN of the EKS node IAM role"
  value       = aws_iam_role.eks_node.arn
}

output "ebs_csi_role_arn" {
  description = "ARN of the EBS CSI driver IAM role"
  value       = aws_iam_role.ebs_csi.arn
}

output "detection_api_role_arn" {
  description = "ARN of the detection API service account IAM role"
  value       = aws_iam_role.detection_api.arn
}

output "rds_monitoring_role_arn" {
  description = "ARN of the RDS enhanced monitoring IAM role"
  value       = aws_iam_role.rds_monitoring.arn
}

output "cluster_autoscaler_role_arn" {
  description = "ARN of the cluster autoscaler IAM role"
  value       = aws_iam_role.cluster_autoscaler.arn
}
