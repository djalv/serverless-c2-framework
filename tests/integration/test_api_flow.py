import os
import requests
import boto3
import pytest

# --- Fixtures ---


@pytest.fixture(scope="module")
def dynamodb_table():
    table_name = "c2-agents-table"
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    return dynamodb.Table(table_name)


# --- Tests ---


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
