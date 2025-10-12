import os
import requests
import boto3
import pytest

# --- Setup ---
API_URL = os.environ.get('API_ENDPOINT_URL')

# Initializes the DynamoDB client for verification
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
AGENTS_TABLE_NAME = 'c2-agents-table'
agents_table = dynamodb.Table(AGENTS_TABLE_NAME)

# --- Tests ---
def test_checkin_flow_for_new_agent():
    test_host = 'integration-test-host'
    request_payload = {
        'hostname': test_host
    }

    response = requests.post(API_URL, json=request_payload)

    assert response.status_code == 200

    response_data = response.json()
    assert 'agentId' in response_data
    assert response_data['message'] == 'Check-in successful'

    new_agent_id = response_data['agentId']
    assert new_agent_id is not None

    try:
        db_response = agents_table.get_item(
            Key={'agentId': new_agent_id}
        )

        assert 'Item' in db_response

        created_item = db_response['Item']

        assert created_item["agentId"] == new_agent_id
        assert created_item["hostname"] == test_host
        assert "lastSeen" in created_item
    
    finally:
        agents_table.delete_item(Key={'agentId': new_agent_id})