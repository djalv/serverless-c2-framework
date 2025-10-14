import json
import datetime
import os
import boto3
import uuid
import logging

from botocore.exceptions import ClientError


logger = logging.getLogger()
logger.setLevel(logging.INFO)

TABLE_NAME = os.environ.get("TABLE_NAME")
DYNAMODB_CLIENTE = boto3.resource("dynamodb")
TABLE = DYNAMODB_CLIENTE.Table(TABLE_NAME)


def lambda_handler(event, context):
    try:
        # 1. Extract and validate request data
        req_body = event.get("body")
        if not req_body:
            print("ERROR: Request body is empty or missing.")

            return {
                "statusCode": 400,  # Bad Request
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "body is empty or missing."}),
            }
        agent_data = json.loads(req_body)
        agent_host = agent_data.get("hostname")

        # 2. Handle agent ID
        if "agentId" in agent_data:
            agent_id = agent_data.get("agentId")
        else:
            agent_id = str(uuid.uuid4())

        task_to_send = "no-task-for-now"
        try:
            response = TABLE.get_item(Key={"agentId": agent_id})
            if "Item" in response and "pendingTask" in response["Item"]:
                task_to_send = response["Item"]["pendingTask"]

        except ClientError as e:
            logger.error(f"Error fetching task from DynamoDB: {e}")

        # 3. Prepare the item for saving to DynamoDB
        actual_time = datetime.datetime.utcnow().isoformat()
        source_ip = (
            event.get("requestContext", {})
            .get("identity", {})
            .get("sourceIp", "unknown")
        )

        saving_item = {
            "agentId": agent_id,
            "lastSeen": actual_time,
            "hostname": agent_host,
            "sourceIp": source_ip,
        }

        # 4. Save the item to DynamoDB
        TABLE.put_item(Item=saving_item)

        # 5. Prepare and return the success response
        response_body = {
            "message": "Check-in successful",
            "agentId": agent_id,
            "task": task_to_send,
        }

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
