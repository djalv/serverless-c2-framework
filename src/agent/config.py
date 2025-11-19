import configparser
import os


def load_config():
    """
    The agent's function is responsible for loading the settings.
    """

    config = configparser.ConfigParser()
    config_file_path = "src/agent/config.ini"

    if not config.read(config_file_path):
        raise FileNotFoundError(f"File not found: {config_file_path}")

    try:
        c2_section = config["c2"]

        api_url = c2_section["api_url"]
        sleep_interval = config.getint("c2", "sleep_interval")
        results_url = c2_section["results_url"]

        return api_url, sleep_interval, results_url

    except KeyError as e:
        print(f"[CRITICAL] Incomplete configuration. Missing key: {e}")
        raise

    except ValueError as e:
        print(f"[CRITICAL] Invalid value in configuration: {e}")
        raise
