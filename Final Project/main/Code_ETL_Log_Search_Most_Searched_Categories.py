from dotenv import load_dotenv
from pyspark.sql import SparkSession 
from pyspark.sql.functions import * 
from pyspark.sql.window import Window
import os
from pathlib import Path
import mysql.connector

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent

load_dotenv(PROJECT_DIR / "credentials.env")

MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_PORT = int(os.getenv("MYSQL_PORT"))
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_DB = os.getenv("MYSQL_DB")

spark = SparkSession.builder \
    .config("spark.driver.memory", "8g") \
    .config("spark.executor.cores", 8) \
    .config("spark.jars", str(PROJECT_DIR / "mysql-connector-j-8.0.33.jar")) \
    .getOrCreate()

# Join các cặp keywords-categories đã được LLM xử lý vào df gốc

def clean_and_load_categorized_keywords(input_file, output_file):
    """Làm sạch file txt, loại bỏ dòng trống và dòng bắt đầu bằng '# batch'"""
    with open(input_file, "r", encoding="utf-8") as infile, open(output_file, "w", encoding="utf-8") as outfile:
        for line in infile:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.lower().startswith("# batch"):
                continue
            outfile.write(line)

    from pyspark.sql.types import StructType, StructField, StringType

    # Định nghĩa schema cho file CSV
    schema = StructType([
        StructField("keyword", StringType(), True),
        StructField("category", StringType(), True)
    ])

    # Đọc file đã làm sạch bằng Spark
    keywords = spark.read.csv(
        output_file,
        sep="###",
        schema=schema,
        encoding="utf-8"
    )

    # Loại bỏ khoảng trắng cả 2 đầu của các giá trị keyword và category
    keywords = keywords \
        .withColumn("keyword", trim(keywords["keyword"])) \
        .withColumn("category", trim(keywords["category"]))
    
    # Xoá file cleaned
    os.remove(output_file)

    return keywords

def join_and_export_df_with_categories(most_searched_comparison, prev_month, current_month, keywords_categorized, output_csv_path):
    from pyspark.sql.functions import col, trim, row_number
    from pyspark.sql.window import Window

    # Trim whitespace của {prev_month}_Most_Search & {current_month}_Most_Search
    most_searched_comparison_trimmed = most_searched_comparison \
        .withColumn(f'{prev_month}_Most_Search', trim(col(f'{prev_month}_Most_Search'))) \
        .withColumn(f'{current_month}_Most_Search', trim(col(f'{current_month}_Most_Search')))

    # Loại bỏ trùng lặp keyword trong keywords_categorized (chỉ lấy category đầu tiên nếu bị trùng)
    window_spec = Window.partitionBy('keyword').orderBy('category')
    keywords_categorized_unique = keywords_categorized \
        .withColumn('row_num', row_number().over(window_spec)) \
        .filter(col('row_num') == 1) \
        .drop('row_num')

    # Join với {prev_month}_Most_Search
    joined_prev = most_searched_comparison_trimmed.join(
        keywords_categorized_unique.withColumnRenamed('category', f'{prev_month}_Category'),
        col(f'{prev_month}_Most_Search') == col('keyword'),
        how='left'
    ).drop(keywords_categorized_unique['keyword'])

    # Join với {current_month}_Most_Search
    joined_full = joined_prev.join(
        keywords_categorized_unique.withColumnRenamed('category', f'{current_month}_Category'),
        col(f'{current_month}_Most_Search') == col('keyword'),
        how='left'
    ).drop(keywords_categorized_unique['keyword'])

    # joined_full.show(1000, truncate=False)

    # Chuyển đổi Spark DataFrame 'joined_full' sang Pandas DataFrame
    joined_full_pd = joined_full.toPandas()

    # Export joined_full DataFrame to CSV
    joined_full_pd.to_csv(output_csv_path, index=False, encoding="utf-8")
    print(f"Đã xuất bảng final ra file {output_csv_path}")

# Đẩy lên MySQL

def create_database_if_not_exists(host, port, user, password, db_name):
    conn = mysql.connector.connect(
        host=host,
        port=port,
        user=user,
        password=password
    )
    cursor = conn.cursor()
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
    cursor.close()
    conn.close()

def import_to_mysql(csv_path, table_name):
    conn = mysql.connector.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB,
        allow_local_infile=True
    )
    cursor = conn.cursor()
    # Tạo bảng nếu chưa tồn tại
    create_sql = (
        f"CREATE TABLE IF NOT EXISTS {table_name} ("
        "user_id INT,"
        "June_Most_Search VARCHAR(255),"
        "July_Most_Search VARCHAR(255),"
        "June_Category VARCHAR(255),"
        "July_Category VARCHAR(255)"
        ")"
    )
    cursor.execute(create_sql)
    # Kiểm tra bảng đã có data chưa
    cursor.execute(f"SELECT EXISTS (SELECT 1 FROM {table_name} LIMIT 1)")
    has_data = cursor.fetchone()[0]
    if has_data == 1:
        # Nếu có data thì xóa hết trước khi import (overwrite)
        cursor.execute(f"DELETE FROM {table_name}")
    # Import dữ liệu
    load_sql = f"""
    LOAD DATA LOCAL INFILE '{csv_path}'
    INTO TABLE {table_name}
    FIELDS TERMINATED BY ',' 
    ENCLOSED BY '\"'
    LINES TERMINATED BY '\\n'
    IGNORE 1 LINES;
    """
    cursor.execute(load_sql)
    conn.commit()
    cursor.close()
    conn.close()
    print("Data Imported Successfully")

# Main function
if __name__ == "__main__":
    input_file = PROJECT_DIR / "distinct_most_searched_keywords_categorized.txt"
    output_file = PROJECT_DIR / "distinct_most_searched_keywords_categorized_cleaned.txt"
    keyword_categorized_df = clean_and_load_categorized_keywords(input_file, output_file)
    most_searched_comparison_df = spark.read.csv(
        str(PROJECT_DIR / "most_searched_comparison" / "most_searched_comparison.csv"),
        header=True,
        inferSchema=True
    )
    output_csv_path = PROJECT_DIR / "most_searched_category_june_vs_july.csv"
    join_and_export_df_with_categories(most_searched_comparison_df, "June", "July", keyword_categorized_df, output_csv_path)
    create_database_if_not_exists(MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB)
    import_to_mysql(output_csv_path, 'customer_most_searched_categories')