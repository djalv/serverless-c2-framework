import pytest
import requests
from unittest.mock import patch, Mock
from src.agent.comms import perform_checkin, send_results


@pytest.fixture
def api_setup():
    return {
        "url": "https://c2server.example.com/checkin",
        "results_url": "https://c2server.example.com/results",
        "data": {"agentId": "EXISTING-AGENT-ID-456", "hostname": "test-host"},
        "task_result": "test-result"
    }


@patch('src.agent.comms.requests.post')
def test_successful_checkin(mock_post, api_setup):
    expected = {
        "message": "Check-in successful",
        "agentId": "EXISTING-AGENT-ID-456",
        "task": "no-task-for-now"
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

@patch('src.agent.comms.requests.post')
def test_perform_checkin_timeout_returns_none(mock_post, api_setup):
    mock_post.side_effect = requests.exceptions.Timeout()

    result = perform_checkin(api_setup["url"], api_setup["data"])

    assert result is None
    mock_post.assert_called_once_with(
        api_setup["url"], json=api_setup["data"], timeout=10
    )


@patch('src.agent.comms.requests.post')
def test_successful_sending_results(mock_post, api_setup):
    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    agent_id = api_setup['data']['agentId']
    task_result = api_setup['task_result']
    payload = {"agentId": agent_id, "taskResult": task_result}

    result = send_results(api_setup["results_url"], agent_id, task_result)

    assert result
    mock_post.assert_called_once_with(
        api_setup["results_url"], json=payload, timeout=10
    )

@patch('src.agent.comms.requests.post')
def test_sending_results_timeout_returns_false(mock_post, api_setup):
    mock_post.side_effect = requests.exceptions.Timeout()

    agent_id = api_setup['data']['agentId']
    task_result = api_setup['task_result']
    payload = {"agentId": agent_id, "taskResult": task_result}

    result = send_results(api_setup["results_url"], agent_id, task_result)

    assert not result
    mock_post.assert_called_once_with(
        api_setup["results_url"], json=payload, timeout=10
    )