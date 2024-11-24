# AWS Backend System for Smart Parking System

This project consists of the following AWS services:

## EC2 Server
The [EC2 server](/AWS/EC2/server.py) is used to provide HTTP services to the [InvokeSageMaker](/InvokeSageMaker.py) Lambda function.
It exposes two interfaces:

### GET /parkinglot
This interface returns the names of all the parking lots data we have in our database. Because we only have the data of some of the public parking lots in Singapore (mainly those managed by HDB), the interface is provided for the mobile client to query and match the parking lots close to the destination of the user.

*Example Query:*
```bash
curl 'http://<The EC2 Server IP>:<Server Port>/' 
```
### POST /parkinglot
This interface queries the parking availability data of a specific parking lot. The client needs to provide the parking lot name in the request body.

*Example Query:*
```bash
curl --location 'http://<The EC2 Server IP>:<Server Port>/parkinglot' \
--header 'Content-Type: application/json' \
--data '{
    "count": 20,
    "parking_lot_id": "A70"
}'
```

## Lambda Functions
The project consists of three Lambda functions:
### Lambda Function For Getting Recent Parking Availability Data
This Lambda function is triggered by an EventBridge rule every 5 minutes. 

The script for this Lambda function is [here](/AWS/Lambda/GetRecent.py).

### Lambda Function For Deleting Obsolete (> 12 hours) Parking Availability Data
This Lambda function is triggered by an EventBridge rule every 5 minutes.

The script for this Lambda function is [here](/AWS/Lambda/DeleteObsolete.py).

### Lambda Function For Invoking SageMaker Endpoint
This Lambda function is triggered by an API Gateway. It queries the parking availability data of a specific parking lot from the RDS MySQL database and sends it to the SageMaker endpoint to get the prediction of the parking availability.

The script for this Lambda function is [here](/AWS/Lambda/InvokeSageMaker.py).

## API Gateway
The API Gateway is used to expose the Lambda function for invoking the SageMaker endpoint to the mobile client.

## RDS MySQL
The RDS MySQL database is used to store the parking availability data. The schema of the database is in [this](/AWS/MySQL_CREATE_SCRIPT.sql) script file.

## S3
The S3 bucket is used to store the trained models. These model files will be used by the SageMaker endpoint to make predictions.

## EventBridge Rules
The EventBridge rules are used to trigger the Lambda functions for getting recent parking availability data and deleting obsolete parking availability data.
