import json
import datetime
import os
import boto3
import logging


logger = logging.getLogger()
logger.setLevel(logging.INFO)

S3_CLIENT = boto3.client("s3")


def lambda_handler(event, context):
    RESULTS_BUCKET_NAME = os.environ.get("RESULTS_BUCKET_NAME")

    if not RESULTS_BUCKET_NAME:
        logger.error("ERROR: Environment variable RESULTS_BUCKET_NAME is not set.")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Server configuration error"}),
        }

    try:
        req_body = event.get("body")
        if not req_body:
            logger.warning("ERROR: Request body is empty or missing.")

            return {
                "statusCode": 400,  # Bad Request
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

        if "encrypted_data" not in agent_data:
            logger.warning("ERROR: Encrypted Data is empty or missing.")

            return {
                "statusCode": 400,  # Bad Request
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "encrypted_data is required."}),
            }

        encrypted_blob = agent_data["encrypted_data"]

        timestamp = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d_%H-%M-%S")
        s3_key = f"{agent_id}/{timestamp}.txt"
        S3_CLIENT.put_object(Bucket=RESULTS_BUCKET_NAME, Key=s3_key, Body=encrypted_blob)

        response_body = {"message": "Result stored success", "s3_key": s3_key}

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
