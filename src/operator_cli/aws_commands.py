import boto3
from botocore.exceptions import ClientError

AGENTS_TABLE_NAME = "c2-agents-table"

try:
    dynamodb_resource = boto3.resource("dynamodb", region_name="us-east-1")
    agents_table = dynamodb_resource.Table(AGENTS_TABLE_NAME)

except Exception as e:
    print(f"[ERROR] Unable to initialize AWS connection: {e}")

    agents_table = None


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
