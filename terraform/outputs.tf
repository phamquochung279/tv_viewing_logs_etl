# Output the RDS endpoint (hostname)
output "db_endpoint" {
  description = "The connection endpoint for the RDS instance (use as MYSQL_HOST in credentials.env)"
  value       = aws_db_instance.mysql.endpoint
}

# Output just the hostname (without port)
output "db_host" {
  description = "The hostname of the RDS instance"
  value       = aws_db_instance.mysql.address
}

# Output the port
output "db_port" {
  description = "The port of the RDS instance (default: 3306)"
  value       = aws_db_instance.mysql.port
}

# Output the database name
output "db_name" {
  description = "The name of the database"
  value       = aws_db_instance.mysql.db_name
}

# Output the master username
output "db_username" {
  description = "The master username for the database"
  value       = aws_db_instance.mysql.username
}

# Output the resource ARN
output "db_instance_arn" {
  description = "The ARN of the RDS instance"
  value       = aws_db_instance.mysql.arn
}

# Output the security group ID
output "db_security_group_id" {
  description = "The security group ID for the RDS instance"
  value       = var.create_security_group ? aws_security_group.rds_sg[0].id : var.existing_security_group_id
}

# Output a connection string template for convenience
output "mysql_connection_info" {
  description = "Connection information for MySQL"
  value = {
    host     = aws_db_instance.mysql.address
    port     = aws_db_instance.mysql.port
    username = aws_db_instance.mysql.username
    database = aws_db_instance.mysql.db_name
    endpoint = aws_db_instance.mysql.endpoint
  }
}

# Output a formatted string for credentials.env
output "credentials_env_template" {
  description = "Template for credentials.env file"
  value = <<-EOT
# Add these to your credentials.env file:
MYSQL_HOST=${aws_db_instance.mysql.address}
MYSQL_PORT=${aws_db_instance.mysql.port}
MYSQL_USER=${aws_db_instance.mysql.username}
MYSQL_PASSWORD=<your_password>
MYSQL_DB=${aws_db_instance.mysql.db_name}
MYSQL_CONNECTION_STRING=mysql+pymysql://${aws_db_instance.mysql.username}:password@${aws_db_instance.mysql.address}:${aws_db_instance.mysql.port}/${aws_db_instance.mysql.db_name}
EOT
}
