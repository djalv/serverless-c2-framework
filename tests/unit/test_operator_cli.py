import pytest
import boto3
import os
from unittest.mock import MagicMock
from moto import mock_aws
from botocore.exceptions import ClientError
from src.operator_cli import aws_commands


@pytest.fixture(scope="function")
def fake_aws_credentials():
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture(scope="function")
def dynamodb_mock(fake_aws_credentials):
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

        table = dynamodb.create_table(
            TableName="c2-agents-table",
            KeySchema=[{"AttributeName": "agentId", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "agentId", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        yield table


def test_list_agents_returns_list_on_success(dynamodb_mock, monkeypatch):
    old_agent = {
        "agentId": "agent-old",
        "hostname": "host-old",
        "lastSeen": "2025-10-16T10:00:00"
    }
    new_agent = {
        "agentId": "agent-new",
        "hostname": "host-new",
        "lastSeen": "2025-10-16T12:00:00"
    }

    dynamodb_mock.put_item(Item=old_agent)
    dynamodb_mock.put_item(Item=new_agent)

    monkeypatch.setattr(aws_commands, "agents_table", dynamodb_mock)

    result = aws_commands.list_agents()
    assert isinstance(result, list)
    
    assert len(result) == 2
    
    assert result[0]["agentId"] == "agent-new"
    assert result[1]["agentId"] == "agent-old"


def test_list_agents_returns_empty_list_when_table_reference_is_none(monkeypatch):
    monkeypatch.setattr(aws_commands, "agents_table", None)

    result = aws_commands.list_agents()

    assert result == []

def test_list_agents_returns_empty_list_on_client_error(monkeypatch):
    mock_table = MagicMock()

    error_response = {'Error': {'Code': 'AccessDeniedException', 'Message': 'Access Denied'}}
    mock_exception = ClientError(error_response, 'Scan')

    mock_table.scan.side_effect = mock_exception
    monkeypatch.setattr(aws_commands, "agents_table", mock_table)

    result = aws_commands.list_agents()

    assert result == []
    
    mock_table.scan.assert_called_once()


def test_list_agents_returns_empty_list_on_generic_exception(monkeypatch, capsys):
    mock_table = MagicMock()

    mock_exception = Exception("Fake memory error")
    mock_table.scan.side_effect = mock_exception

    monkeypatch.setattr(aws_commands, "agents_table", mock_table)

    result = aws_commands.list_agents()
    assert result == []

    captured = capsys.readouterr()
    assert "[ERROR] Unexpected error occurred while listing agents: Fake memory error" in captured.out


def test_send_task_to_agent_updates_item_successfully(monkeypatch):
    mock_table = MagicMock()
    monkeypatch.setattr(aws_commands, "agents_table", mock_table)

    agent_id = "EXISTING-AGENT-ID-456"
    command = "whoami"

    result = aws_commands.send_task_to_agent(agent_id, command)

    assert result

    mock_table.update_item.assert_called_once_with(
        Key={"agentId": agent_id},
        UpdateExpression="SET pendingTask = :task_value",
        ExpressionAttributeValues={":task_value": command},
    )


def test_send_task_to_agent_returns_false_when_table_is_none(monkeypatch):
    monkeypatch.setattr(aws_commands, "agents_table", None)

    agent_id = "EXISTING-AGENT-ID-456"
    command = "whoami"

    result = aws_commands.send_task_to_agent(agent_id, command)

    assert not result

def test_send_task_to_agent_handles_client_error(monkeypatch):
    mock_table = MagicMock()

    error_response = {'Error': {'Code': 'ProvisionedThroughputExceededException', 'Message': 'Rate exceeded'}}
    mock_exception = ClientError(error_response, 'UpdateItem')

    mock_table.update_item.side_effect = mock_exception
    
    monkeypatch.setattr(aws_commands, "agents_table", mock_table)

    agent_id = "EXISTING-AGENT-ID-456"
    command = "whoami"

    result = aws_commands.send_task_to_agent(agent_id, command)

    assert not result
    mock_table.update_item.assert_called_once()


