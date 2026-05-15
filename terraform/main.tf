# RDS MySQL Database Instance
resource "aws_db_instance" "mysql" {
  identifier            = var.db_instance_identifier
  engine                = "mysql"
  engine_version        = var.db_engine_version
  instance_class        = var.db_instance_class
  allocated_storage     = var.db_allocated_storage
  storage_type          = var.db_storage_type
  storage_encrypted     = true

  # Database configuration
  db_name  = var.db_name
  username = var.master_username
  password = var.master_password

  # Network configuration
  publicly_accessible    = var.publicly_accessible
  skip_final_snapshot    = var.skip_final_snapshot
  final_snapshot_identifier = var.skip_final_snapshot ? null : "${var.db_instance_identifier}-final-snapshot-${formatdate("YYYY-MM-DD-hhmm", timestamp())}"

  # Security
  vpc_security_group_ids = var.create_security_group ? [aws_security_group.rds_sg[0].id] : [var.existing_security_group_id]

  # Backup configuration
  backup_retention_period = var.enable_backup ? var.backup_retention_period : 0
  backup_window           = "03:00-04:00"
  maintenance_window      = "mon:04:00-mon:05:00"

  # Performance
  performance_insights_enabled = false
  enabled_cloudwatch_logs_exports = [
    "error",
    "general",
    "slowquery"
  ]

  # Deletion protection
  deletion_protection = false

  tags = merge(
    var.tags,
    {
      Name = var.db_instance_identifier
    }
  )

  depends_on = [
    aws_security_group.rds_sg
  ]
}

# DB Subnet Group (optional, uses default VPC)
# If you want to use a specific VPC, uncomment and configure:
# resource "aws_db_subnet_group" "mysql" {
#   name       = "${var.db_instance_identifier}-subnet-group"
#   subnet_ids = var.db_subnet_ids
#
#   tags = merge(
#     var.tags,
#     {
#       Name = "${var.db_instance_identifier}-subnet-group"
#     }
#   )
# }
