([English below](#final-project-folder---installation--usage-guide))

# Final Project Folder - Hướng dẫn cài đặt & sử dụng

<a href="TV Viewing Logs.png" target="_blank">
  <img src="TV Viewing Logs.png" alt="TV Viewing Logs Project Architecture" title="TV Viewing Logs Project Architecture" width="100%">
</a>

Bài tập cuối khóa của lớp DE anh Trần Hoàng Long. Project này hoạt động theo các bước sau: 
1) Xử lý & tổng hợp 8GB data raw ở 2 folder `log_content` & `log_search` bằng PySpark và self-hosted LLM tùy chọn *(2 folder này không tiện show public, vui lòng liên hệ tôi để lấy)*
2) Bắn các bảng data tổng hợp lên DB (AWS RDS, tạo bởi Terraform hoặc thủ công)
3) Kết nối viz tool (Power BI) với data trong DB để vẽ dashboard

## 1. Cài đặt môi trường và thư viện

### Prerequisites:

- **Python**: 3.8
- **Spark**: 3.3.0
- **Hadoop**: 3.0
- **Java**: 18.0.2.1
- **Terraform**: >= 1.0
- **MySQL Connector/ODBC**: 8.0.33
- **AWS CLI**: v2 (nếu muốn dùng Terraform, AWS CLI là cần thiết để chạy `aws configure`)

### Cấu hình AWS Credentials (nếu dùng Terraform)

- **Local machine (khuyên dùng cho project này):**
  ```bash
  aws configure
  ```
  Nhập lần lượt các giá trị được yêu cầu:
  - AWS Access Key ID
  - AWS Secret Access Key
  - Default region name (ví dụ: `ap-southeast-1`)
  - Default output format (`json`)

  #### NOTE: Cách lấy AWS Access Key ID & AWS Secret Access Key

  1. Đăng nhập AWS Console bằng user có quyền IAM.
  2. Vào service **IAM** -> **Users** -> chọn user của bạn.
  3. Chọn tab **Security credentials**.
  4. Ở mục **Access keys**, bấm **Create access key**.
  5. Chọn use case phù hợp (thường là CLI hoặc Local code), rồi bấm **Create access key**.
  6. Copy ngay 2 giá trị sau:
      - **Access Key ID**
      - **Secret Access Key**

  Lưu ý:
  - AWS chỉ hiển thị **Secret Access Key** đúng 1 lần tại màn hình tạo key. Nếu quên không lưu lại, bạn phải tạo key mới.
  - Nên dùng IAM User riêng cho project, cấp quyền tối thiểu cần thiết (ví dụ chỉ RDS/VPC liên quan), tránh dùng root account.

Cuối cùng, kiểm tra credentials đã hoạt động chưa:
```bash
aws sts get-caller-identity
```

Terraform sẽ tự gọi AWS API thông qua AWS provider, bạn chỉ cần đảm bảo máy chạy Terraform có mạng đi tới AWS API endpoints (internet/NAT/VPC endpoints tùy kiến trúc mạng). Thường thì máy local bình thường đã có access sẵn, không cần phải làm gì thêm.

Để kiểm tra cho chắc, chạy script PowerShell dưới đây trên máy local:

```powershell
# Quick check: DNS + TCP 443 + STS + RDS API
$region = "ap-southeast-1"
$endpoints = @(
  "sts.$region.amazonaws.com",
  "rds.$region.amazonaws.com",
  "ec2.$region.amazonaws.com",
  "iam.amazonaws.com"
)

Write-Host "== 1) AWS CLI version =="
aws --version

Write-Host "`n== 2) DNS and TCP 443 checks =="
foreach ($ep in $endpoints) {
  $dnsOk = $false
  $tcpOk = $false

  try {
    Resolve-DnsName $ep -ErrorAction Stop | Out-Null
    $dnsOk = $true
  } catch {
    $dnsOk = $false
  }

  try {
    $tcp = Test-NetConnection $ep -Port 443 -WarningAction SilentlyContinue
    $tcpOk = [bool]$tcp.TcpTestSucceeded
  } catch {
    $tcpOk = $false
  }

  Write-Host ("{0} | DNS={1} | TCP443={2}" -f $ep, $dnsOk, $tcpOk)
}

Write-Host "`n== 3) STS identity check =="
aws sts get-caller-identity --region $region

