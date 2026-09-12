output "ec2_instance_id" {
  description = "ID of the InfraRescue EC2 instance"
  value       = aws_instance.infrarescue.id
}

output "ec2_public_ip" {
  description = "Public IP address of the InfraRescue EC2 instance"
  value       = aws_instance.infrarescue.public_ip
}

output "ssh_command" {
  description = "SSH command for connecting to the InfraRescue server"
  value       = "ssh -i ~/.ssh/infrarescue_ed25519 ec2-user@${aws_instance.infrarescue.public_ip}"
}