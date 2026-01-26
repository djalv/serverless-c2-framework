import json
from cryptography.fernet import Fernet
from . import config


def encrypt(data_dict):
    data_dict_string = json.dumps(data_dict)
    data_bytes = data_dict_string.encode("utf-8")

    AES_KEY = config.AES_KEY
    f = Fernet(AES_KEY)

    encrypted_bytes = f.encrypt(data_bytes)

    return encrypted_bytes.decode("utf-8")


def decrypt(encrypt_string):
    AES_KEY = config.AES_KEY
    f = Fernet(AES_KEY)

    try:
        if isinstance(encrypt_string, str):
            encrypt_string = encrypt_string.encode("utf-8")

        decrypted_bytes = f.decrypt(encrypt_string)
        decrypted_string = decrypted_bytes.decode("utf-8")

        return json.loads(decrypted_string)

    except Exception as e:
        print(f"[ERROR] Decryption failed: {e}")
        return None
