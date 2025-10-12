import time
import socket
import config
import state
import comms


def run_agent_loop():
    api_url, sleep_interval = config.load_config()

    while True:
        agent_id = state.get_agent_id()
        hostname = socket.gethostname()

        payload = {"hostname": hostname}

        if agent_id:
            payload["agentId"] = agent_id

        response_checkin = comms.perform_checkin(api_url, payload)

        if response_checkin:
            if "agentId" in response_checkin:
                new_agent_id = response_checkin["agentId"]
                state.save_agent_id(new_agent_id)

            # -- Response task processing --
        else:
            print(f"Check-in failed. Trying again in {sleep_interval}s.")

        time.sleep(sleep_interval)
