import os

STATE_FILE = "src/agent/agent.id"


def get_agent_id():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            agent_id = f.read()

            return agent_id
    return None


def save_agent_id(agent_id):
    with open(STATE_FILE, "w") as f:
        f.write(agent_id)
