import os

def load_env():
    """Simple .env loader since python-dotenv is unavailable."""
    try:
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
        print("[*] Environment variables loaded.")
    except FileNotFoundError:
        print("[!] .env file not found.")
