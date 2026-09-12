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

variable "allowed_ssh_cidr" {
  description = "Trusted public IP allowed to SSH into the InfraRescue server"
  type        = string
}

variable "instance_type" {
  description = "EC2 instance type for InfraRescue"
  type        = string
  default     = "t3.micro"
}

variable "ssh_public_key_path" {
  description = "Local path to the SSH public key"
  type        = string
}
