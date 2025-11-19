import pytest
import boto3
import os
from unittest.mock import MagicMock, call
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


# Testing operator_cli.aws_commands
def test_list_agents_returns_list_on_success(dynamodb_mock, monkeypatch):
    old_agent = {"agentId": "agent-old", "hostname": "host-old", "lastSeen": "2025-10-16T10:00:00"}
    new_agent = {"agentId": "agent-new", "hostname": "host-new", "lastSeen": "2025-10-16T12:00:00"}

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

    error_response = {"Error": {"Code": "AccessDeniedException", "Message": "Access Denied"}}
    mock_exception = ClientError(error_response, "Scan")

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

    error_response = {"Error": {"Code": "ProvisionedThroughputExceededException", "Message": "Rate exceeded"}}
    mock_exception = ClientError(error_response, "UpdateItem")

    mock_table.update_item.side_effect = mock_exception

    monkeypatch.setattr(aws_commands, "agents_table", mock_table)

    agent_id = "EXISTING-AGENT-ID-456"
    command = "whoami"

    result = aws_commands.send_task_to_agent(agent_id, command)

    assert not result
    mock_table.update_item.assert_called_once()


def test_execute_task_wait_result_when_there_is_no_s3_client_return_error(monkeypatch):
    monkeypatch.setattr(aws_commands, "s3_client", None)

    agent_id = "EXISTING-AGENT-ID-456"
    command = "whoami"

    result = aws_commands.execute_task_wait_result(agent_id, command)

    assert result == "[ERROR] S3 client reference is not available."


def test_execute_task_wait_result_success_file_appears(monkeypatch):
    agent_id = "EXISTING-AGENT-ID-456"
    command = "whoami"
    bucket_name = "fake-bucket"
    new_file_key = f"{agent_id}/result.txt"
    expected_content = "root"

    monkeypatch.setattr(aws_commands, "RESULTS_BUCKET_NAME", bucket_name)

    mock_s3 = MagicMock()
    monkeypatch.setattr(aws_commands, "s3_client", mock_s3)

    response_before = {}
    response_after = {"Contents": [{"Key": new_file_key}]}

    mock_s3.list_objects_v2.side_effect = [response_before, response_after]

    mock_body = MagicMock()
    mock_body.read.return_value = expected_content.encode("utf-8")
    mock_s3.get_object.return_value = {"Body": mock_body}

    mock_send_task = MagicMock(return_value=True)
    monkeypatch.setattr(aws_commands, "send_task_to_agent", mock_send_task)

    mock_sleep = MagicMock()
    monkeypatch.setattr(aws_commands, "time", MagicMock())
    monkeypatch.setattr(aws_commands.time, "sleep", mock_sleep)

    result = aws_commands.execute_task_wait_result(agent_id, command)

    assert result == expected_content

    mock_send_task.assert_called_once_with(agent_id, command)

    mock_sleep.assert_called()

    mock_s3.get_object.assert_called_with(Bucket=bucket_name, Key=new_file_key)


def test_execute_task_wait_result(monkeypatch):
    agent_id = "EXISTING-AGENT-ID-456"
    command = "whoami"
    bucket_name = "fake-bucket"
    new_file_key = f"{agent_id}/result.txt"

    monkeypatch.setattr(aws_commands, "RESULTS_BUCKET_NAME", bucket_name)

    mock_s3 = MagicMock()
    monkeypatch.setattr(aws_commands, "s3_client", mock_s3)

    response_before = {}
    response_after = {"Contents": [{"Key": new_file_key}]}

    mock_s3.list_objects_v2.side_effect = [response_before, response_after]

    mock_send_task = MagicMock(return_value=False)
    monkeypatch.setattr(aws_commands, "send_task_to_agent", mock_send_task)

    result = aws_commands.execute_task_wait_result(agent_id, command)

    assert result == "[ERROR] The task could not be submitted. Aborting."

    mock_send_task.assert_called_once_with(agent_id, command)


def test_execute_task_wait_result_returns_timeout_message(monkeypatch):
    agent_id = "agent-timeout"
    command = "sleep 100"
    bucket_name = "fake-bucket"

    monkeypatch.setattr(aws_commands, "RESULTS_BUCKET_NAME", bucket_name)

    mock_s3 = MagicMock()
    mock_s3.list_objects_v2.return_value = {"Contents": []}
    monkeypatch.setattr(aws_commands, "s3_client", mock_s3)

    mock_send_task = MagicMock(return_value=True)
    monkeypatch.setattr(aws_commands, "send_task_to_agent", mock_send_task)

    mock_time = MagicMock()
    monkeypatch.setattr(aws_commands, "time", mock_time)

    result = aws_commands.execute_task_wait_result(agent_id, command)

    assert result == "[TIMEOUT] No results received in 90 seconds."

    assert mock_time.sleep.call_count == 45
    mock_time.sleep.assert_called_with(2)


def test_execute_task_wait_result_handles_generic_exception(monkeypatch):
    agent_id = "agent-error"
    command = "error_cmd"

    mock_s3 = MagicMock()
    mock_exception = Exception("fake-exception")
    mock_s3.list_objects_v2.side_effect = mock_exception

    monkeypatch.setattr(aws_commands, "s3_client", mock_s3)

    result = aws_commands.execute_task_wait_result(agent_id, command)

    assert result == "[ERROR] Unexpected error occurred while fetching result: fake-exception"
