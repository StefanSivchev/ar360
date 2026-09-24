output "bucket_name" {
  description = "Lake bucket name; S3_BUCKET in .env"
  value       = aws_s3_bucket.lake.bucket
}

output "bucket_arn" {
  description = "Lake bucket ARN; the Snowflake IAM role on Day 12 needs it"
  value       = aws_s3_bucket.lake.arn
}
