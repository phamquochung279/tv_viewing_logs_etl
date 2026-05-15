# Script này sẽ tạo bảng tổng hợp data cả tháng trên đầu Contract & đẩy lên MySQL

import findspark
findspark.init()
from pyspark.context import SparkContext
from pyspark.sql.session import SparkSession
from pyspark.sql.functions import *
import pandas as pd
from pyspark.sql.window import Window
import pyspark.sql.functions as sf
from pyspark.sql.functions import concat_ws
from datetime import datetime, timedelta
import os
from pathlib import Path
import mysql.connector
from dotenv import load_dotenv

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

def categorize_AppName(df):
    """Phân loại AppName thành Type (Truyen Hinh, Giai Tri, Thieu Nhi, Phim Truyen, The Thao), đồng thời lọc các dòng có giá trị Contract & Type lỗi."""
    df=df.withColumn("Type",when(col("AppName")=="CHANNEL","Truyen Hinh")
        .when(col("AppName")=="RELAX","Giai Tri")
        .when(col("AppName")=="CHILD","Thieu Nhi")
        .when((col("AppName")=="FIMS")|(col("AppName")=="VOD"),"Phim Truyen")
        .when((col("AppName")=="KPLUS")|(col("AppName")=="SPORT"),"The Thao")
    )
    df = df.select('Contract','Type','TotalDuration', 'Date')
    df = df.filter(df.Contract != '0' )
    df = df.filter(df.Type != 'Error')
    return df

def most_watch(df):
    """Tìm MostWatch--thể loại có số phút xem cao nhất--của từng chủ Contract."""
    df=df.withColumn("MostWatch",greatest(col("Giai Tri"),col("Phim Truyen"),col("The Thao"),col("Thieu Nhi"),col("Truyen Hinh"),col("Giai Tri")))
    df=df.withColumn("MostWatch",
                    when(col("MostWatch")==col("Truyen Hinh"),"Truyen Hinh")
                    .when(col("MostWatch")==col("Phim Truyen"),"Phim Truyen")
                    .when(col("MostWatch")==col("The Thao"),"The Thao")
                    .when(col("MostWatch")==col("Thieu Nhi"),"Thieu Nhi")
                    .when(col("MostWatch")==col("Giai Tri"),"Giai Tri"))
    return df

def customer_taste(df):
    """Tìm Taste--các thể loại chủ Contract đã xem (số phút xem >0)."""
    df=df.withColumn("Taste",concat_ws("-",
                                    when(col("Giai Tri").isNotNull(),lit("Giai Tri"))
                                    ,when(col("Phim Truyen").isNotNull(),lit("Phim Truyen"))
                                    ,when(col("The Thao").isNotNull(),lit("The Thao"))
                                    ,when(col("Thieu Nhi").isNotNull(),lit("Thieu Nhi"))
                                    ,when(col("Truyen Hinh").isNotNull(),lit("Truyen Hinh"))))
    return df

def find_active_level(df, active_threshold):
    """Thêm cột Active dựa trên số ActiveDays."""
    df=df.withColumn("Active",when(col("ActiveDays") > active_threshold,"High").otherwise("Low")
)
    return df

def final_df(df):
    """Xuất bảng tổng hợp metrics của mỗi Contract."""
    df=df.groupBy("Contract").agg(
    sf.sum("Giai Tri").alias("Total_Giai_Tri"),
    sf.sum("Phim Truyen").alias("Total_Phim_Truyen"),
    sf.sum("The Thao").alias("Total_The_Thao"),
    sf.sum("Thieu Nhi").alias("Total_Thieu_Nhi"),
    sf.sum("Truyen Hinh").alias("Total_Truyen_Hinh"),
    sf.first("MostWatch").alias("MostWatch"),
    sf.first("Taste").alias("Taste"),
    sf.first("Active").alias("Active")
)
    return df

