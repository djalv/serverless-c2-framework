import json
import datetime
import os
import boto3
import logging


logger = logging.getLogger()
logger.setLevel(logging.INFO)

RESULTS_BUCKET_NAME = os.environ.get("RESULTS_BUCKET_NAME")
S3_CLIENT = boto3.client("s3")


def lambda_handler(event, context):
    try:
        req_body = event.get("body")
        if not req_body:
            logger.warning("ERROR: Request body is empty or missing.")

            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "body is empty or missing."}),
            }
        agent_data = json.loads(req_body)

        agent_id = agent_data.get("agentId")
        if not agent_id:
            logger.warning("ERROR: Agent ID is empty or missing.")

            return {
                "statusCode": 400,  # Bad Request
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "agentId is required."}),
            }

        if "taskResult" not in agent_data:
            logger.warning("ERROR: Task Result is empty or missing.")

            return {
                "statusCode": 400,  # Bad Request
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "taskResult is required."}),
            }
        task_result = agent_data["taskResult"]

        timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
        s3_key = f"{agent_id}/{timestamp}.txt"

        S3_CLIENT.put_object(Bucket=RESULTS_BUCKET_NAME, Key=s3_key, Body=task_result)

        response_body = {"message": "Result stored successfully", "s3_key": s3_key}

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(response_body),
        }

    except Exception as e:
        logger.error(f"An unhandled exception occurred: {e}", exc_info=True)

        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "An internal server error occurred"}),
        }