Write-Host "`n== 4) RDS API check =="
aws rds describe-db-engine-versions --region $region --max-items 5 | Out-Null
if ($LASTEXITCODE -eq 0) {
  Write-Host "RDS API reachable: PASS"
} else {
  Write-Host "RDS API reachable: FAIL"
}
```

Nếu các endpoint đều có `TCP443=True` và lệnh STS/RDS không lỗi, thì máy local **đã sẵn sàng** để chạy Terraform.

### Dependencies:

Các lib cần dùng trong project này bao gồm:

```
pyspark==3.3.0
mysql-connector-python==2.2.9
pandas==2.0.3
dotenv==1.0.1
findspark==2.0.1
openai==2.2.0
```

Tạo .venv rồi cài đặt bằng lệnh:
```
pip install -r requirements.txt
```

## 2. Tạo database MySQL

> **💡 Note**: Bước này **đã được cover hoàn toàn bởi Terraform**. Bạn có thể chọn **Cách 1: Terraform (Recommended)** để tự động hóa, hoặc làm **Thủ Công** nếu muốn.

Ở project này chúng ta dùng AWS, bạn có thể thử các cloud platform khác nếu muốn.

### Cách 1: Sử Dụng Terraform (Recommended)

Bạn có thể dùng Terraform để tự động hóa hoàn toàn quá trình tạo DB trên AWS này:

```bash
# 1. Vào thư mục Terraform
cd terraform

# 2. Copy file ví dụ và sửa các thông tin
cp terraform.tfvars.example terraform.tfvars
# Mở terraform.tfvars và sửa:
#   - db_instance_identifier (tên unique)
#   - master_username (username MySQL)
#   - master_password (password - ≥8 ký tự)
#   - db_name (tên database)

# 3. Khởi tạo & Deploy
terraform init
terraform plan      # Xem plan trước
terraform apply     # Chạy (gõ 'yes')

# 4. Chờ 5-10 phút cho RDS instance được tạo...

# 5. Lấy connection info
terraform output credentials_env_template
```

Một vài lệnh Terraform hay dùng thêm:
```bash
terraform validate
terraform fmt -recursive
terraform destroy
terraform destroy -target=aws_db_instance.mysql
```

**Xem thêm**: [terraform/README.md](terraform/README.md) để hiểu chi tiết về Terraform setup.

### Cách 2: Thủ Công

Nếu bạn muốn làm mọi thứ bằng tay cho đơn giản:

- Login vào AWS.
- Chọn 1 region nào đó gần Việt Nam (VD: **ap-southeast-1**, tức Singapore) để tối ưu tốc độ & chi phí.
- Search & click vào Service **Aurora and RDS**. Vào tab **Database** & ấn **Create database**.
- *Choose a database creation method*: chọn **Standard create**
- *Engine options*: chọn **MySQL** cho *Engine types* & **8.0.42** cho *Engine version*
- Điền các trường *DB instance identifier*, *Master username*, *Master password* tùy theo ý thích.
    - NOTE: username không được để là "root", "mysql", "admin". Password phải có ít nhất 8 kí tự, nên có special chars, chữ hoa, chữ thường và số.
- *Public access*: chọn **Yes** (cho đơn giản)
- *VPC security group*: chọn **Choose existing** nếu bạn đã có sẵn 1 Security Group cho phép "My IP" truy cập port 3306.
    
    Nếu chưa thì chọn **Create new**, lát nữa tạo DB xong thì sang **EC2/Security Group** tìm Security Group vừa tạo & cho phép "My IP" truy cập port 3306.
- Các configs còn lại giữ nguyên, Rê đến cuối trang và click **Create database**.
- Chờ đến khi DB instance chuyển sang Status "Available" là **XONG!**

## 3. Update credentials

> **💡 Note**: Nếu bạn dùng **Terraform** ở bước 2, phần này sẽ được **tự động xử lý**. Nếu làm thủ công, hãy làm theo hướng dẫn bên dưới.

### Nếu dùng Terraform cho bước 2: 

Để output các thông tin connection, chạy lệnh:

```bash
# Trong thư mục terraform/
terraform output credentials_env_template
```

Để tự động cập nhật **các biến đã có sẵn** trong file `Final Project/credentials.env` bằng các thông tin connection trong output, chạy script PowerShell sau trong folder `terraform/`:

```powershell
$target = "..\Final Project\credentials.env"
$template = terraform output -raw credentials_env_template

