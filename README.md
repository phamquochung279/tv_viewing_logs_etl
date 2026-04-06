# TV Viewing Log - Data Engineering Project

Bài tập cuối khóa của lớp DE anh Trần Hoàng Long. Project này hoạt động theo các bước sau: 
1) Xử lý & tổng hợp data ở 2 folder `log_content` & `log_search`
2) Bắn các bảng data tổng hợp lên DB
3) Kết nối viz tool với data trong DB để vẽ dashboard

## 1. Cài đặt môi trường và thư viện

### Prerequisites:

- **Python**: 3.8
- **Spark**: 3.3.0
- **Hadoop**: 3.0
- **Java**: 18.0.2.1
- **MySQL Connector/ODBC**: 8.0.33

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

Ở project này chúng ta dùng AWS, bạn có thể thử các cloud platform khác nếu muốn.

- Login vào AWS. Search & click vào Service **Aurora and RDS**. Vào tab **Database** & ấn **Create database**.
- *Choose a database creation method*: chọn **Standard create**
- *Engine options*: chọn **MySQL** cho *Engine types* & **8.0.42** cho *Engine version*
- Điền các trường *DB instance identifier*, *Master username*, *Master password* tùy theo ý thích.
- *Public access*: chọn **Yes** (cho đơn giản)
- *VPC security group*: chọn **Choose existing** nếu bạn đã có sẵn 1 Security Group cho phép "My IP" truy cập port 3306.
    
    Nếu chưa thì chọn **Create new**, lát nữa tạo DB xong thì sang **EC2/Security Group** tìm Security Group vừa tạo & cho phép "My IP" truy cập port 3306.
- Các configs còn lại giữ nguyên, Rê đến cuối trang và click **Create database**.
- Chờ đến khi DB instance chuyển sang Status "Available" là **XONG!**

## 3. Update credentials

- Sau khi status của DB instance chuyển sang "Available", click vào DB identifier --> tab **Connectivity & security** để lấy endpoint, port (mặc định là 3306)

- Username & password nãy bạn đặt là gì vẫn còn nhớ chứ?

- Sửa file `credentials_sample.env` với các thông tin của bạn:
```
MYSQL_HOST=endpoint của DB instance vừa tạo

MYSQL_PORT=3306

MYSQL_USER=Master username đã nhập khi tạo DB instance

MYSQL_PASSWORD=Master password đã nhập khi tạo DB instance

MYSQL_DB=tên DB bạn muốn tạo để lưu các bảng data mà project này làm ra (KHÔNG NHẦM LẪN với tên bạn đặt cho DB instance khi tạo nó)

```

## 4. Xử lý & đẩy bảng customer_content_stats_summary lên DB

Chạy script `Code_ETL_Log_Content_Summary.py` để xử lý dữ liệu log_content và đẩy thành bảng `customer_content_stats_summary` lên MySQL.

## 5. Tạo file most_searched_keywords.csv

- Chạy script `Code_ETL_Log_Search_Most_Searched_Keywords.py` để xử lý dữ liệu log_search và sinh 2 file:  `most_searched_comparison.csv` & `distinct_most_searched_keywords.csv`.
    - `most_searched_comparison.csv` chứa 3 cột: `user_id`, `từ khóa được tìm nhiều nhất vào T6`, `từ khóa được tìm nhiều nhất vào T7`.
    - `distinct_most_searched_keywords.csv` chứa duy nhất 1 cột `keywords`--là các unique keywords được tìm nhiều nhất T6 & T7 bởi từng `user_id`. --> chúng ta cần nhờ LLM phân loại các keyword này thuộc category gì.

## 6. Phân loại keywords bằng LLM

- Cài đặt [LMStudio](https://lmstudio.ai/) & tải 1 model LLM tùy chọn (nên là 1 model chuyên về text categorization, và có thể chạy được trên máy bạn mà không bốc cháy). Ở đây tôi đang dùng model **qwen2.5-7b-instruct**.
- Ở panel bên tay trái, chọn tab *Developer* --> click nút toggle *Start Server* hoặc tổ hợp *Ctrl + R*. Status sẽ chuyển thành *Running*, và text Server not running sẽ chuyển thành *Reachable at http://{IP của bạn}:{server port}* --> Model đã được host ở local & sẵn sàng để sử dụng.
- Mở và chạy notebook `Using_LLM_To_Categorize_Keywords.ipynb` để nhận file `distinct_most_searched_keywords.csv` & thu về file `distinct_most_searched_keywords_categorized.txt`.

NOTE: Nếu lap bạn cũng cùi bắp như tôi, process hết *148k keywords* có thể mất vài ngày trời. Xin mời tận dụng file `distinct_most_searched_keywords_categorized.txt` có sẵn của tôi nếu không muốn chờ lâu.

## 7. Đẩy bảng customer_most_searched_categories lên DB

Chạy script `Code_ETL_Log_Search_Most_Searched_Categories.py` để:
- Kết hợp 2 file `most_searched_comparison.csv` & `distinct_most_searched_keywords_categorized.txt` thành bảng hoàn chỉnh gồm 5 cột: user_id, từ khóa search nhiều nhất T6 & T7, thể loại search nhiều nhất T6 & T7
- Đẩy thành bảng `customer_most_searched_categories` lên MySQL.

## 8. Kết nối Power BI với DB và vẽ dashboard

- Nếu bạn connect được Power BI với DB instance bằng phương thức MySQL --> Xin chúc mừng, bạn là người may mắn!
    
- Còn nếu không: thử dùng **MYSQL_CONNECTION_STRING** trong `credentials_sample.env` để connect Power BI với instance DB thông qua phương thức ODBC

Connect xong, load các bảng & dùng data để vẽ dashboard (tham khảo dashboard tồi tàn của tôi ở file `study-de-final-project-Pham-Quoc-Hung.pbix`).

## Contact

Author: Phạm Quốc Hùng <br />

<a href="mailto:pham.quochung0999@gmail.com">![Gmail](https://img.shields.io/badge/Gmail-D14836?style=for-the-badge&logo=gmail&logoColor=white)</a> <a href="https://public.tableau.com/app/profile/hung.pham279">![Tableau](https://img.shields.io/badge/Tableau-E97627?style=for-the-badge&logo=Tableau&logoColor=white)</a> <a href="https://github.com/phamquochung279">![Github](https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white)</a> <a href="https://www.linkedin.com/in/pham-quochung/">![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)</a>