def ETL_Spark_Dataframe(df):
    print('------------------------')
    print('Categorize AppName')
    print('------------------------')
    df = categorize_AppName(df)
    print('-----------------------------')
    print('Pivot data')
    print('-----------------------------')
    # Pivot để lấy các cột thể loại
    pivot_df = df.groupBy("Contract").pivot("Type").sum("TotalDuration")

    # Tính số dòng (Active) cho từng Contract
    active_df = df.groupBy("Contract").agg(sf.countDistinct("Date").alias("ActiveDays"))

    # Join vào pivot_df
    df = pivot_df.join(active_df, on="Contract", how="left")
    print('-----------------------------')
    print('Find MostWatch')
    print('-----------------------------')
    df = most_watch(df)
    print('-----------------------------')
    print('Find Taste')
    print('-----------------------------')
    df = customer_taste(df)
    print('-----------------------------')
    print('Find Active')
    print('-----------------------------')
    df = find_active_level(df, 4)
    print('-----------------------------')
    print('Create final summary table')
    df = final_df(df)
    return df

def convert_to_datevalue(string):
    date_value=datetime.strptime(string,"%Y%m%d").date()
    return date_value
    
def convert_to_stringvalue(date):
    string_value = date.strftime("%Y%m%d")    
    return string_value

def date_range(start_date,end_date):
    date_list=[]
    current_date=start_date
    while(current_date<=end_date):
        date_list.append(convert_to_stringvalue(current_date))
        current_date+=timedelta(days=1)
    return date_list

def generate_range_date(start_date,end_date):
    start_date= convert_to_datevalue(start_date)
    end_date= convert_to_datevalue(end_date)
    date_list=date_range(start_date,end_date)
    return date_list

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

def summary_maintask(start_date, end_date, path, save_path, table_name):

    # Tạo db (nếu chưa có)--chạy dòng này sớm để lỡ có lỗi connection DB thì đỡ mất công chạy code ETL
    print(f'Creating database {MYSQL_DB} (if not exists)')
    create_database_if_not_exists(MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB)

    # Tạo list các ngày sẽ lấy data
    date_list = generate_range_date(start_date, end_date)
    print(f"Summary ETL for {len(date_list)} days...")

    # Đọc và union tất cả file json vào 1 Spark DataFrame, thêm cột Date cho từng file trước khi union
    df_all = None
    for day in date_list:
        print(f"Reading {day}.json")
        df_day = spark.read.json(os.path.join(path, f"{day}.json")).select("_source.*")
        # Thêm cột Date dựa trên tên file
        df_day = df_day.withColumn("Date", to_date(lit(day), "yyyyMMdd"))
        if df_all is None:
            df_all = df_day
        else:
            df_all = df_all.unionByName(df_day)

    print('-----------------------------')
    print('Running ETL_Spark_Dataframe on union DataFrame')
    print('-----------------------------')
    result = ETL_Spark_Dataframe(df_all)

    print('-----------------------------')
    print('Exporting summary table as csv')
    print('-----------------------------')
    summary_save_path = os.path.join(save_path, "summary_data/")
    result.repartition(1).write.csv(summary_save_path, mode='overwrite', header=True)

    # Lấy path của file csv vừa ghi
    csv_file = None
    for file in os.listdir(summary_save_path):
        if file.startswith("part-") and file.endswith(".csv"):
            csv_file = os.path.join(summary_save_path, file)
            break

    if csv_file and os.path.exists(csv_file):
        print('-----------------------------')
        print('Import summary result to mysql')
        print('-----------------------------')
        import_to_mysql(csv_file, table_name)
        print("Finished summary job")
    else:
        print("Không tìm thấy file CSV tổng hợp")

    print("All summary jobs finished.")

if __name__ == "__main__":
    path = "C:/Users/acer/Desktop/study_de/Big Data/Dataset/Dataset/log_content/"
    save_path="C:/Users/acer/Desktop/study_de/Big Data/BigData_Gen14/Class 6 - ETL Pipeline/DataSummary/"
    start_date = "20220401"
    end_date = "20220430"
    table_name = 'customer_content_stats_summary'
    summary_maintask(start_date, end_date, path,save_path, table_name)