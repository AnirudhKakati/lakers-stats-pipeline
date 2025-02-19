terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.0"
    }
  }
}

provider "aws" {
  region  = "us-east-2"
  profile = "lakers-stats-pipeline"
}

resource "aws_s3_bucket" "lakers_stats_pipeline" {

  bucket = "lakers-stats-pipeline-bucket"

  tags = {
    Name        = "LakersStatsBucket"
    Environment = "Dev"
  }

}

resource "aws_iam_role" "lambda_role" {
  name               = "lambda_execution_role"
  assume_role_policy = <<EOF
  {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Action": "sts:AssumeRole",
        "Principal": {
          "Service": "lambda.amazonaws.com"
        },
        "Effect": "Allow",
        "Sid": ""
      }
    ] 
  }
  EOF
}

resource "aws_iam_policy" "lambda_policy" {
  name        = "lambda_s3_policy"
  description = "Allow Lambda to read from and write to S3 and create logs"

  policy = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "s3:GetObject",
          "s3:PutObject"
        ],
        "Resource": "arn:aws:s3:::lakers-stats-pipeline-bucket/*"
      },
      {
        "Effect": "Allow",
        "Action": [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        "Resource": "*"
      }
    ]
  }
  EOF
}

resource "aws_iam_role_policy_attachment" "lambda_attach" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.lambda_policy.arn
}

resource "aws_lambda_function" "fetch_schedule_lambda" {
  function_name = "fetch_lakers_schedule"
  role = aws_iam_role.lambda_role.arn
  handler = "fetch_schedule.lambda_handler" # Matches function name inside script
  runtime = "python3.9"
  timeout = 10

  s3_bucket = "lakers-stats-pipeline-bucket"
  s3_key = "lambdas/fetch_schedule_lambda.zip"

  environment {
    variables = {
      BUCKET_NAME = "lakers-stats-pipeline-bucket"
      S3_KEY = "schedule/lakers_schedule.json"
    }
  }  
}

resource "aws_cloudwatch_event_rule" "lakers_schedule_trigger" {
  name = "lakers-schedule-trigger"
  description = "Triggers the Lambda function for fetching schedule every October 1st"
  schedule_expression = "cron(0 0 1 10 ? *)"
}

resource "aws_cloudwatch_event_target" "lakers_schedule_lambda_target" {
  rule = aws_cloudwatch_event_rule.lakers_schedule_trigger.name
  target_id = "fetch_schedule_lambda"
  arn = aws_lambda_function.fetch_schedule_lambda.arn
  
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id = "AllowExecutionFromEventBridge"
  action = "lambda:InvokeFunction"
  function_name = aws_lambda_function.fetch_schedule_lambda.function_name
  principal = "events.amazonaws.com"
  source_arn = aws_cloudwatch_event_rule.lakers_schedule_trigger.arn 
}
