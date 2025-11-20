import pytest
import json
import os
import boto3
import logging
from botocore.exceptions import ClientError
from unittest.mock import MagicMock, patch
from moto import mock_aws
from src.c2_backend.checkin.app import lambda_handler


@pytest.fixture
def fake_aws_credentials():
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture
def dynamodb_mock(fake_aws_credentials, monkeypatch, mocker):
    """Cria a tabela DynamoDB simulada."""
    TABLE_NAME = "c2-agents-table-test"
    monkeypatch.setenv("TABLE_NAME", TABLE_NAME)

    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        dynamodb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[{"AttributeName": "agentId", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "agentId", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        mocker.patch("src.c2_backend.checkin.app.DYNAMODB_CLIENTE", dynamodb)
        
        yield dynamodb.Table(TABLE_NAME)


def test_checkin_handler_new_agent_returns_200_and_new_id(dynamodb_mock, mocker):
    fake_uuid = "12345678-1234-5678-1234-567812345678"
    mocker.patch("uuid.uuid4", return_value=fake_uuid)

    event = {"body": json.dumps({"hostname": "linux-box"}), "requestContext": {"identity": {"sourceIp": "10.0.0.1"}}}

    response = lambda_handler(event, None)

    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["agentId"] == fake_uuid
    assert body["task"] == "no-task-for-now"

    item = dynamodb_mock.get_item(Key={"agentId": fake_uuid})["Item"]
    assert item["hostname"] == "linux-box"
    assert item["sourceIp"] == "10.0.0.1"


def test_checkin_handler_existing_agent_with_task_returns_task(dynamodb_mock):
    agent_id = "agent-007"
    task_cmd = "whoami"

    dynamodb_mock.put_item(Item={"agentId": agent_id, "hostname": "old-host", "pendingTask": task_cmd})

    event = {
        "body": json.dumps({"hostname": "old-host", "agentId": agent_id}),
        "requestContext": {"identity": {"sourceIp": "10.0.0.1"}},
    }

    response = lambda_handler(event, None)

    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["agentId"] == agent_id
    assert body["task"] == task_cmd

    item = dynamodb_mock.get_item(Key={"agentId": agent_id})["Item"]
    assert "pendingTask" not in item


def test_checkin_handler_missing_body_returns_400(monkeypatch):
    monkeypatch.setenv("TABLE_NAME", "test-table")

    event = {}
    response = lambda_handler(event, None)

    assert response["statusCode"] == 400
    assert "body is empty" in json.loads(response["body"])["error"]


def test_checkin_handler_dynamodb_exception_returns_500(mocker):
    mock_table = MagicMock()

    mock_table.put_item.side_effect = Exception("AWS Down")

    mock_dynamodb_resource = MagicMock()
    mock_dynamodb_resource.Table.return_value = mock_table

    mocker.patch("src.c2_backend.checkin.app.DYNAMODB_CLIENTE", mock_dynamodb_resource)

    mocker.patch.dict(os.environ, {"TABLE_NAME": "any-table"})

    event = {"body": json.dumps({"hostname": "fail-box"}), "requestContext": {"identity": {"sourceIp": "1.1.1.1"}}}

    response = lambda_handler(event, None)

    assert response["statusCode"] == 500
    assert "internal server error" in json.loads(response["body"])["error"]


def test_checkin_handler_missing_table_name_env_returns_500(monkeypatch):
    monkeypatch.delenv("TABLE_NAME", raising=False)

    event = {}
    context = None

    response = lambda_handler(event, context)

    assert response["statusCode"] == 500
    body = json.loads(response["body"])
    assert "Server configuration error" in body["error"]


def test_checkin_handler_client_error_logs_and_continues(mocker, caplog):
    mocker.patch.dict(os.environ, {"TABLE_NAME": "c2-agents-table-test"})

    fake_uuid = "12345678-1234-5678-1234-567812345678"
    mocker.patch("uuid.uuid4", return_value=fake_uuid)

    mock_table = MagicMock()

    error_response = {"Error": {"Code": "ProvisionedThroughputExceededException", "Message": "Rate Exceeded"}}
    client_error = ClientError(error_response, "GetItem")

    mock_table.get_item.side_effect = client_error

    mock_resource = MagicMock()
    mock_resource.Table.return_value = mock_table

    mocker.patch("src.c2_backend.checkin.app.DYNAMODB_CLIENTE", mock_resource)

    event = {"body": json.dumps({"hostname": "test-host"}), "requestContext": {"identity": {"sourceIp": "127.0.0.1"}}}

    with caplog.at_level(logging.ERROR):
        response = lambda_handler(event, None)

    assert response["statusCode"] == 200

    assert "Error fetching task from DynamoDB" in caplog.text
    assert "ProvisionedThroughputExceededException" in caplog.text

    mock_table.put_item.assert_called_once()
