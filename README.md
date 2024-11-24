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

The architecture of the project is as follows:
      ![System Architecture](assets/arch.png "System Architecture")  

## Data used for training the model