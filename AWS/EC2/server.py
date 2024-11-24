from datetime import datetime
from datetime import timedelta
import pymysql
import pytz
import pandas as pd
from fastapi import FastAPI
import uvicorn
from fastapi import HTTPException
import logging
import uuid
import os
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

# Configure the logging
logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filemode='a'
)

# read these from environment variables
DB_PWD = os.environ.get("DB_PWD")
DB_HOST = os.environ.get("DB_HOST")
DB_USER = os.environ.get("DB_USER")
DB_NAME = os.environ.get("DB_NAME")
SERVER_PORT = os.environ.get("SERVER_PORT")


def connect_to_db():
    # use pymysql to connect to db
    try:
        conn = pymysql.connect(user=DB_USER, password=DB_PWD, host=DB_HOST, database=DB_NAME)
        return conn
    except pymysql.Error as e:
        logging.error(f"Error connecting to database: {e}")
        return None


def convert_to_singapore_time_object(dt):
    # Define the Singapore timezone
    singapore_tz = pytz.timezone('Asia/Singapore')

    # Convert the datetime object to Singapore time
    dt_singapore = dt.astimezone(singapore_tz)

    # Format the datetime object as a string
    # dt_string = dt_singapore.strftime("%Y-%m-%dT%H:%M:%S")

    return dt_singapore


def query_records_by_time(invocation_id, conn, parking_lot_id, req_time, count, interval_mins=15):
    # query the most recent count records according to req_time
    start_time = req_time - timedelta(minutes=interval_mins * count)
    # convert start_time object to string
    start_time_str = start_time.strftime("%Y-%m-%d %H:%M:%S")
    req_time_str = req_time.strftime("%Y-%m-%d %H:%M:%S")
    query = f"SELECT * FROM history_{parking_lot_id} WHERE update_datetime BETWEEN '{start_time_str}' AND '{req_time_str}'"
    logging.info(f"{invocation_id} query_records_by_time query SQL:{query}")
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        records = cursor.fetchall()
        if len(records) == 0:
            logging.error(f"{invocation_id} records is 0")
            raise HTTPException(status_code=404,
                                detail=f"No records found for {parking_lot_id} between {start_time_str} and {req_time_str}")

        df = pd.DataFrame(records)
        # set the column names
        df.columns = ['lots_available', 'total_lots', 'update_datetime', 'req_time']
        # df = df['update_datetime']
        df = df[['update_datetime', 'lots_available']]
        df = df.set_index('update_datetime')
        df = df.resample(f'{interval_mins}min').nearest().interpolate()
        # convert df['lots_available'] to a list
        records = df['lots_available'].tolist()

        if len(records) < count:
            makeup = records[0]
            # append numbers to the front of the list to make the length equal to `count`
            records = [makeup] * (count - len(records)) + records
        # print(records)
        instances = [[r] for r in records]
        cursor.close()
        logging.info(f"{invocation_id} query_records_by_time end")
        return {"instances": [instances]}
    except Exception as e:
        logging.error(f"{invocation_id} query_records_by_time exception:{e}")
        raise HTTPException(status_code=404, detail=f"Error: {e}")


def get_connection(connection):
    res = connection
    try:
        # Ping the server to keep the connection alive
        connection.ping(reconnect=True)
    except pymysql.MySQLError:
        # Reconnect if the connection was lost
        res = connect_to_db()
    return res


class QueryRequest(BaseModel):
    count: int
    parking_lot_id: str


app = FastAPI()


conn = connect_to_db()
if conn is None:
    print("Error connecting to db")
    exit(1)


