import os

STATE_FILE = "src/agent/agent.id"


def get_agent_id():
    """
    The agent function responsible for retrieving the agent ID saved in a file.
    """

    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            agent_id = f.read().strip()

            return agent_id if agent_id else None
    return None


def save_agent_id(agent_id):
    """
    The agent function responsible for saving the agent ID to a file.
    """
    with open(STATE_FILE, "w") as f:
        f.write(str(agent_id))
