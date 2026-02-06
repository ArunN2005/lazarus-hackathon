from e2b_code_interpreter import Sandbox
from simple_env import load_env
import os

load_env()
print("[*] Testing E2B Sandbox Connection (Final Check)...")

try:
    with Sandbox.create() as sb:
        print("[*] Sandbox created.")
        
        # Test Filesystem
        sb.files.write("test.txt", "Hello World")
        print("[*] File written.")
        
        # Test Command
        cmd = sb.commands.run("cat test.txt")
        print(f"[*] Command Output: {cmd.stdout}")
        
except Exception as e:
    print(f"[!] E2B Test Failed: {e}")
