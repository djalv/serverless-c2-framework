import pytest
import boto3
import os
from unittest.mock import MagicMock, call, patch, Mock
from moto import mock_aws
from botocore.exceptions import ClientError
from src.operator_cli import aws_commands
from src.operator_cli import formatter
from src.operator_cli.operator_cli import handle_list_agents, handle_send_task


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
    agent_id = "EXISTING-AGENT-ID-456"
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
    agent_id = "EXISTING-AGENT-ID-456"
    command = "error_cmd"

    mock_s3 = MagicMock()
    mock_exception = Exception("fake-exception")
    mock_s3.list_objects_v2.side_effect = mock_exception

    monkeypatch.setattr(aws_commands, "s3_client", mock_s3)

    result = aws_commands.execute_task_wait_result(agent_id, command)

    assert result == "[ERROR] Unexpected error occurred while fetching result: fake-exception"


# Testing operator_cli.formatter
@patch("src.operator_cli.formatter.Rule")
@patch("src.operator_cli.formatter.Console")
def test_print_banner_prints_art_and_rules(mock_console_cls, mock_rule_cls):
    mock_console_instance = mock_console_cls.return_value

    formatter.print_banner()

    assert mock_console_instance.print.call_count == 4
    assert mock_rule_cls.call_count == 2


def test_print_agents_table_prints_error_message_on_empty_list(capsys):
    empty_list = []

    formatter.print_agents_table(empty_list)

    captured = capsys.readouterr()
    assert "[ERROR] No agents found." in captured.out


@patch("src.operator_cli.formatter.Table")
@patch("src.operator_cli.formatter.Console")
def test_print_agents_table_creates_table_and_adds_rows_correctly(mock_console_cls, mock_table_cls):
    mock_console_instance = mock_console_cls.return_value
    mock_table_instance = mock_table_cls.return_value

    agents_data = [
        {
            "agentId": "EXISTING-AGENT-ID-456",
            "lastSeen": "2023-01-01",
            "hostname": "host-1",
            "os_name": "Linux",
            "sourceIp": "1.1.1.1",
        },
        {"agentId": "EXISTING-AGENT-ID-789", "hostname": "host-2", "os_name": "Windows", "sourceIp": "2.2.2.2"},
    ]

    formatter.print_agents_table(agents_data)
    mock_table_cls.assert_called_once_with(title="Agents", show_header=True, header_style="bold cyan")

    assert mock_table_instance.add_column.call_count == 5

    expected_calls = [
        call("EXISTING-AGENT-ID-456", "2023-01-01", "host-1", "Linux", "1.1.1.1"),
        call("EXISTING-AGENT-ID-789", "N/A", "host-2", "Windows", "2.2.2.2"),
    ]
    mock_table_instance.add_row.assert_has_calls(expected_calls)

    mock_console_instance.print.assert_called_once_with(mock_table_instance)


@patch("src.operator_cli.formatter.Panel")
@patch("src.operator_cli.formatter.Console")
def test_print_task_result_creates_panel_and_prints(mock_console_cls, mock_panel_cls):
    mock_console_instance = mock_console_cls.return_value

    mock_panel_instance = Mock()
    mock_panel_cls.fit.return_value = mock_panel_instance

    result_content = "Command Output\nSuccess"
    agent_id = "EXISTING-AGENT-ID-456"

    formatter.print_task_result(result_content, agent_id)

    mock_panel_cls.fit.assert_called_once_with(
        result_content, title=f"Agent's Result {agent_id}", border_style="green", padding=(1, 2)
    )

    mock_console_instance.print.assert_called_once_with(mock_panel_instance)


@patch("src.operator_cli.operator_cli.formatter.print_agents_table")
@patch("src.operator_cli.operator_cli.aws_commands.list_agents")
def test_handle_list_agents_retrieves_and_prints_agents(mock_list_agents, mock_print_table):
    fake_agents_list = [
        {"agentId": "EXISTING-AGENT-ID-456", "hostname": "host-1"},
        {"agentId": "EXISTING-AGENT-ID-789", "hostname": "host-2"}
    ]
    mock_list_agents.return_value = fake_agents_list
    handle_list_agents()

    mock_list_agents.assert_called_once()

    mock_print_table.assert_called_once_with(fake_agents_list)


@patch("src.operator_cli.operator_cli.formatter.print_agents_table")
@patch("src.operator_cli.operator_cli.aws_commands.list_agents")
def test_handle_list_agents_handles_empty_list(mock_list_agents, mock_print_table):
    mock_list_agents.return_value = []

    handle_list_agents()

    mock_list_agents.assert_called_once()
    mock_print_table.assert_called_once_with([])


@patch("src.operator_cli.operator_cli.formatter.print_task_result")
@patch("src.operator_cli.operator_cli.aws_commands.execute_task_wait_result")
def test_handle_send_task_executes_and_prints_result(mock_execute_task, mock_print_result):
    fake_agent_id = "EXISTING-AGENT-ID-456"
    fake_command = "whoami"
    fake_result_content = "root\n"

    mock_execute_task.return_value = fake_result_content

    handle_send_task(fake_agent_id, fake_command)

    mock_execute_task.assert_called_once_with(fake_agent_id, fake_command)

    mock_print_result.assert_called_once_with(fake_result_content, fake_agent_id)