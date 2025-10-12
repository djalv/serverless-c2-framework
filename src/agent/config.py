import configparser


def load_config():
    config = configparser.ConfigParser()
    config.read("src/agent/config.ini")

    api_url = config["c2"]["api_url"]
    sleep_interval = config.getint("c2", "sleep_interval")

    return api_url, sleep_interval