$templateMap = @{}
$template -split "`r?`n" | ForEach-Object {
  if ($_ -match '^\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$') {
    $templateMap[$matches[1]] = $matches[2]
  }
}

$updated = Get-Content $target | ForEach-Object {
  if ($_ -match '^\s*([A-Z0-9_]+)\s*=') {
    $k = $matches[1]
    if ($templateMap.ContainsKey($k)) {
      "${k}=$($templateMap[$k])"
    } else {
      $_
    }
  } else {
    $_
  }
}

Set-Content -Path $target -Value $updated -Encoding utf8
```

### Nếu làm thủ công bước 2:

- Sau khi status của DB instance chuyển sang "Available", click vào DB identifier --> tab **Connectivity & security** để lấy endpoint, port (mặc định là 3306)

- Sửa file `credentials_sample.env` với các thông tin của bạn:
```
MYSQL_HOST=endpoint của DB instance vừa tạo

MYSQL_PORT=3306

MYSQL_USER=Master username đã nhập khi tạo DB instance

MYSQL_PASSWORD=Master password đã nhập khi tạo DB instance

MYSQL_DB=tên DB bạn muốn tạo để lưu các bảng data mà project này làm ra (KHÔNG NHẦM LẪN với tên bạn đặt cho DB instance khi tạo nó)

