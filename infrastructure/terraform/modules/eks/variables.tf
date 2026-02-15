variable "cluster_name" {
  description = "Name of the EKS cluster"
  type        = string
}

variable "cluster_version" {
  description = "Kubernetes version for the EKS cluster"
  type        = string
  default     = "1.29"
}

variable "vpc_id" {
  description = "VPC ID where the cluster will be deployed"
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block of the VPC"
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for worker nodes"
  type        = list(string)
}

variable "public_subnet_ids" {
  description = "Public subnet IDs for load balancers"
  type        = list(string)
}

variable "cluster_role_arn" {
  description = "ARN of the IAM role for the EKS cluster"
  type        = string
}

variable "node_role_arn" {
  description = "ARN of the IAM role for EKS node groups"
  type        = string
}

variable "endpoint_public_access" {
  description = "Enable public access to the EKS API endpoint"
  type        = bool
  default     = false
}

variable "public_access_cidrs" {
  description = "CIDR blocks allowed to access the public API endpoint"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

# Application node group
variable "application_instance_types" {
  description = "Instance types for application node group"
  type        = list(string)
  default     = ["m6i.xlarge"]
}

variable "application_desired_size" {
  description = "Desired number of application nodes"
  type        = number
  default     = 3
}

variable "application_min_size" {
  description = "Minimum number of application nodes"
  type        = number
  default     = 2
}

variable "application_max_size" {
  description = "Maximum number of application nodes"
  type        = number
  default     = 10
}

variable "application_disk_size" {
  description = "Disk size in GB for application nodes"
  type        = number
  default     = 100
}

# Monitoring node group
variable "monitoring_instance_types" {
  description = "Instance types for monitoring node group"
  type        = list(string)
  default     = ["m6i.large"]
}

variable "monitoring_desired_size" {
  description = "Desired number of monitoring nodes"
  type        = number
  default     = 2
}

variable "monitoring_min_size" {
  description = "Minimum number of monitoring nodes"
  type        = number
  default     = 1
}

variable "monitoring_max_size" {
  description = "Maximum number of monitoring nodes"
  type        = number
  default     = 3
}

variable "monitoring_disk_size" {
  description = "Disk size in GB for monitoring nodes"
  type        = number
  default     = 200
}

# Addon versions
variable "vpc_cni_version" {
  description = "Version of the VPC CNI addon"
  type        = string
  default     = null
}

variable "coredns_version" {
  description = "Version of the CoreDNS addon"
  type        = string
  default     = null
}

variable "kube_proxy_version" {
  description = "Version of the kube-proxy addon"
  type        = string
  default     = null
}

variable "ebs_csi_version" {
  description = "Version of the EBS CSI driver addon"
  type        = string
  default     = null
}

variable "ebs_csi_role_arn" {
  description = "IAM role ARN for EBS CSI driver"
  type        = string
  default     = null
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 90
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}
