variable "aws_region" {
  description = "AWS region where the resources will be created"
  type        = string
  default     = "us-east-1"
}

# Cần config biến dưới đây trong terraform.tfvars:
variable "db_instance_identifier" {
  description = "The identifier for the DB instance - unique name for your RDS instance"
  type        = string
  validation {
    condition     = can(regex("^[a-z0-9-]{1,63}$", var.db_instance_identifier))
    error_message = "DB instance identifier must be lowercase alphanumeric with hyphens only, max 63 characters."
  }
}

variable "db_engine_version" {
  description = "MySQL engine version"
  type        = string
  default     = "8.0.42"
}

variable "db_instance_class" {
  description = "The instance class for the DB instance (e.g., db.t3.micro for free tier)"
  type        = string
  default     = "db.t3.micro"
}

variable "db_allocated_storage" {
  description = "Allocated storage in GB"
  type        = number
  default     = 20
  validation {
    condition     = var.db_allocated_storage >= 20
    error_message = "Allocated storage must be at least 20 GB."
  }
}

variable "db_storage_type" {
  description = "Storage type (gp2, gp3, io1, etc.)"
  type        = string
  default     = "gp2"
}

# Cần config biến dưới đây trong terraform.tfvars:
variable "master_username" {
  description = "Master username for the database"
  type        = string
  validation {
    condition     = can(regex("^[a-z][a-z0-9_]*$", var.master_username))
    error_message = "Master username must start with a letter and contain only lowercase letters, numbers, and underscores."
  }
}

# Cần config biến dưới đây trong terraform.tfvars:
variable "master_password" {
  description = "Master password for the database"
  type        = string
  sensitive   = true
  validation {
    condition     = length(var.master_password) >= 8
    error_message = "Master password must be at least 8 characters long."
  }
}

# Cần config biến dưới đây trong terraform.tfvars:
variable "db_name" {
  description = "Name of the initial database to create"
  type        = string
  validation {
    condition     = can(regex("^[a-z][a-z0-9_]*$", var.db_name))
    error_message = "Database name must start with a letter and contain only lowercase letters, numbers, and underscores."
  }
}

variable "publicly_accessible" {
  description = "Whether the DB instance should be publicly accessible"
  type        = bool
  default     = true
}

variable "skip_final_snapshot" {
  description = "Skip creating a final snapshot when destroying the DB instance"
  type        = bool
  default     = false
}

variable "allowed_cidr_blocks" {
  description = "List of CIDR blocks allowed to access the database"
  type        = list(string)
  default     = ["0.0.0.0/0"] # WARNING: This is open to the world. Restrict this in production!
}

variable "create_security_group" {
  description = "Whether to create a new security group or use an existing one"
  type        = bool
  default     = true
}

variable "existing_security_group_id" {
  description = "Existing security group ID (if create_security_group is false)"
  type        = string
  default     = ""
}

variable "enable_backup" {
  description = "Enable automated backups"
  type        = bool
  default     = true
}

variable "backup_retention_period" {
  description = "Number of days to retain backups"
  type        = number
  default     = 7
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default = {
    Project     = "ETL-Project"
    Environment = "Development"
    ManagedBy   = "Terraform"
  }
}
