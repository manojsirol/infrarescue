# ---------------------------------------------------------
# SNS Topic
# Used by InfraRescue to escalate incidents that cannot
# be safely remediated automatically.
# ---------------------------------------------------------

resource "aws_sns_topic" "infrarescue_alerts" {
  name = "${var.project_name}-alerts"

  tags = {
    Name    = "${var.project_name}-alerts"
    Project = var.project_name
  }
}


# ---------------------------------------------------------
# IAM Role
# Allows the EC2 instance to obtain temporary AWS
# credentials without storing access keys in the project.
# ---------------------------------------------------------

resource "aws_iam_role" "infrarescue_ec2_role" {
  name = "${var.project_name}-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"

    Statement = [
      {
        Effect = "Allow"

        Principal = {
          Service = "ec2.amazonaws.com"
        }

        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Project = var.project_name
  }
}


# ---------------------------------------------------------
# Least-privilege SNS policy
# The InfraRescue EC2 instance can publish only to the
# InfraRescue SNS topic.
# ---------------------------------------------------------

resource "aws_iam_role_policy" "infrarescue_sns_publish" {
  name = "${var.project_name}-sns-publish"
  role = aws_iam_role.infrarescue_ec2_role.id

  policy = jsonencode({
    Version = "2012-10-17"

    Statement = [
      {
        Effect = "Allow"

        Action = [
          "sns:Publish"
        ]

        Resource = aws_sns_topic.infrarescue_alerts.arn
      }
    ]
  })
}


# ---------------------------------------------------------
# Instance Profile
# Connects the IAM role to EC2.
# ---------------------------------------------------------

resource "aws_iam_instance_profile" "infrarescue" {
  name = "${var.project_name}-instance-profile"
  role = aws_iam_role.infrarescue_ec2_role.name
}
