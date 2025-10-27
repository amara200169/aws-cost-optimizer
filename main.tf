terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-2"  # Your region
}

data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "lambda_src"  # We'll create this
  output_path = "handler.zip"
}

resource "aws_lambda_function" "optimizer" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = "aws-cost-optimizer"
  role             = aws_iam_role.lambda_role.arn
  handler          = "lambda_handler.lambda_handler"
  runtime          = "python3.10"
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  environment {
    variables = {
      DRY_RUN = "true"  # Toggle to "false" for real stops
    }
  }

  tags = {
    Name        = "CostOptimizer"
    Environment = "production"
    Owner       = "Amara"
  }
}

resource "aws_iam_role" "lambda_role" {
  name = "cost_optimizer_lambda_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "lambda_ec2_ce" {
  name = "lambda_ec2_ce_policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ec2:DescribeInstances",
          "ec2:StopInstances"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:GetMetricStatistics"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ce:GetCostAndUsage"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_cloudwatch_event_rule" "daily_trigger" {
  name                = "daily-cost-scan"
  schedule_expression = "cron(0 2 * * ? *)"  # Daily at 2AM UTC
}

resource "aws_cloudwatch_event_target" "lambda_target" {
  rule      = aws_cloudwatch_event_rule.daily_trigger.name
  target_id = "optimizer-target"
  arn       = aws_lambda_function.optimizer.arn
}

resource "aws_lambda_permission" "allow_cloudwatch" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.optimizer.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily_trigger.arn
}

output "lambda_arn" {
  value = aws_lambda_function.optimizer.arn
}