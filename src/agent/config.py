import configparser


def load_config():
    config = configparser.ConfigParser()
    config.read("config.ini")

    api_url = config["c2"]["api_url"]
    sleep_interval = config["c2"]["sleep_interval"]

    return api_url, sleep_interval
