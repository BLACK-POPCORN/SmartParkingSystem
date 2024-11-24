# AWS Backend System for Smart Parking System

This project consists of the following AWS services:

## EC2 Server
The [EC2 server](/EC2/server.py) is used to provide HTTP services to the [InvokeSageMaker](/InvokeSageMaker.py) Lambda function.
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