```

## 4. Xử lý & đẩy bảng customer_content_stats_summary lên DB

Chạy script `Final Project/main/Code_ETL_Log_Content_Summary.py` để xử lý dữ liệu log_content và đẩy thành bảng `customer_content_stats_summary` lên MySQL.

## 5. Tạo file most_searched_keywords.csv

- Chạy script `Final Project/main/Code_ETL_Log_Search_Most_Searched_Keywords.py` để xử lý dữ liệu log_search và sinh 2 file:  `most_searched_comparison.csv` & `distinct_most_searched_keywords.csv`.
    - `most_searched_comparison.csv` chứa 3 cột: `user_id`, `từ khóa được tìm nhiều nhất vào T6`, `từ khóa được tìm nhiều nhất vào T7`.
    - `distinct_most_searched_keywords.csv` chứa duy nhất 1 cột `keywords`--là các unique keywords được tìm nhiều nhất T6 & T7 bởi từng `user_id`. --> chúng ta cần nhờ LLM phân loại các keyword này thuộc category gì.

## 6. Phân loại keywords bằng LLM

- Cài đặt [LMStudio](https://lmstudio.ai/) & tải 1 model LLM tùy chọn (nên là 1 model chuyên về text categorization, và có thể chạy được trên máy bạn mà không bốc cháy). Ở đây tôi đang dùng model **qwen2.5-7b-instruct**.
- Ở panel bên tay trái, chọn tab *Developer* --> click nút toggle *Start Server* hoặc tổ hợp *Ctrl + R*. Status sẽ chuyển thành *Running*, và text Server not running sẽ chuyển thành *Reachable at http://{IP của bạn}:{server port}* --> Model đã được host ở local & sẵn sàng để sử dụng.
- Chạy script `Final Project/main/Using_LLM_To_Categorize_Keywords.py` để đọc file `distinct_most_searched_keywords.csv` & thu về file `distinct_most_searched_keywords_categorized.txt`.

NOTE: Nếu lap bạn cũng cùi bắp như tôi, process hết *148k keywords* có thể mất vài ngày trời. Xin mời tận dụng file `distinct_most_searched_keywords_categorized.txt` có sẵn của tôi nếu không muốn chờ lâu.

## 7. Đẩy bảng customer_most_searched_categories lên DB

Chạy script `Final Project/main/Code_ETL_Log_Search_Most_Searched_Categories.py` để:
- Kết hợp 2 file `most_searched_comparison.csv` & `distinct_most_searched_keywords_categorized.txt` thành bảng hoàn chỉnh gồm 5 cột: user_id, từ khóa search nhiều nhất T6 & T7, thể loại search nhiều nhất T6 & T7
- Đẩy thành bảng `customer_most_searched_categories` lên MySQL.

## 8. Kết nối Power BI với DB và vẽ dashboard

- Nếu bạn connect được Power BI với DB instance bằng phương thức MySQL --> Xin chúc mừng, bạn là người may mắn!
    
- Còn nếu không: thử dùng **MYSQL_CONNECTION_STRING** trong `credentials_sample.env` để connect Power BI với instance DB thông qua phương thức ODBC

Connect xong, load các bảng & dùng data để vẽ dashboard (tham khảo dashboard tồi tàn của tôi ở file `powerbi\study-de-final-project-Pham-Quoc-Hung.pbix`).

![Power BI dashboard page 1](Final%20Project/powerbi/powerbi_dashboard_page1.png)

![Power BI dashboard page 2](Final%20Project/powerbi/powerbi_dashboard_page2.png)

## Contact

Author: Phạm Quốc Hùng <br />

<a href="mailto:pham.quochung0999@gmail.com">![Gmail](https://img.shields.io/badge/Gmail-D14836?style=for-the-badge&logo=gmail&logoColor=white)</a> <a href="https://public.tableau.com/app/profile/hung.pham279">![Tableau](https://img.shields.io/badge/Tableau-E97627?style=for-the-badge&logo=Tableau&logoColor=white)</a> <a href="https://github.com/phamquochung279">![Github](https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white)</a> <a href="https://www.linkedin.com/in/pham-quochung/">![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)</a>

---

# Final Project Folder - Installation & Usage Guide

<a href="TV Viewing Logs.png" target="_blank">
  <img src="TV Viewing Logs.png" alt="TV Viewing Logs Project Architecture" title="TV Viewing Logs Project Architecture" width="100%">
</a>

This is the capstone project for the Data Engineering course by Mr. Trần Hoàng Long. The project works as follows:
1) Process & aggregate data from 2 folders `log_content` & `log_search` *(these 2 folders are not publicly available — please contact me to get them if you want)*
2) Push the aggregated data tables to a DB
3) Connect a viz tool to the data in DB to build a dashboard

## 1. Environment & Library Setup

### Prerequisites:

- **Python**: 3.8
- **Spark**: 3.3.0
- **Hadoop**: 3.0
- **Java**: 18.0.2.1
- **Terraform**: >= 1.0
- **AWS CLI**: v2 (required to run `aws configure`)
- **MySQL Connector/ODBC**: 8.0.33

### Configure AWS Credentials & AWS API (for Terraform)

This part is **not configured inside this project source code**. You must configure it externally before running Terraform.

- **Local machine (recommended for this project):**
  ```bash
  aws configure
  ```
  Then provide:
  - AWS Access Key ID
  - AWS Secret Access Key
  - Default region name (example: `ap-southeast-1`)
  - Default output format (`json`)

  ### How to Get AWS Access Key ID & AWS Secret Access Key

  1. Sign in to AWS Console with an IAM-enabled account.
  2. Go to **IAM** -> **Users** -> select your user.
  3. Open the **Security credentials** tab.
  4. In **Access keys**, click **Create access key**.
  5. Choose the appropriate use case (usually CLI or Local code), then click **Create access key**.
  6. Copy and store these two values immediately:
    - **Access Key ID**
    - **Secret Access Key**

  Notes:
  - AWS shows **Secret Access Key** only once at creation time. If you lose it, create a new key.
  - Use a dedicated IAM user with least-privilege permissions for this project (for example only required RDS/VPC actions). Avoid using the root account.

Validate credentials:
```bash
aws sts get-caller-identity
```

Terraform calls AWS APIs automatically through the AWS provider, you only need network connectivity from the machine running Terraform to AWS API endpoints (internet/NAT/VPC endpoints depending on your network architecture). Usually your local machine would have access by default, you don't have to configure anything beforehand.

Quick check script for **local machine (PowerShell)**:

```powershell
# Quick check: DNS + TCP 443 + STS + RDS API
$region = "ap-southeast-1"
$endpoints = @(
  "sts.$region.amazonaws.com",
  "rds.$region.amazonaws.com",
  "ec2.$region.amazonaws.com",
  "iam.amazonaws.com"
)

Write-Host "== 1) AWS CLI version =="
aws --version

