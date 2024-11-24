import requests
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


def get_history_data_at_time(t: datetime, timeout=10):
    dt_string = convert_to_singapore_time(t)
    url = f"https://api.data.gov.sg/v1/transport/carpark-availability?date_time={dt_string}"
    payload = {}
    headers = {}
    print(f"request history for {dt_string}...")

    try:
        response = requests.request("GET", url, headers=headers, data=payload, timeout=timeout)
        print(f"response received for {dt_string}, elapsed time: {response.elapsed}")

        if response.status_code == 200:
            data = response.json()
            # 2023-09-23T15:59:27+08:00
            # req_time = data['items'][0]['timestamp']
            req_time = dt_string
            l = len(data['items'])
            parking_lots = data['items'][0]['carpark_data'] if l > 0 else []

            all = []

            for lot in parking_lots:
                carpark_number = lot['carpark_number']
                carpark_info = lot['carpark_info']
                # 2023-09-23T15:59:21
                update_datetime = lot['update_datetime']
                total_lots = -1
                lots_available = 0
                for info in carpark_info:
                    lot_type = info['lot_type']
                    if lot_type == 'C':
                        total_lots = info['total_lots']
                        lots_available = info['lots_available']
                        break

                lot_dict = {
                    'id': carpark_number,
                    'lots_available': lots_available,
                    'total_lots': total_lots,
                    'update_datetime': update_datetime,
                    'req_time': req_time
                }
                all.append(lot_dict)
            print(f"got {len(all)} rows of history for {dt_string}...")
            return all
        else:
            print(f"Error: {response.status_code}")
            return []
    except requests.Timeout:
        print("The request timed out")
        return []
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return []


def connect_to_db():
    # use pymysql to connect to db
    try:
        conn = pymysql.connect(user=DB_USER, password=DB_PWD, host=DB_HOST, database=DB_NAME)
        return conn
    except pymysql.Error as e:
        print(f"Error connecting to database: {e}")
        return None


def insert_all_records(conn, all):
    # insert into db
    cursor = conn.cursor()
    # iterate every row and insert into db
    count = 0
    for lot in all:

        id = lot['id']
        lots_available = lot['lots_available']
        total_lots = lot['total_lots']
        update_datetime = lot['update_datetime']
        req_time = lot['req_time']

        # if update_datetime is one day ahead of req_time, then continue
        if datetime.strptime(req_time, "%Y-%m-%dT%H:%M:%S") - datetime.strptime(update_datetime,
                                                                                "%Y-%m-%dT%H:%M:%S") > timedelta(
                days=1):
            continue

        add_availability = (f"INSERT INTO history_{id}"
                            "(lots_available, total_lots, update_datetime, req_time) "
                            "VALUES (%s, %s, %s, %s)")
        # print(f"inserting into history_{id}...")
        data_availability = (lots_available, total_lots, update_datetime, req_time)
        try:
            cursor.execute(add_availability, data_availability)
            conn.commit()
            count += 1
        except pymysql.Error as err:
            print(f"Error inserting into table: history_{id}, error: {err}")
            conn.rollback()
            continue
    print(f"inserted {count} records")
    return count


def delete_records_with_update_time_before_from_all_tables(conn, dt):
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
        delete = f"DELETE FROM {table_name} WHERE update_datetime < '{dt}'"
        try:
            cursor.execute(delete)
            # get the number of rows affected
            conn.commit()
            deleted_count += cursor.rowcount
            print(f"deleted {cursor.rowcount} records from {table_name} before {dt}")
        except pymysql.Error as err:
            print(f"Error deleting from table: {table_name}, error: {err}")
            conn.rollback()
            continue
    cursor.close()


def lambda_handler(event, context):
    conn = connect_to_db()
    if conn is None:
        print("Error connecting to db")
        return

    req_time = datetime.now()
    # minus the req_time by 5 seconds
    req_time = req_time - timedelta(seconds=5)

    all = get_history_data_at_time(req_time)
    inserted = insert_all_records(conn, all)
    conn.close()

    if len(all) > 0:
        return {
            'statusCode': 200,
            'body': f"inserted {inserted} records"
        }
    else:
        return {
            'statusCode': 404,
            'body': 'found no records from API, most likely due to timeout'
        }
