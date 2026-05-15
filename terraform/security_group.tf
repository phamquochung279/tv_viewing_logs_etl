# Create a security group for the RDS instance
resource "aws_security_group" "rds_sg" {
  count       = var.create_security_group ? 1 : 0
  name        = "${var.db_instance_identifier}-sg"
  description = "Security group for RDS MySQL instance - ${var.db_instance_identifier}"
  tags = merge(
    var.tags,
    {
      Name = "${var.db_instance_identifier}-sg"
    }
  )
}

# Ingress rule: Allow MySQL (port 3306) from specified CIDR blocks
resource "aws_security_group_rule" "rds_ingress" {
  count             = var.create_security_group ? 1 : 0
  type              = "ingress"
  from_port         = 3306
  to_port           = 3306
  protocol          = "tcp"
  cidr_blocks       = var.allowed_cidr_blocks
  security_group_id = aws_security_group.rds_sg[0].id
  description       = "Allow MySQL access from specified CIDR blocks"
}

# Egress rule: Allow all outbound traffic
resource "aws_security_group_rule" "rds_egress" {
  count             = var.create_security_group ? 1 : 0
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.rds_sg[0].id
  description       = "Allow all outbound traffic"
}
