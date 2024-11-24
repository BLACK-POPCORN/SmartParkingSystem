import json
import boto3
import requests
import os

# Create a SageMaker runtime client
sagemaker_runtime = boto3.client('sagemaker-runtime')

QUERY_SERVICE_URL = os.environ.get("QUERY_SERVICE_URL")
SAGE_MAKER_ENDPOINT = os.environ.get("SAGE_MAKER_ENDPOINT")


def query_recent_parking_his(count: int, parking_lot_id: str):
    url = f"http://{QUERY_SERVICE_URL}/parkinglot"

    payload = json.dumps({
        "count": count,
        "parking_lot_id": parking_lot_id
    })
    headers = {
        'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    if response.status_code == 200:
        return response.json()
    else:
        return None


def lambda_handler(e, context):
    print("e is:", e)
    if "body" not in e:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Invalid input format'})
        }

    event = json.loads(e["body"])
    print("parsed event is:", event)
    if 'model_name' not in event:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Invalid input format'})
        }

    his = query_recent_parking_his(20, event['model_name'])
    if not his or 'instances' not in his:
        return {
            'statusCode': 404,
            'body': json.dumps({'error': "invalid model name"})
        }
    print("query his is:", his)

    try:
        # Invoke the SageMaker endpoint
        print("before invoking sageMaker:")
        response = sagemaker_runtime.invoke_endpoint(
            EndpointName=SAGE_MAKER_ENDPOINT,  # Replace with your SageMaker endpoint name
            ContentType='application/json',
            Body=json.dumps({'instances': his['instances']}),
            TargetModel=f"{event['model_name']}.tar.gz"
        )
        print("sagemaker resp is:", response)

        # # Parse the response from SageMaker
        result = json.loads(response['Body'].read().decode())
        # print(type(result))
        print("result is :", result)

        # # Return the result as JSON
        return {
            'statusCode': 200,
            # 'body': result
            'body': json.dumps(result)
        }
    except Exception as e:
        return {
            'statusCode': 404,
            'body': json.dumps({'error': f"{e}"})
        }
