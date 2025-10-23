import subprocess


def execute_task(command):
    try:
        print("[INFO] Task executed")
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=30
        )
        return f"{result.stdout}{result.stderr}"

    except Exception as e:
        print(f"[ERROR] Error executing task on host: {e}")
        return f"Failed to execute command on host. Error: {e}"
