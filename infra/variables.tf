variable "region" {
  description = "AWS region for every resource in this project"
  type        = string
  default     = "eu-central-1"
}

variable "suffix" {
  description = "Makes the bucket name globally unique, e.g. your name"
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9-]{3,30}$", var.suffix))
    error_message = "suffix must be 3-30 characters: lowercase letters, digits, hyphens."
  }
}
