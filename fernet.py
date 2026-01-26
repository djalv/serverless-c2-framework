from cryptography.fernet import Fernet

key = Fernet.generate_key()

print(f"Key (bytes): {key}")
print(f"Key (decoded string): {key.decode()}")