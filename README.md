# Smart Parking System

## Introduction
Our project consists of three parts.
1. A mobile application

   For details of this part, please refer to the [SmartParkingMobile](/SmartParkingMobile) directory.
2. Machine Learning Model

   For details of this part, please refer to the [ML](/ML) directory.
3. An AWS Backend, which consists of these following services:
    - AWS Lambda (three Lambdas)
    - AWS API Gateway
    - AWS RDS MySQL
    - AWS S3
    - AWS EventBridge Rules
    - AWS EC2
    - AWS SageMaker (Model and Endpoint)
     
      For details of this part, please refer to the [AWS](/AWS) directory.

## Overall System Architecture
The architecture of the project is as follows:
      ![System Architecture](assets/arch.png "System Architecture")  

## Data used for training the model
### Parking Availability Data
Nearly 2000 files of parking availability data were collected and used for training the model. 
For the sake of demonstration, only a few files are included in the [Data](/Data) directory to avoid excessive usage of repo storage .

### Precipitation Data
The full precipitation data is available in the [Precipitation](/Data/Precipitation) folder.