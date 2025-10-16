import configparser


def load_config():
    config = configparser.ConfigParser()
    config.read("src/agent/config.ini")

    api_url = config["c2"]["api_url"]
    sleep_interval = config.getint("c2", "sleep_interval")
    results_url = config["c2"]["results_url"]

    return api_url, sleep_interval, results_url