Write-Host "`n== 2) DNS and TCP 443 checks =="
foreach ($ep in $endpoints) {
  $dnsOk = $false
  $tcpOk = $false

  try {
    Resolve-DnsName $ep -ErrorAction Stop | Out-Null
    $dnsOk = $true
  } catch {
    $dnsOk = $false
  }

  try {
    $tcp = Test-NetConnection $ep -Port 443 -WarningAction SilentlyContinue
    $tcpOk = [bool]$tcp.TcpTestSucceeded
  } catch {
    $tcpOk = $false
  }

  Write-Host ("{0} | DNS={1} | TCP443={2}" -f $ep, $dnsOk, $tcpOk)
}

Write-Host "`n== 3) STS identity check =="
aws sts get-caller-identity --region $region

Write-Host "`n== 4) RDS API check =="
aws rds describe-db-engine-versions --region $region --max-items 5 | Out-Null
if ($LASTEXITCODE -eq 0) {
  Write-Host "RDS API reachable: PASS"
} else {
  Write-Host "RDS API reachable: FAIL"
}
```

If all endpoints show `TCP443=True` and both STS/RDS commands succeed, your local machine is ready to use Terraform.

### Dependencies:

Libraries required for this project:

```
pyspark==3.3.0
mysql-connector-python==2.2.9
pandas==2.0.3
dotenv==1.0.1
findspark==2.0.1
openai==2.2.0
```

Create a .venv then install with:
```
pip install -r requirements.txt
```

## 2. Create MySQL Database

> **💡 Note**: This step is **fully covered by Terraform**. You can choose **Terraform Method (Recommended)** to automate the entire process, or do it **Manually** if you prefer.

This project uses AWS. You may try other cloud platforms if you wish.

### Method 1: Using Terraform (Recommended)

Instead of manually clicking through the AWS Console, you can use Terraform to fully automate the entire process:

```bash
# 1. Navigate to Terraform directory
cd terraform

# 2. Copy example file and edit the values
cp terraform.tfvars.example terraform.tfvars
# Open terraform.tfvars and update:
#   - db_instance_identifier (unique name)
#   - master_username (MySQL username)
#   - master_password (password - ≥8 characters)
#   - db_name (database name)

# 3. Initialize & Deploy
terraform init
terraform plan      # View plan first
terraform apply     # Execute (type 'yes')

# 4. Wait 5-10 minutes for RDS instance creation...

# 5. Get connection info
terraform output credentials_env_template
```

A few more useful Terraform commands:
```bash
terraform validate
terraform fmt -recursive
terraform destroy
terraform destroy -target=aws_db_instance.mysql
```

**Advantages**:
- ⚡ 2-3x faster
- 🔄 Reusable for multiple projects
- 📝 Infrastructure as Code (version control friendly)
- 🚀 CI/CD friendly

**Learn more**: [terraform/README.md](terraform/README.md) for detailed Terraform setup guide.

### Method 2: Manual Setup

If you prefer to do things manually:

- Log in to AWS. Search & click on the **Aurora and RDS** service. Go to the **Database** tab & click **Create database**.
- *Choose a database creation method*: select **Standard create**
- *Engine options*: select **MySQL** for *Engine types* & **8.0.42** for *Engine version*
- Fill in the *DB instance identifier*, *Master username*, *Master password* fields as you like.
- *Public access*: select **Yes** (for simplicity)
- *VPC security group*: select **Choose existing** if you already have a Security Group that allows "My IP" to access port 3306.
    
    If not, select **Create new**, then after the DB is created, go to **EC2/Security Group**, find the newly created Security Group & allow "My IP" to access port 3306.
- Leave all other configs as default, scroll to the bottom of the page and click **Create database**.
- Wait until the DB instance status changes to "Available" — **DONE!**

## 3. Update Credentials

> **💡 Note**: If you used **Terraform** in step 2, this step is **automatically handled**. If you did it manually, follow the guide below.

### If Using Terraform

To print out the connection information, run this command:

```bash
# Inside terraform/ directory
terraform output credentials_env_template
```

To update **the existing variables** in `Final Project/credentials.env` with the connection info returned by output, run this PowerShell script from the `terraform/` directory:

```powershell
$target = "..\Final Project\credentials.env"
$template = terraform output -raw credentials_env_template

$templateMap = @{}
$template -split "`r?`n" | ForEach-Object {
  if ($_ -match '^\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$') {
    $templateMap[$matches[1]] = $matches[2]
  }
}

$updated = Get-Content $target | ForEach-Object {
  if ($_ -match '^\s*([A-Z0-9_]+)\s*=') {
    $k = $matches[1]
    if ($templateMap.ContainsKey($k)) {
      "${k}=$($templateMap[$k])"
    } else {
      $_
    }
  } else {
    $_
  }
}

