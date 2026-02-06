from e2b_code_interpreter import Sandbox as CodeInterpreter
from simple_env import load_env
import os

load_env()
E2B_API_KEY = os.getenv("E2B_API_KEY")

print(f"[*] Testing E2B Sandbox Connection with Key: {E2B_API_KEY[:5]}...")

try:
    with CodeInterpreter() as sandbox:
        print("[*] Sandbox created.")
        execution = sandbox.notebook.exec_cell("print('Hello from the E2B Sandbox!')")
        print(f"[*] Execution Result: {execution.text}")
        
except Exception as e:
    print(f"[!] E2B Test Failed: {e}")
