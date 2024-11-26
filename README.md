# Smart Parking System

Group Member:

- Wang, Huijia
- Wang, Ke
- Zhang, Tianhao
- Sun, Yuming

Supervisor:

- Prof. Nascimento, Mario
- Prof. Singh, Sarita



## Introduction

Our project consists of three parts.

### Mobile application

   For details of this part, please refer to the [SmartParkingMobile](/SmartParkingMobile) directory.
   
   Use React-native framework as front-end.

### Machine Learning Model
   Our machine learning models predict parking availability using historical data and precipitation data. We employ Long Short-Term Memory (LSTM) neural networks to capture temporal dependencies in the data. 
   For details of this part, please refer to the [ML](/ML) directory.

### AWS Backend 

It consists of these following services: 
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
For the sake of demonstration, only a few files are included in the [ParkingAvailability](/Data/ParkingAvailability) directory to avoid excessive usage of repo storage .

### Precipitation Data
The full precipitation data is available in the [Precipitation](/Data/Precipitation) folder.
