variable "aws_region" {
  description = "AWS region for InfraRescue infrastructure"
  type        = string
  default     = "ap-south-1"
}

variable "project_name" {
  description = "Project name used for resource naming and tagging"
  type        = string
  default     = "infrarescue"
}
