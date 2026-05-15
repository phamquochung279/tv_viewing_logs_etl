## Structure folder terraform

- `provider.tf`: config Terraform version & AWS provider.
- `variables.tf`: định nghĩa input variables (type, default, validation).
- `main.tf`: file chính để khai báo & trực tiếp tạo RDS MySQL instance.
- `security_group.tf`: tạo security group và inbound/outbound rules.
- `outputs.tf`: chứa các endpoint, port, username, template credentials--bạn có thể print ra để paste vào credentials.env.
- `terraform.tfvars.example`: template để tạo `terraform.tfvars`--nơi chứa các giá trị thực tế mà bạn muốn gán cho các biến trong `variables.tf`.
- `.gitignore`: chặn commit các file nhạy cảm như `terraform.tfvars` và `*.tfstate` (file này sẽ được tạo sau khi chạy `terraform apply`).

## Một vài command Terraform thường dùng

```bash
terraform init                                      # Khởi tạo folder Terraform và tải provider
terraform plan                                      # Preview các thay đổi sẽ được tạo/sửa/xóa
terraform apply                                     # Thực thi thay đổi để tạo/sửa resource thật trên AWS
terraform output                                    # Print toàn bộ output values đã khai báo trong outputs.tf
terraform validate                                  # Check cú pháp và logic cơ bản của file Terraform
terraform fmt -recursive                            # Tự động format toàn bộ file .tf trong thư mục (và cả các thư mục con mới flag -recursive)
terraform destroy                                   # Xóa toàn bộ resource mà tfstate hiện tại đang quản lý
terraform destroy -target=aws_db_instance.mysql    # Chỉ xóa riêng RDS instance aws_db_instance.mysql
```
