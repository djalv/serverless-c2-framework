import pytest
import boto3
import requests
import os
import uuid
import time
from src.operator_cli import aws_commands


@pytest.fixture(scope="module")
def dynamodb_table():
    table_name = "c2-agents-table"
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    return dynamodb.Table(table_name)


@pytest.fixture(scope="module")
def aws_resources():
    return {
        "dynamodb": boto3.resource("dynamodb", region_name="us-east-1"),
        "s3": boto3.client("s3", region_name="us-east-1"),
        "table_name": "c2-agents-table",
        "bucket_name": "c2-results-bucket-alvaroneto-654561",
        "api_url": os.environ.get("API_ENDPOINT_URL"),
    }


@pytest.mark.integration
def test_checkin_flow_for_new_agent(dynamodb_table):
    API_URL = os.environ.get("API_ENDPOINT_URL")

    test_host = "integration-test-host"
    request_payload = {"hostname": test_host}

    response = requests.post(API_URL, json=request_payload)

    assert response.status_code == 200

    response_data = response.json()
    assert "agentId" in response_data
    assert response_data["message"] == "Check-in successful"

    new_agent_id = response_data["agentId"]
    assert new_agent_id is not None

    try:
        db_response = dynamodb_table.get_item(Key={"agentId": new_agent_id})

        assert "Item" in db_response

        created_item = db_response["Item"]

        assert created_item["agentId"] == new_agent_id
        assert created_item["hostname"] == test_host
        assert "lastSeen" in created_item

    finally:
        dynamodb_table.delete_item(Key={"agentId": new_agent_id})


@pytest.mark.integration
def test_operator_can_write_task_to_dynamodb(aws_resources):
    table = aws_resources["dynamodb"].Table(aws_resources["table_name"])
    agent_id = f"integration-test-{uuid.uuid4()}"
    task_cmd = "whoami"

    table.put_item(Item={"agentId": agent_id, "hostname": "test-host", "lastSeen": "now"})

    try:
        success = aws_commands.send_task_to_agent(agent_id, task_cmd)
        assert success is True

        response = table.get_item(Key={"agentId": agent_id})
        assert "Item" in response
        assert response["Item"].get("pendingTask") == task_cmd

    finally:
        table.delete_item(Key={"agentId": agent_id})


@pytest.mark.integration
def test_backend_delivers_and_clears_task(aws_resources):
    table = aws_resources["dynamodb"].Table(aws_resources["table_name"])
    agent_id = f"integration-test-{uuid.uuid4()}"
    task_cmd = "ls -la"

    table.put_item(Item={"agentId": agent_id, "hostname": "test-host", "pendingTask": task_cmd})

    try:
        payload = {"agentId": agent_id, "hostname": "test-host"}
        response = requests.post(aws_resources["api_url"], json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["task"] == task_cmd

        time.sleep(1)
        db_item = table.get_item(Key={"agentId": agent_id})["Item"]
        assert "pendingTask" not in db_item

    finally:
        table.delete_item(Key={"agentId": agent_id})


@pytest.mark.integration
def test_backend_stores_result_in_s3(aws_resources):
    results_api_url = aws_resources["api_url"].replace("/checkin", "/results")

    agent_id = f"integration-result-{uuid.uuid4()}"
    task_result_content = "Root User Access Granted"

    payload = {"agentId": agent_id, "taskResult": task_result_content}

    response = requests.post(results_api_url, json=payload)
    assert response.status_code == 200

    s3 = aws_resources["s3"]
    bucket = aws_resources["bucket_name"]

    found = False
    for _ in range(5):
        time.sleep(1)
        objects = s3.list_objects_v2(Bucket=bucket, Prefix=f"{agent_id}/")
        if "Contents" in objects:
            found = True
            file_key = objects["Contents"][0]["Key"]

            # Lê o arquivo
            file_obj = s3.get_object(Bucket=bucket, Key=file_key)
            content = file_obj["Body"].read().decode("utf-8")
            assert content == task_result_content

            # Cleanup do arquivo S3
            s3.delete_object(Bucket=bucket, Key=file_key)
            break

    assert found
