import pytest
import boto3
import requests
import os
import uuid
import time
from src.operator_cli import aws_commands


@pytest.fixture(scope="module")
def e2e_env():
    return {
        "dynamodb": boto3.resource("dynamodb", region_name="us-east-1"),
        "s3": boto3.client("s3", region_name="us-east-1"),
        "table_name": "c2-agents-table",
        "api_url": os.environ.get("API_ENDPOINT_URL"),
        "results_api_url": os.environ.get("API_ENDPOINT_URL").replace("/checkin", "/results"),
    }


@pytest.mark.e2e
def test_e2e_complete_command_cycle(e2e_env):
    agent_id = None
    hostname = f"e2e-host-{uuid.uuid4()}"
    command_to_run = "echo 'E2E Test'"
    expected_output = "E2E Test Output"

    resp1 = requests.post(e2e_env["api_url"], json={"hostname": hostname})
    assert resp1.status_code == 200
    agent_id = resp1.json()["agentId"]

    try:
        aws_commands.send_task_to_agent(agent_id, command_to_run)

        time.sleep(1)
        resp2 = requests.post(e2e_env["api_url"], json={"agentId": agent_id, "hostname": hostname})
        assert resp2.status_code == 200
        received_task = resp2.json()["task"]
        assert received_task == command_to_run

        resp3 = requests.post(e2e_env["results_api_url"], json={"agentId": agent_id, "taskResult": expected_output})
        assert resp3.status_code == 200

        s3_client = e2e_env["s3"]
        bucket_name = "c2-results-bucket-alvaroneto-654561"

        prefix = f"{agent_id}/"

        found_content = None
        for _ in range(5):
            time.sleep(2)
            response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
            if "Contents" in response:
                latest = sorted(response["Contents"], key=lambda x: x["LastModified"], reverse=True)[0]
                file_obj = s3_client.get_object(Bucket=bucket_name, Key=latest["Key"])
                found_content = file_obj["Body"].read().decode("utf-8")
                break

        assert found_content == expected_output

    finally:
        e2e_env["dynamodb"].Table(e2e_env["table_name"]).delete_item(Key={"agentId": agent_id})


@pytest.mark.e2e
def test_e2e_multiple_agents_listing(e2e_env):
    agents = [f"e2e-agent-{i}-{uuid.uuid4()}" for i in range(3)]
    table = e2e_env["dynamodb"].Table(e2e_env["table_name"])

    for ag in agents:
        table.put_item(Item={"agentId": ag, "hostname": f"host-{ag}", "lastSeen": "2025-01-01"})

    try:
        listed_agents = aws_commands.list_agents()

        ids_found = [a["agentId"] for a in listed_agents]
        for ag in agents:
            assert ag in ids_found

    finally:
        for ag in agents:
            table.delete_item(Key={"agentId": ag})
