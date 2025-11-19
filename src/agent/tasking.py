import subprocess


def execute_task(command):
    """
    The agent function responsible for running commands.
    """
    try:
        print("[INFO] Task executed")
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return f"{result.stdout.strip()}"
        else:
            return f"Error: {result.stderr}"

    except Exception as e:
        print(f"[ERROR] Error executing task on host: {e}")
        return f"Failed to execute command on host. Error: {e}"
