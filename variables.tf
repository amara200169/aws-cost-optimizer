variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-2"
}

variable "tf_state_bucket" {
  description = "S3 bucket name for Terraform remote state"
  type        = string
  default     = "sheri-aws-cost-tf-state-20251027"
}

variable "alert_email" {
  description = "Email address to receive SNS cost alert notifications"
  type        = string
}

variable "dry_run" {
  description = "When true, Lambda scans but does not stop instances"
  type        = bool
  default     = true
}

variable "idle_cpu_threshold_days" {
  description = "Number of days to evaluate CPU utilization for idle detection"
  type        = number
  default     = 3
}

variable "lambda_timeout" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 300
}

variable "lambda_memory" {
  description = "Lambda function memory in MB"
  type        = number
  default     = 256
}

variable "log_retention_days" {
  description = "CloudWatch log group retention in days"
  type        = number
  default     = 30
}
