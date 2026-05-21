terraform {
  backend "s3" {
    bucket         = "sheri-cost-tf-state-419445613749"
    key            = "terraform.tfstate"
    region         = "us-east-2"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

data "aws_caller_identity" "current" {}

# ─── Lambda source zip ────────────────────────────────────────────────────────

data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "lambda_src"
  output_path = "handler.zip"
}

# ─── SNS topic + email subscription ──────────────────────────────────────────

resource "aws_sns_topic" "cost_alerts" {
  name = "cost-alerts"

  tags = {
    Name        = "CostAlerts"
    Environment = "production"
    Owner       = "Amara"
  }
}

resource "aws_sns_topic_subscription" "email_alert" {
  topic_arn = aws_sns_topic.cost_alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# ─── Dead-letter queue for Lambda failures ────────────────────────────────────

resource "aws_sqs_queue" "lambda_dlq" {
  name                      = "cost-optimizer-dlq"
  message_retention_seconds = 1209600 # 14 days

  tags = {
    Name        = "CostOptimizerDLQ"
    Environment = "production"
    Owner       = "Amara"
  }
}

# ─── CloudWatch log group with retention ─────────────────────────────────────

resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/aws-cost-optimizer"
  retention_in_days = var.log_retention_days

  tags = {
    Name        = "CostOptimizerLogs"
    Environment = "production"
    Owner       = "Amara"
  }
}

# ─── IAM role ─────────────────────────────────────────────────────────────────

resource "aws_iam_role" "lambda_role" {
  name = "cost_optimizer_lambda_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })

  tags = {
    Name        = "CostOptimizerRole"
    Environment = "production"
    Owner       = "Amara"
  }
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
        Effect   = "Allow"
        Action   = ["ec2:DescribeInstances", "ec2:StopInstances"]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["cloudwatch:GetMetricStatistics"]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["ce:GetCostAndUsage"]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["sns:Publish"]
        Resource = aws_sns_topic.cost_alerts.arn
      },
      {
        Effect   = "Allow"
        Action   = ["sqs:SendMessage"]
        Resource = aws_sqs_queue.lambda_dlq.arn
      }
    ]
  })
}

# ─── Lambda function ──────────────────────────────────────────────────────────

resource "aws_lambda_function" "optimizer" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = "aws-cost-optimizer"
  role             = aws_iam_role.lambda_role.arn
  handler          = "lambda_handler.main"
  runtime          = "python3.12"
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory

  dead_letter_config {
    target_arn = aws_sqs_queue.lambda_dlq.arn
  }

  environment {
    variables = {
      DRY_RUN               = tostring(var.dry_run)
      SNS_TOPIC_ARN         = aws_sns_topic.cost_alerts.arn
      IDLE_CPU_DAYS         = tostring(var.idle_cpu_threshold_days)
    }
  }

  depends_on = [aws_cloudwatch_log_group.lambda_logs]

  tags = {
    Name        = "CostOptimizer"
    Environment = "production"
    Owner       = "Amara"
  }
}

# ─── EventBridge daily trigger ────────────────────────────────────────────────

resource "aws_cloudwatch_event_rule" "daily_trigger" {
  name                = "daily-cost-scan"
  description         = "Triggers the cost optimizer Lambda daily at 2 AM UTC"
  schedule_expression = "cron(0 2 * * ? *)"

  tags = {
    Name        = "CostOptimizerSchedule"
    Environment = "production"
    Owner       = "Amara"
  }
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

# ─── CloudWatch alarm: Lambda errors ─────────────────────────────────────────

resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "cost-optimizer-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 86400
  statistic           = "Sum"
  threshold           = 0
  alarm_description   = "Cost optimizer Lambda failed during execution"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.optimizer.function_name
  }

  alarm_actions = [aws_sns_topic.cost_alerts.arn]
}

# ─── Outputs ──────────────────────────────────────────────────────────────────

output "lambda_arn" {
  description = "ARN of the cost optimizer Lambda function"
  value       = aws_lambda_function.optimizer.arn
}

output "sns_topic_arn" {
  description = "ARN of the SNS cost-alerts topic"
  value       = aws_sns_topic.cost_alerts.arn
}

output "dlq_url" {
  description = "URL of the Lambda dead-letter queue"
  value       = aws_sqs_queue.lambda_dlq.id
}

output "log_group" {
  description = "CloudWatch log group for Lambda execution logs"
  value       = aws_cloudwatch_log_group.lambda_logs.name
}
