import pytest
import json
import os
import boto3
import datetime
from unittest.mock import MagicMock
from moto import mock_aws
from src.c2_backend.store_results.app import lambda_handler


@pytest.fixture
def fake_aws_credentials():
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture
def s3_bucket_mock(fake_aws_credentials, monkeypatch, mocker):
    bucket_name = "c2-results-bucket-test"
    monkeypatch.setenv("RESULTS_BUCKET_NAME", bucket_name)

    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket=bucket_name)

        mocker.patch("src.c2_backend.store_results.app.S3_CLIENT", s3)

        yield s3, bucket_name


def test_store_results_handler_valid_payload_returns_200(s3_bucket_mock, mocker):
    s3_client, bucket_name = s3_bucket_mock
    
    agent_id = "agent-123"
    task_result = "Command executed successfully\nUser: root"
    
    event = {
        "body": json.dumps({
            "agentId": agent_id,
            "taskResult": task_result
        })
    }

    response = lambda_handler(event, None)

    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["message"] == "Result stored success"
    
    s3_objects = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=f"{agent_id}/")

    assert "Contents" in s3_objects
    assert len(s3_objects["Contents"]) == 1

    actual_key = s3_objects["Contents"][0]["Key"]
    
    s3_object = s3_client.get_object(Bucket=bucket_name, Key=actual_key)
    content = s3_object["Body"].read().decode("utf-8")
    
    assert content == task_result


def test_store_results_handler_missing_body_returns_400(s3_bucket_mock):
    event = {}
    response = lambda_handler(event, None)

    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert "body is empty" in body["error"]


def test_store_results_handler_missing_agentid_returns_400(s3_bucket_mock):
    event = {"body": json.dumps({"taskResult": "some result"})}
    response = lambda_handler(event, None)

    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert "agentId" in body["error"]


def test_store_results_handler_s3_exception_returns_500(s3_bucket_mock, mocker):
    mock_s3_client = MagicMock()
    mock_s3_client.put_object.side_effect = Exception("S3 Service Down")

    mocker.patch("src.c2_backend.store_results.app.S3_CLIENT", mock_s3_client)

    event = {"body": json.dumps({"agentId": "agent-error", "taskResult": "result"})}

    response = lambda_handler(event, None)

    assert response["statusCode"] == 500
    body = json.loads(response["body"])
    assert "An internal server error occurred" in body["error"]


def test_store_results_handler_missing_bucket_env_returns_500(monkeypatch):
    monkeypatch.delenv("RESULTS_BUCKET_NAME", raising=False)

    event = {}

    response = lambda_handler(event, None)

    assert response["statusCode"] == 500
    body = json.loads(response["body"])
    assert "Server configuration error" in body["error"]


def test_store_results_handler_missing_task_result_returns_400(s3_bucket_mock):
    event = {"body": json.dumps({"agentId": "agent-123"})}
    response = lambda_handler(event, None)

    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert "taskResult is required." in body["error"]
