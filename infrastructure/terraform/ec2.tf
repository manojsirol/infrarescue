# Pin the AMI used by the existing InfraRescue EC2 instance.
# This prevents a newer Amazon Linux AMI from unexpectedly
# forcing replacement of the existing server.

locals {
  amazon_linux_ami = "ami-07f35208dba26f009"
}

resource "aws_key_pair" "infrarescue" {
  key_name   = "${var.project_name}-key"
  public_key = file(var.ssh_public_key_path)

  tags = {
    Name    = "${var.project_name}-key"
    Project = var.project_name
  }
}

resource "aws_instance" "infrarescue" {
  ami = local.amazon_linux_ami
  instance_type          = var.instance_type
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.infrarescue.id]
  key_name               = aws_key_pair.infrarescue.key_name
  iam_instance_profile   = aws_iam_instance_profile.infrarescue.name

  root_block_device {
    volume_type = "gp3"
    volume_size = 8
    encrypted   = true
  }

  tags = {
    Name    = "${var.project_name}-server"
    Project = var.project_name
  }
}
