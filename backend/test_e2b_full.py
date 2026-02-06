from e2b_code_interpreter import Sandbox
from simple_env import load_env
import os
import traceback

load_env()

print("[*] Testing Sandbox...")
try:
    with Sandbox.create() as sb:
        with open("sb_attrs.txt", "w") as f:
            f.write(str(dir(sb)))
        print("Success")
except Exception:
    with open("traceback.txt", "w") as f:
        traceback.print_exc(file=f)