@app.get("/")
def read_root():
    return ['A10', 'A100', 'A11', 'A12', 'A13', 'A15', 'A2', 'A20', 'A21', 'A24', 'A25', 'A26', 'A27', 'A28', 'A29',
            'A30', 'A31', 'A33', 'A34', 'A35', 'A36', 'A37', 'A38', 'A39', 'A4', 'A40', 'A41', 'A42', 'A43', 'A44',
            'A45', 'A47', 'A48', 'A49', 'A50', 'A51', 'A52', 'A53', 'A54', 'A55', 'A59', 'A60', 'A61', 'A63', 'A64',
            'A65', 'A66', 'A67', 'A68', 'A69', 'A7', 'A70', 'A71', 'A72', 'A73', 'A74', 'A75', 'A76', 'A77', 'A78',
            'A8', 'A81', 'A82', 'A85', 'A87', 'A88', 'A9', 'A94', 'A98', 'ACB', 'ACM', 'AH1', 'AM14', 'AM16', 'AM18',
            'AM19', 'AM20', 'AM22', 'AM32', 'AM43', 'AM46', 'AM51', 'AM64', 'AM79', 'AM80', 'AM81', 'AM96', 'AR1L',
            'AR1M', 'AR2L', 'AR2M', 'AR5M', 'AR7L', 'AR7M', 'AR9', 'AV1', 'B10', 'B10M', 'B11', 'B14', 'B16', 'B17',
            'B19', 'B20', 'B21', 'B23L', 'B23M', 'B24', 'B25', 'B26', 'B27', 'B28', 'B30', 'B31', 'B32', 'B33', 'B34',
            'B35', 'B40', 'B41', 'B42', 'B43', 'B44', 'B44B', 'B45', 'B46', 'B47', 'B48', 'B48B', 'B49', 'B50', 'B51',
            'B52', 'B53', 'B54', 'B57', 'B59', 'B6', 'B60', 'B63', 'B65', 'B65L', 'B65M', 'B66', 'B67', 'B69', 'B7',
            'B70', 'B71', 'B72', 'B73', 'B74', 'B75', 'B79', 'B7A', 'B7B', 'B8', 'B80', 'B81', 'B83', 'B84', 'B85',
            'B86', 'B88', 'B89', 'B8B', 'B9', 'B90', 'B91', 'B92', 'B94', 'B94A', 'B95', 'B96', 'B97', 'B98', 'B99M',
            'BA1', 'BA2', 'BA3', 'BA4', 'BA6', 'BA7', 'BA8', 'BA9', 'BBB', 'BBM1', 'BBM2', 'BBM3', 'BBM5', 'BBM7',
            'BBM8', 'BBM9', 'BE10', 'BE11', 'BE12', 'BE13', 'BE14', 'BE18', 'BE19', 'BE22', 'BE23', 'BE25', 'BE26',
            'BE27', 'BE28', 'BE29', 'BE3', 'BE30', 'BE31', 'BE32', 'BE33', 'BE34', 'BE35', 'BE36', 'BE37', 'BE38',
            'BE39', 'BE3R', 'BE4', 'BE40', 'BE42', 'BE44', 'BE45', 'BE5', 'BE6', 'BE7', 'BE8', 'BE9', 'BH1', 'BH2',
            'BJ1', 'BJ10', 'BJ11', 'BJ12', 'BJ13', 'BJ14', 'BJ15', 'BJ16', 'BJ17', 'BJ18', 'BJ19', 'BJ2', 'BJ20',
            'BJ21', 'BJ23', 'BJ24', 'BJ25', 'BJ26', 'BJ27', 'BJ28', 'BJ29', 'BJ3', 'BJ30', 'BJ31', 'BJ32', 'BJ33',
            'BJ34', 'BJ35', 'BJ36', 'BJ37', 'BJ38', 'BJ39', 'BJ4', 'BJ40', 'BJ41', 'BJ42', 'BJ43', 'BJ44', 'BJ45',
            'BJ48', 'BJ49', 'BJ50', 'BJ51', 'BJ52', 'BJ53', 'BJ54', 'BJ55', 'BJ56', 'BJ57', 'BJ58', 'BJ60', 'BJ61',
            'BJ62', 'BJ63', 'BJ65', 'BJ66', 'BJ67', 'BJ68', 'BJ69', 'BJ71', 'BJ72', 'BJ8', 'BJAL', 'BJBL', 'BJMP',
            'BKE1', 'BKE2', 'BKE3', 'BKE4', 'BKE7', 'BKE9', 'BKRM', 'BL10', 'BL13', 'BL15', 'BL17', 'BL18', 'BL19',
            'BL22', 'BL23', 'BL3', 'BL8', 'BL8L', 'BLM', 'BM1', 'BM10', 'BM13', 'BM14', 'BM19', 'BM2', 'BM20', 'BM26',
            'BM28', 'BM29', 'BM3', 'BM30', 'BM31', 'BM4', 'BM5', 'BM6', 'BM9', 'BMVM', 'BP1', 'BP2', 'BR10', 'BR11',
            'BR12', 'BR14', 'BR4', 'BR5', 'BR6', 'BR8', 'BR9', 'BRB1', 'BRBL', 'BRM', 'BRM1', 'BRM3', 'BRM4', 'BRM5',
            'BRM6', 'BRM7', 'BTM', 'BTM2', 'BTM3', 'BVM2', 'BWM', 'C10', 'C11', 'C12', 'C13M', 'C14M', 'C15M', 'C16',
            'C17', 'C18', 'C18A', 'C19M', 'C20', 'C20M', 'C21L', 'C21M', 'C22M', 'C24', 'C25', 'C26', 'C27', 'C28M',
            'C29', 'C29A', 'C2M', 'C30', 'C31', 'C32', 'C33', 'C34', 'C35', 'C36', 'C37', 'C38', 'C3M', 'C3ML', 'C40L',
            'C40M', 'C4M', 'C5', 'C6', 'C7', 'C8', 'C9', 'CAM', 'CC1', 'CC10', 'CC11', 'CC12', 'CC4', 'CC5', 'CC6',
            'CC7', 'CC8', 'CC9', 'CCKC', 'CDM', 'CK1', 'CK10', 'CK11', 'CK12', 'CK13', 'CK14', 'CK15', 'CK16', 'CK17',
            'CK18', 'CK19', 'CK2', 'CK20', 'CK22', 'CK23', 'CK24', 'CK25', 'CK28', 'CK29', 'CK3', 'CK30', 'CK31',
            'CK32', 'CK33', 'CK34', 'CK35', 'CK36', 'CK37', 'CK38', 'CK39', 'CK3A', 'CK4', 'CK40', 'CK41', 'CK42',
            'CK44', 'CK45', 'CK46', 'CK47', 'CK48', 'CK49', 'CK50', 'CK51', 'CK52', 'CK53', 'CK54', 'CK55', 'CK56',
            'CK57', 'CK58', 'CK59', 'CK6', 'CK60', 'CK61', 'CK62', 'CK63', 'CK64', 'CK65', 'CK66', 'CK6A', 'CK7',
            'CK70', 'CK71', 'CK72', 'CK73', 'CK74', 'CK75', 'CK76', 'CK77', 'CK78', 'CK79', 'CK8', 'CK8A', 'CK9',
            'CK9A', 'CKM1', 'CKM2', 'CKM3', 'CKM4', 'CKM5', 'CKM6', 'CKM7', 'CKM8', 'CKM9', 'CKT1', 'CKT2', 'CLM',
            'CLNA', 'CLRG', 'CLTR', 'CM1', 'CR1', 'CR1A', 'CR1B', 'CR2', 'CR29', 'CR3', 'CR30', 'CR31', 'CR6', 'CR7',
            'CSM', 'CTM1', 'CV1', 'CV2', 'CV3', 'CVBK', 'CY', 'DRM1', 'DRM2', 'DRM3', 'DRM4', 'DRM5', 'DRS', 'DSR1',
            'DSR2', 'DSRL', 'DUXM', 'DWSO', 'DWSP', 'DWST', 'DWSV', 'DWVT', 'EC2', 'EC3', 'EC4', 'EC7', 'EC8', 'ECM',
            'ECM2', 'ECML', 'EI3', 'EPL', 'EPM', 'FR2C', 'FR3M', 'FR4M', 'FRM', 'GBM', 'GE1A', 'GE1B', 'GE1C', 'GE1F',
            'GE1G', 'GE2', 'GE3', 'GE5', 'GEM', 'GEML', 'GM1A', 'GM1M', 'GM2', 'GM2A', 'GM3', 'GM5', 'GM6A', 'GM6B',
            'GMLM', 'GSM', 'GSML', 'H12', 'H14', 'H17', 'H18', 'H3', 'H3BL', 'H3DL', 'H4', 'H6', 'H8', 'H87L', 'H93L',
            'HCM', 'HE1', 'HE12', 'HE17', 'HE19', 'HE24', 'HE3', 'HE4', 'HE9', 'HG1', 'HG10', 'HG11', 'HG12', 'HG13',
            'HG14', 'HG15', 'HG16', 'HG17', 'HG18', 'HG19', 'HG1A', 'HG1B', 'HG1C', 'HG1D', 'HG1E', 'HG1F', 'HG2',
            'HG20', 'HG22', 'HG23', 'HG24', 'HG29', 'HG2A', 'HG2B', 'HG2C', 'HG2D', 'HG30', 'HG31', 'HG32', 'HG33',
            'HG34', 'HG35', 'HG36', 'HG37', 'HG38', 'HG39', 'HG3B', 'HG3D', 'HG3E', 'HG3L', 'HG4', 'HG41', 'HG42',
            'HG43', 'HG44', 'HG45', 'HG46', 'HG47', 'HG48', 'HG49', 'HG5', 'HG50', 'HG51', 'HG52', 'HG53', 'HG54',
            'HG55', 'HG56', 'HG60', 'HG61', 'HG62', 'HG64', 'HG67', 'HG68', 'HG69', 'HG7', 'HG70', 'HG71', 'HG73',
            'HG74', 'HG75', 'HG76', 'HG77', 'HG78', 'HG79', 'HG80', 'HG86', 'HG87', 'HG88', 'HG89', 'HG9', 'HG90',
            'HG91', 'HG92', 'HG93', 'HG94', 'HG95', 'HG96', 'HG97', 'HG98', 'HG99', 'HG9T', 'HLM', 'HR1', 'HR2', 'HR3',
            'HR4', 'HR5', 'HRM', 'HVM', 'J1', 'J10', 'J11', 'J12', 'J14', 'J15', 'J16', 'J17', 'J18', 'J19', 'J2',
            'J20', 'J21', 'J22', 'J23', 'J23M', 'J24', 'J25', 'J26', 'J27', 'J29', 'J3', 'J32', 'J33', 'J34', 'J35',
            'J36', 'J37', 'J38', 'J39', 'J4', 'J40', 'J41', 'J43', 'J44', 'J45', 'J46', 'J47', 'J48', 'J49', 'J49M',
            'J5', 'J50', 'J51', 'J52', 'J53', 'J54', 'J55', 'J56', 'J57', 'J57L', 'J6', 'J60L', 'J60M', 'J61', 'J62',
            'J62M', 'J63', 'J64', 'J65', 'J66', 'J67', 'J68M', 'J69', 'J7', 'J70', 'J71', 'J72', 'J73', 'J74', 'J74M',
            'J75M', 'J76M', 'J77M', 'J78M', 'J79M', 'J8', 'J80M', 'J81M', 'J82M', 'J83M', 'J84M', 'J85M', 'J86M',
            'J88M', 'J89M', 'J8M', 'J9', 'J90', 'J91', 'J92', 'J93', 'J94', 'J95', 'J96', 'J97', 'J98M', 'J99M', 'JB1',
            'JB2', 'JB3', 'JB4', 'JBM', 'JBM2', 'JCM', 'JCML', 'JKM', 'JKS', 'JM1', 'JM10', 'JM11', 'JM12', 'JM13',
            'JM14', 'JM15', 'JM16', 'JM17', 'JM18', 'JM19', 'JM2', 'JM20', 'JM21', 'JM22', 'JM23', 'JM24', 'JM25',
            'JM26', 'JM27', 'JM28', 'JM29', 'JM3', 'JM30', 'JM31', 'JM32', 'JM33', 'JM4', 'JM5', 'JM6', 'JM7', 'JM8',
            'JM9', 'JMB1', 'JMB2', 'JMB3', 'JRM', 'JRTM', 'JS1L', 'JS33', 'JS3L', 'JS4L', 'JS5L', 'JSA1', 'JSR2', 'K10',
            'K19', 'K2', 'K2T', 'K52', 'K7', 'KAM', 'KAML', 'KAS', 'KB1', 'KB10', 'KB11', 'KB12', 'KB14', 'KB17',
            'KB18', 'KB20', 'KB3', 'KB4', 'KB7', 'KBM', 'KBRM', 'KE1', 'KE2', 'KE3', 'KE3M', 'KE4', 'KEM1', 'KJ1',
            'KJ2', 'KJ3', 'KJ4', 'KJM1', 'KJM2', 'KJML', 'KLM', 'KM1', 'KM2', 'KM3', 'KM4', 'KM5', 'KM6', 'KM6L', 'KRM',
            'KTM', 'KTM2', 'KTM3', 'KTM4', 'KTM5', 'KTM6', 'KU1', 'KU2', 'KU3', 'KU4', 'KU9', 'KUM1', 'KUM2', 'L1',
            'LBM', 'LT1', 'LT2', 'LT3', 'M1', 'M16', 'M20', 'M25', 'M3', 'M32', 'M33', 'M35', 'M36', 'M37', 'M38', 'M4',
            'MLM', 'MLM1', 'MM1', 'MM2', 'MM3', 'MM4', 'MM6', 'MM7', 'MM7L', 'MN1', 'MN2', 'MNM', 'MNRM', 'MP1', 'MP12',
            'MP13', 'MP14', 'MP15', 'MP16', 'MP17', 'MP19', 'MP1M', 'MP2', 'MP2M', 'MP3M', 'MP4M', 'MP5', 'MP5M',
            'MP5S', 'MP6', 'MP7', 'MR4', 'MR5', 'MR6', 'MR7', 'N12L', 'NBRM', 'NT1', 'NT12', 'NT2', 'NT3', 'NT4', 'NT5',
            'NT6', 'NT6L', 'NT7', 'NT7L', 'NT8', 'NT9', 'NTL', 'P1', 'P11', 'P12', 'P13', 'P14', 'P15', 'P16', 'P17',
            'P2', 'P3', 'P34L', 'P35L', 'P4', 'P40L', 'P5', 'P5L', 'P6', 'P6L', 'P7', 'P71L', 'P73L', 'P8', 'P88L',
            'P9', 'PD8W', 'PDC4', 'PDC5', 'PDJ3', 'PDJ7', 'PDL2', 'PDP4', 'PDP5', 'PDQ5', 'PDR2', 'PDR6', 'PDR7',
            'PDS1', 'PDT8', 'PDW5', 'PDW7', 'PDW8', 'PL10', 'PL11', 'PL12', 'PL13', 'PL14', 'PL15', 'PL16', 'PL17',
            'PL18', 'PL19', 'PL20', 'PL21', 'PL22', 'PL23', 'PL24', 'PL25', 'PL26', 'PL27', 'PL28', 'PL29', 'PL30',
            'PL31', 'PL32', 'PL33', 'PL34', 'PL35', 'PL36', 'PL37', 'PL38', 'PL39', 'PL40', 'PL41', 'PL42', 'PL43',
            'PL44', 'PL45', 'PL46', 'PL47', 'PL48', 'PL49', 'PL50', 'PL51', 'PL52', 'PL53', 'PL54', 'PL55', 'PL56',
            'PL57', 'PL58', 'PL59', 'PL60', 'PL61', 'PL62', 'PL65', 'PL66', 'PL67', 'PL68', 'PL69', 'PL70', 'PL71',
            'PL75', 'PL77', 'PL78', 'PL79', 'PL84', 'PL85', 'PL86', 'PL87', 'PL88', 'PM10', 'PM11', 'PM12', 'PM13',
            'PM14', 'PM15', 'PM16', 'PM17', 'PM18', 'PM19', 'PM2', 'PM20', 'PM21', 'PM22', 'PM23', 'PM24', 'PM25',
            'PM26', 'PM27', 'PM28', 'PM29', 'PM3', 'PM30', 'PM32', 'PM33', 'PM34', 'PM35', 'PM36', 'PM37', 'PM38',
            'PM4', 'PM40', 'PM41', 'PM43', 'PM44', 'PM45', 'PM46', 'PM5', 'PM6', 'PM7', 'PM8', 'PM9', 'PP1', 'PP2',
            'PP3', 'PP4', 'PP5', 'PP6', 'PP9T', 'PR1', 'PR10', 'PR12', 'PR13', 'PR14', 'PR2', 'PR3', 'PR4', 'PR6',
            'PR7', 'PR8', 'PRM', 'PRS1', 'Q16', 'Q17', 'Q19', 'Q41', 'Q65', 'Q66', 'Q67', 'Q68', 'Q70', 'Q73', 'Q75M',
            'Q77M', 'Q8', 'Q80', 'Q81', 'Q84', 'Q85', 'Q86', 'Q87', 'Q88', 'Q89', 'Q94', 'Q96', 'RC1', 'RC2', 'RC3',
            'RCM', 'RHM', 'RHM2', 'RHM3', 'RHM4', 'RHS', 'S100', 'S102', 'S103', 'S104', 'S105', 'S106', 'S107', 'S108',
            'S109', 'S110', 'S111', 'S113', 'S114', 'S115', 'S116', 'S117', 'S118', 'S119', 'S120', 'S13L', 'S14L',
            'S16L', 'S19L', 'S24L', 'S28L', 'S30L', 'S36L', 'S38L', 'S39L', 'S40L', 'SAM', 'SAM2', 'SB1', 'SB10',
            'SB11', 'SB12', 'SB13', 'SB15', 'SB16', 'SB17', 'SB18', 'SB19', 'SB2', 'SB20', 'SB21', 'SB22', 'SB23',
            'SB24', 'SB25', 'SB26', 'SB27', 'SB28', 'SB29', 'SB3', 'SB30', 'SB31', 'SB32', 'SB33', 'SB34', 'SB35',
            'SB36', 'SB37', 'SB38', 'SB39', 'SB4', 'SB40', 'SB41', 'SB42', 'SB43', 'SB44', 'SB45', 'SB46', 'SB47',
            'SB5', 'SB6', 'SB7', 'SB8', 'SB9', 'SD1', 'SD11', 'SD2', 'SD3', 'SD4', 'SD5', 'SD9', 'SDM', 'SDM2', 'SE11',
            'SE12', 'SE13', 'SE14', 'SE15', 'SE16', 'SE17', 'SE18', 'SE19', 'SE20', 'SE21', 'SE22', 'SE23', 'SE24',
            'SE25', 'SE26', 'SE27', 'SE28', 'SE29', 'SE31', 'SE32', 'SE33', 'SE34', 'SE35', 'SE37', 'SE38', 'SE39',
            'SE40', 'SE41', 'SE42', 'SE43', 'SE50', 'SE51', 'SE52', 'SE53', 'SE5L', 'SE9', 'SG1', 'SG2', 'SG3', 'SG4',
            'SGLM', 'SGTM', 'SH1', 'SH2', 'SI1', 'SI10', 'SI11', 'SI12', 'SI13', 'SI2', 'SI4', 'SI6', 'SI7', 'SI8',
            'SI9', 'SIM', 'SIM1', 'SIM2', 'SIM3', 'SIM4', 'SIM5', 'SIM6', 'SK1', 'SK10', 'SK11', 'SK12', 'SK13', 'SK14',
            'SK15', 'SK16', 'SK17', 'SK18', 'SK19', 'SK2', 'SK20', 'SK21', 'SK22', 'SK23', 'SK24', 'SK25', 'SK26',
            'SK27', 'SK28', 'SK29', 'SK3', 'SK30', 'SK31', 'SK32', 'SK33', 'SK34', 'SK35', 'SK36', 'SK37', 'SK38',
            'SK39', 'SK4', 'SK40', 'SK41', 'SK42', 'SK43', 'SK44', 'SK45', 'SK46', 'SK47', 'SK48', 'SK49', 'SK5',
            'SK50', 'SK51', 'SK52', 'SK53', 'SK54', 'SK55', 'SK58', 'SK59', 'SK6', 'SK60', 'SK61', 'SK62', 'SK63',
            'SK64', 'SK65', 'SK66', 'SK67', 'SK68', 'SK69', 'SK7', 'SK70', 'SK71', 'SK72', 'SK73', 'SK74', 'SK75',
            'SK76', 'SK77', 'SK78', 'SK79', 'SK8', 'SK80', 'SK81', 'SK82', 'SK83', 'SK84', 'SK85', 'SK86', 'SK87',
            'SK88', 'SK89', 'SK9', 'SK90', 'SK91', 'SK92', 'SK93', 'SK94', 'SK95', 'SK96', 'SK97', 'SK98', 'SK99',
            'SLS', 'SM1', 'SM3', 'SM9', 'SMM', 'SPM', 'SPS', 'SS1L', 'STAM', 'STM1', 'STM2', 'STM3', 'T1', 'T11', 'T12',
            'T13', 'T15', 'T16', 'T17', 'T18', 'T19', 'T20', 'T24', 'T25', 'T26', 'T27', 'T28', 'T29', 'T3', 'T30',
            'T31', 'T32', 'T34', 'T35', 'T37', 'T38', 'T39', 'T4', 'T41', 'T42', 'T43', 'T44', 'T45', 'T46', 'T47',
            'T47A', 'T47L', 'T48', 'T49', 'T49A', 'T50', 'T51', 'T55', 'T57', 'T58', 'T7', 'T72', 'T73', 'T74', 'T75',
            'T76', 'T77', 'T78', 'T79', 'T7A', 'T8', 'T80', 'T81', 'T9', 'TAM1', 'TAM2', 'TB1', 'TB10', 'TB11', 'TB14',
            'TB17', 'TB18', 'TB19', 'TB2', 'TB22', 'TB23', 'TB28', 'TB3', 'TB4A', 'TB6', 'TB7', 'TB8', 'TB9', 'TBC2',
            'TBC3', 'TBCM', 'TBL', 'TBM', 'TBM2', 'TBM3', 'TBM4', 'TBM5', 'TBM6', 'TBM7', 'TBM8', 'TBMT', 'TE1', 'TE13',
            'TE14', 'TE2', 'TE25', 'TE3', 'TE4', 'TE9', 'TG1', 'TG2', 'TG3', 'TG6', 'TG7', 'TGM1', 'TGM2', 'TGM3',
            'TGM4', 'TGML', 'TH1', 'TH1L', 'TJ27', 'TJ28', 'TJ29', 'TJ30', 'TJ31', 'TJ32', 'TJ33', 'TJ34', 'TJ35',
            'TJ36', 'TJ37', 'TJ38', 'TJ39', 'TJ41', 'TJ42', 'TM10', 'TM11', 'TM12', 'TM13', 'TM14', 'TM15', 'TM16',
            'TM17', 'TM18', 'TM19', 'TM1A', 'TM20', 'TM21', 'TM22', 'TM23', 'TM24', 'TM25', 'TM26', 'TM27', 'TM28',
            'TM29', 'TM3', 'TM30', 'TM31', 'TM32', 'TM33', 'TM34', 'TM35', 'TM36', 'TM37', 'TM4', 'TM41', 'TM42',
            'TM43', 'TM44', 'TM45', 'TM46', 'TM47', 'TM48', 'TM49', 'TM5', 'TM50', 'TM51', 'TM52', 'TM53', 'TM54',
            'TM55', 'TM56', 'TM6', 'TM7', 'TM8', 'TM9', 'TP10', 'TP12', 'TP14', 'TP15', 'TP16', 'TP17', 'TP18', 'TP2',
            'TP20', 'TP22', 'TP27', 'TP3', 'TP30', 'TP31', 'TP34', 'TP36', 'TP3A', 'TP40', 'TP41', 'TP43', 'TP48',
            'TP49', 'TP4A', 'TP50', 'TP52', 'TP53', 'TP54', 'TP60', 'TP62', 'TP63', 'TP67', 'TP68', 'TP7', 'TP8',
            'TPB1', 'TPL', 'TPM', 'TPM2', 'TPM3', 'TPM4', 'TPM5', 'TPM6', 'TPM7', 'TPM8', 'TPM9', 'TPMA', 'TPMB',
            'TPMC', 'TPMD', 'TPME', 'TPMF', 'TPMG', 'TPMH', 'TPMJ', 'TPMK', 'TPML', 'TPMM', 'TPMN', 'TPMP', 'TPMQ',
            'TPMR', 'TPMS', 'TR1', 'TRM', 'TRS', 'TW1', 'TW2', 'TW3', 'TW4', 'TWM1', 'TWM2', 'TWM3', 'TWM4', 'TWM6',
            'U1', 'U10', 'U11', 'U12', 'U13', 'U15', 'U17', 'U18', 'U19', 'U2', 'U21', 'U22', 'U23', 'U24', 'U24T',
            'U25', 'U26', 'U27', 'U28', 'U29', 'U3', 'U30', 'U31', 'U32', 'U33', 'U34', 'U38', 'U39', 'U4', 'U40',
            'U41', 'U43', 'U45', 'U46', 'U48', 'U5', 'U50', 'U51', 'U52', 'U54', 'U55', 'U56', 'U57', 'U58', 'U6',
            'U60', 'U63', 'U64', 'U65', 'U66', 'U67', 'U68', 'U69', 'U7', 'U70', 'U71', 'U8', 'U9', 'UA2', 'UA3', 'UA5',
            'UAM1', 'UBK2', 'UBK4', 'UBK5', 'UBKM', 'UBM1', 'UBM2', 'W10', 'W100', 'W101', 'W102', 'W103', 'W104',
            'W105', 'W106', 'W107', 'W108', 'W109', 'W11', 'W11M', 'W12M', 'W13', 'W14', 'W17', 'W18', 'W181', 'W182',
            'W185', 'W187', 'W19', 'W20', 'W21', 'W23', 'W24', 'W25', 'W26', 'W27', 'W28', 'W3', 'W30', 'W36', 'W37',
            'W39', 'W4', 'W40', 'W41', 'W43', 'W44', 'W45', 'W46', 'W48', 'W49', 'W4M', 'W5', 'W50', 'W505', 'W509',
            'W51', 'W516', 'W517', 'W52', 'W527', 'W53', 'W536', 'W54', 'W546', 'W549', 'W55', 'W554', 'W56', 'W56L',
            'W57', 'W570', 'W574', 'W578', 'W579', 'W58', 'W586', 'W588', 'W59', 'W5M', 'W6', 'W61', 'W64', 'W65',
            'W66', 'W67', 'W676', 'W68', 'W69', 'W691', 'W693', 'W694', 'W7', 'W70', 'W71', 'W717', 'W72', 'W73', 'W74',
            'W75', 'W76', 'W77', 'W78', 'W780', 'W782', 'W783', 'W785', 'W79', 'W799', 'W80', 'W81', 'W82', 'W83',
            'W84', 'W85', 'W86', 'W87', 'W88', 'W887', 'W889', 'W89', 'W8M', 'W90', 'W91', 'W92', 'W93', 'W94', 'W95',
            'W96', 'W98', 'WCB', 'WCC', 'WDB1', 'WGL', 'Y1', 'Y10', 'Y11', 'Y12', 'Y13', 'Y14', 'Y15', 'Y16', 'Y17',
            'Y18', 'Y19', 'Y2', 'Y20', 'Y21', 'Y21M', 'Y23', 'Y24', 'Y25', 'Y25M', 'Y26', 'Y27', 'Y28', 'Y28M', 'Y29',
            'Y3', 'Y30M', 'Y31', 'Y32', 'Y33', 'Y34', 'Y34A', 'Y35', 'Y36', 'Y38', 'Y39', 'Y3M', 'Y4', 'Y40', 'Y41',
            'Y41M', 'Y43', 'Y45', 'Y45M', 'Y46', 'Y48', 'Y48M', 'Y49', 'Y49H', 'Y49L', 'Y49M', 'Y4T', 'Y5', 'Y51',
            'Y51M', 'Y52M', 'Y53M', 'Y54M', 'Y56', 'Y57', 'Y58', 'Y59M', 'Y6', 'Y60M', 'Y61M', 'Y62M', 'Y63M', 'Y64M',
            'Y65M', 'Y66M', 'Y68L', 'Y68M', 'Y69L', 'Y69M', 'Y7', 'Y70M', 'Y71M', 'Y73M', 'Y74M', 'Y75M', 'Y76M',
            'Y77L', 'Y77M', 'Y78M', 'Y79L', 'Y79M', 'Y8', 'Y80M', 'Y81M', 'Y82M', 'Y83L', 'Y83M', 'Y9', 'YHS']


@app.post("/parkinglot")
def query_parking_his(request: QueryRequest):
    invocation_id = str(uuid.uuid4())
    c = connect_to_db()
    if c is None:
        logging.error(f"Error connecting to database")
        return None

    count = request.count
    parking_lot_id = request.parking_lot_id
    req_time = datetime.now()
    res = query_records_by_time(invocation_id, c, parking_lot_id, convert_to_singapore_time_object(req_time), count)
    print(res)
    # conn.close()
    c.close()
    return res


if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=int(SERVER_PORT))
