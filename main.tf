terraform {
  backend "s3" {
    bucket         = "sheri-aws-cost-tf-state-20251027"
    key            = "terraform.tfstate"
    region         = "us-east-2"
    encrypt        = true
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-2"
}

# Zip up the lambda code from local folder
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "lambda_src"
  output_path = "handler.zip"
}

# IAM role that Lambda assumes
resource "aws_iam_role" "lambda_role" {
  name = "cost_optimizer_lambda_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Effect = "Allow",
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# Attach basic logging policy
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Custom inline policy for EC2 + CloudWatch + Cost Explorer
resource "aws_iam_role_policy" "lambda_ec2_ce" {
  name = "lambda_ec2_ce_policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "ec2:DescribeInstances",
          "ec2:StopInstances"
        ],
        Resource = "*"
      },
      {
        Effect = "Allow",
        Action = [
          "cloudwatch:GetMetricStatistics"
        ],
        Resource = "*"
      },
      {
        Effect = "Allow",
        Action = [
          "ce:GetCostAndUsage"
        ],
        Resource = "*"
      }
    ]
  })
}

# Deploy Lambda function
resource "aws_lambda_function" "optimizer" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = "aws-cost-optimizer"
  role             = aws_iam_role.lambda_role.arn
  handler          = "lambda_handler.main"
  runtime          = "python3.10"
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  environment {
    variables = {
      DRY_RUN = "true"
    }
  }

  tags = {
    Name        = "CostOptimizer"
    Environment = "production"
    Owner       = "Amara"
  }
}

# Schedule the Lambda daily via CloudWatch Events
resource "aws_cloudwatch_event_rule" "daily_trigger" {
  name                = "daily-cost-scan"
  schedule_expression = "cron(0 2 * * ? *)" # 2:00 AM UTC daily
}

# Target the Lambda from the rule
resource "aws_cloudwatch_event_target" "lambda_target" {
  rule      = aws_cloudwatch_event_rule.daily_trigger.name
  target_id = "optimizer-target"
  arn       = aws_lambda_function.optimizer.arn
}

# Allow EventBridge to invoke the Lambda
resource "aws_lambda_permission" "allow_cloudwatch" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.optimizer.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily_trigger.arn
}

# Output the Lambda ARN
output "lambda_arn" {
  value = aws_lambda_function.optimizer.arn
}

