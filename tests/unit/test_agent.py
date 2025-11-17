import pytest
import requests
from unittest.mock import patch, Mock, MagicMock, mock_open
from src.agent.comms import perform_checkin, send_results
from src.agent.config import load_config
from src.agent.state import get_agent_id, save_agent_id, STATE_FILE

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
    mock_post.assert_called_once_with(
        api_setup["url"], json=api_setup["data"], timeout=10
    )

@patch("src.agent.comms.requests.post")
def test_perform_checkin_returns_none_on_network_failure(mock_post, api_setup):
    mock_post.side_effect = requests.exceptions.Timeout()

    result = perform_checkin(api_setup["url"], api_setup["data"])

    assert result is None
    mock_post.assert_called_once_with(
        api_setup["url"], json=api_setup["data"], timeout=10
    )

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
    mock_post.assert_called_once_with(
        api_setup["results_url"], json=payload, timeout=10
    )

@patch("src.agent.comms.requests.post")
def test_send_results_returns_false_on_network_failure(mock_post, api_setup):
    mock_post.side_effect = requests.exceptions.Timeout()

    agent_id = api_setup["data"]["agentId"]
    task_result = api_setup["task_result"]
    payload = {"agentId": agent_id, "taskResult": task_result}

    result = send_results(api_setup["results_url"], agent_id, task_result)

    assert not result
    mock_post.assert_called_once_with(
        api_setup["results_url"], json=payload, timeout=10
    )

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

# Testing agent.state
def test_get_agent_id_returns_agent_id(mocker):
    fake_file_content = "  EXISTING-AGENT-ID-456  \n"
    expected_id = "EXISTING-AGENT-ID-456"
    
    mocker.patch('os.path.exists', return_value=True)
    mocker.patch('builtins.open', mock_open(read_data=fake_file_content))
    
    agent_id = get_agent_id()

    assert agent_id == expected_id

def test_get_agent_id_returns_none(mocker):
    mocker.patch('os.path.exists', return_value=False)

    agent_id = get_agent_id()
    assert agent_id == None

def test_save_agent_id_writes_id_to_file_correctly(mocker):
    content_to_write = "NEW-AGENT-ID-456"
    
    mock_open_write = mock_open()
    mocker.patch('builtins.open', mock_open_write)

    save_agent_id(content_to_write)
    mock_open_write.assert_called_once_with(STATE_FILE, 'w')
    mock_open_write().write.assert_called_once_with(content_to_write)