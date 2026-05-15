from pyspark.sql import SparkSession 
from pyspark.sql.functions import * 
from pyspark.sql.window import Window
import os
from pathlib import Path
import mysql.connector

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent

spark = SparkSession.builder \
    .config("spark.driver.memory", "8g") \
    .config("spark.executor.cores", 8) \
    .getOrCreate()

# Ghép tất cả file log_search t6, t7 lại với nhau & tìm ra keyword được search nhiều nhất mỗi tháng của từng user_id

def process_log_search(data):
    data = data.select('user_id','keyword')
    data = data.groupBy('user_id','keyword').count()
    data = data.withColumnRenamed('count','TotalSearch')
    data = data.orderBy('user_id',ascending = False )
    window = Window.partitionBy('user_id').orderBy(col('TotalSearch').desc())
    data = data.withColumn('Rank',row_number().over(window))
    data = data.filter(col('Rank') == 1)
    data = data.withColumnRenamed('keyword','Most_Search')
    data = data.select('user_id','Most_Search')
    return data

def load_and_process_log_search(base_path, date_prefix):
    # Lấy danh sách các folder bắt đầu bằng date_prefix
    folders = [f for f in os.listdir(base_path) if f.startswith(date_prefix) and os.path.isdir(os.path.join(base_path, f))]
    folders.sort()  # Sắp xếp theo thứ tự

    # Khởi tạo DataFrame rỗng
    full_data = None

    # Lặp qua các folder và append data vào 1 df
    for folder in folders:
        folder_path = os.path.join(base_path, folder)
        print(f"Reading: {folder}")
        data = spark.read.parquet(folder_path)
        if full_data is None:
            full_data = data
        else:
            full_data = full_data.union(data)

    # Xử lý df sau khi đã append hết
    print(f"Processing data for {date_prefix}...")
    most_searched_data = process_log_search(full_data)

    # Hiển thị kết quả
    # most_searched_data.show(20, truncate=False)
    return full_data, most_searched_data

# Xuất df tất cả (distinct) most searched keywords để LLM categorize

def most_searched_comparison_df(df1, df2, df1_prefix, df2_prefix, output_path):
# Tạo df most_searched_comparison bằng cách outer join
    most_searched_comparison = df1.withColumnRenamed('Most_Search', f'{df1_prefix}_Most_Search') \
        .join(
            df2.withColumnRenamed('Most_Search', f'{df2_prefix}_Most_Search'),
            on='user_id',
            how='outer'
        )

    # Xuất ra file CSV
    most_searched_comparison.coalesce(1).write.mode('overwrite').option('header', 'true').csv(output_path)

    print(f"Đã xuất {most_searched_comparison.count()} most searched keywords ra folder")

    # Đổi tên file CSV trong folder
    csv_file = [f for f in os.listdir(output_path) if f.endswith('.csv')][0]
    os.rename(
        os.path.join(output_path, csv_file),
        os.path.join(output_path, 'most_searched_comparison.csv')
    )

    return most_searched_comparison

def export_distinct_most_searched_keywords_to_csv(df1, df2, df1_prefix, df2_prefix, comparison_csv_path, distinct_csv_path):

    most_searched_comparison = most_searched_comparison_df(df1, df2, df1_prefix, df2_prefix, comparison_csv_path)

    # Select distinct từ cột {df1_prefix}_Most_Search
    prev_month_keywords = most_searched_comparison.select(f'{df1_prefix}_Most_Search').distinct()

    # Select distinct từ cột {df2_prefix}_Most_Search
    next_month_keywords = most_searched_comparison.select(f'{df2_prefix}_Most_Search').distinct()

    # Đổi tên cột về 'keyword' để union
    prev_month_keywords = prev_month_keywords.withColumnRenamed(f'{df1_prefix}_Most_Search', 'keyword')
    next_month_keywords = next_month_keywords.withColumnRenamed(f'{df2_prefix}_Most_Search', 'keyword')

    # Append cả 2 lại và remove duplicates
    distinct_most_searched_keywords = prev_month_keywords.union(next_month_keywords).distinct()

    # Xuất ra file CSV
    distinct_most_searched_keywords.coalesce(1).write.mode('overwrite').option('header', 'true').csv(distinct_csv_path)

    print(f"Đã xuất {distinct_most_searched_keywords.count()} distinct keywords để LLM categorize")

    # Đổi tên file CSV trong folder
    csv_file = [f for f in os.listdir(distinct_csv_path) if f.endswith('.csv')][0]
    os.rename(
        os.path.join(distinct_csv_path, csv_file),
        os.path.join(distinct_csv_path, 'distinct_most_searched_keywords.csv')
    )

# Main function
if __name__ == "__main__":
    base_path = r"C:\Users\acer\Desktop\study_de\Big Data\Dataset\Dataset\log_search"
    prev_month_data, prev_month_data_most_searched = load_and_process_log_search(base_path, '202206')
    current_month_data, current_month_most_searched = load_and_process_log_search(base_path, '202207')
    comparison_csv_path = PROJECT_DIR / "most_searched_comparison"
    distinct_csv_path = PROJECT_DIR / "distinct_most_searched_keywords"
    export_distinct_most_searched_keywords_to_csv(prev_month_data_most_searched, current_month_most_searched, "June", "July", comparison_csv_path, distinct_csv_path)