import configparser


def load_config():
    """
    The agent's function is responsible for loading the settings.
    """

    config = configparser.ConfigParser()
    config_file_path = "src/agent/config.ini"
    if not config.read(config_file_path):
        raise FileNotFoundError(f"File not found: {config_file_path}")

    api_url = config["c2"]["api_url"]
    sleep_interval = config.getint("c2", "sleep_interval")
    results_url = config["c2"]["results_url"]

    return api_url, sleep_interval, results_url
