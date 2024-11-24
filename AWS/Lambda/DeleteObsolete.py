from datetime import datetime
from datetime import timedelta
import pymysql
import pytz
import os

# read these from environment variables
DB_PWD = os.environ.get("DB_PWD")
DB_HOST = os.environ.get("DB_HOST")
DB_USER = os.environ.get("DB_USER")
DB_NAME = os.environ.get("DB_NAME")


def convert_to_singapore_time(dt):
    # Define the Singapore timezone
    singapore_tz = pytz.timezone('Asia/Singapore')

    # Convert the datetime object to Singapore time
    dt_singapore = dt.astimezone(singapore_tz)

    # Format the datetime object as a string
    dt_string = dt_singapore.strftime("%Y-%m-%dT%H:%M:%S")

    return dt_string


def delete_records_with_update_time_before_from_all_tables(conn, dt):
    dt_string = convert_to_singapore_time(dt)
    deleted_count = 0
    cursor = conn.cursor()
    # Get all tables
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    for table in tables:
        table_name = table[0]
        if not table_name.startswith('history_'):
            continue
        id = table_name.split('_')[1]
        # delete records with update_datetime before dt
        delete = f"DELETE FROM {table_name} WHERE update_datetime < '{dt_string}'"
        try:
            cursor.execute(delete)
            # get the number of rows affected
            conn.commit()
            deleted_count += cursor.rowcount
            print(f"deleted {cursor.rowcount} records from {table_name} before {dt_string}")
        except pymysql.Error as err:
            print(f"Error deleting from table: {table_name}, error: {err}")
            conn.rollback()
            continue
    cursor.close()
    print(f"deleted {deleted_count} records in total")
    return deleted_count


def connect_to_db():
    # use pymysql to connect to db
    try:
        conn = pymysql.connect(user=DB_USER, password=DB_PWD, host=DB_HOST, database=DB_NAME)
        return conn
    except pymysql.Error as e:
        print(f"Error connecting to database: {e}")
        return None


def lambda_handler(event, context):
    conn = connect_to_db()
    if conn is None:
        print("Error connecting to db")
        return
    deleted_count = delete_records_with_update_time_before_from_all_tables(conn, datetime.now() - timedelta(hours=12))
    conn.close()

    return {
        'statusCode': 200,
        'body': f"deleted {deleted_count} records"
    }