Set-Content -Path $target -Value $updated -Encoding utf8
```

This keeps comments/other lines unchanged and updates only keys that already exist in `credentials.env`.

### If Using Manual Setup

- Once the DB instance status changes to "Available", click on the DB identifier --> **Connectivity & security** tab to get the endpoint and port (default is 3306)

- Edit the `credentials_sample.env` file with your information:
```
MYSQL_HOST=endpoint of the DB instance you just created

MYSQL_PORT=3306

MYSQL_USER=Master username entered when creating the DB instance

MYSQL_PASSWORD=Master password entered when creating the DB instance

MYSQL_DB=the name of the DB you want to create to store the data tables produced by this project (DO NOT confuse this with the name you gave the DB instance when creating it)

```

## 4. Process & Push the customer_content_stats_summary Table to DB

Run the script `Final Project/main/Code_ETL_Log_Content_Summary.py` to process the log_content data and push it as the `customer_content_stats_summary` table to MySQL.

## 5. Create the most_searched_keywords.csv File

- Run the script `Final Project/main/Code_ETL_Log_Search_Most_Searched_Keywords.py` to process the log_search data and generate 2 files: `most_searched_comparison.csv` & `distinct_most_searched_keywords.csv`.
    - `most_searched_comparison.csv` contains 3 columns: `user_id`, `most searched keyword in June`, `most searched keyword in July`.
    - `distinct_most_searched_keywords.csv` contains a single column `keywords` — the unique keywords most searched in June & July by each `user_id`. --> We need the LLM to categorize what category these keywords belong to.

## 6. Categorize Keywords Using LLM

- Install [LMStudio](https://lmstudio.ai/) & download an LLM model of your choice (preferably one specialized in text categorization, and one that your machine can run without bursting into flames). Here I am using the **qwen2.5-7b-instruct** model.
- In the left panel, select the *Developer* tab --> click the *Start Server* toggle button or press *Ctrl + R*. The status will change to *Running*, and the text "Server not running" will change to *Reachable at http://{your IP}:{server port}* --> The model is now hosted locally & ready to use.
- Run the script `Final Project/main/Using_LLM_To_Categorize_Keywords.py` to read `distinct_most_searched_keywords.csv` and produce `distinct_most_searched_keywords_categorized.txt`.

NOTE: If you have a potato PC like I do, processing all *148k keywords* can take several days. Feel free to use my pre-made `distinct_most_searched_keywords_categorized.txt` file if you don't have the time.

## 7. Push the customer_most_searched_categories Table to DB

Run the script `Final Project/main/Code_ETL_Log_Search_Most_Searched_Categories.py` to:
- Combine the 2 files `most_searched_comparison.csv` & `distinct_most_searched_keywords_categorized.txt` into a complete table with 5 columns: user_id, most searched keyword in June & July, most searched category in June & July
- Push it as the `customer_most_searched_categories` table to MySQL.

## 8. Connect Power BI to DB and Build Dashboard

- If you can connect Power BI to the DB instance via MySQL — congratulations, you're a lucky one!
    
- If not: try using **MYSQL_CONNECTION_STRING** in `credentials_sample.env` to connect Power BI to the DB instance via ODBC

Once connected, load the tables & use the data to build a dashboard (feel free to reference my humble dashboard in the file `powerbi\study-de-final-project-Pham-Quoc-Hung.pbix`).

![Power BI dashboard page 1](Final%20Project/powerbi/powerbi_dashboard_page1.png)

![Power BI dashboard page 2](Final%20Project/powerbi/powerbi_dashboard_page2.png)

## Contact

Author: Phạm Quốc Hùng <br />

<a href="mailto:pham.quochung0999@gmail.com">![Gmail](https://img.shields.io/badge/Gmail-D14836?style=for-the-badge&logo=gmail&logoColor=white)</a> <a href="https://public.tableau.com/app/profile/hung.pham279">![Tableau](https://img.shields.io/badge/Tableau-E97627?style=for-the-badge&logo=Tableau&logoColor=white)</a> <a href="https://github.com/phamquochung279">![Github](https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white)</a> <a href="https://www.linkedin.com/in/pham-quochung/">![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)</a>

---

