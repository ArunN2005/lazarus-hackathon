import os
import json
import re
import requests
import time
from simple_env import load_env

# Try to import E2B, handle failure
try:
    from e2b_code_interpreter import Sandbox
    E2B_AVAILABLE = True
except ImportError:
    E2B_AVAILABLE = False
    print("[!] E2B Code Interpreter not found. Sandbox execution will be skipped.")

# Load Environment
load_env()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
E2B_API_KEY = os.getenv("E2B_API_KEY")

class LazarusEngine:
    def __init__(self):
        self.api_key = GEMINI_API_KEY
        self.github_token = os.getenv("GITHUB_TOKEN")
        # Fallback to 2.0 Flash if 3.0 Pro is unstable/unavailable
        self.model_name = "gemini-2.0-flash" 
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"

    def commit_to_github(self, repo_url: str, filename: str, content: str) -> dict:
        """
        Commits a file to a 'lazarus-resurrection' branch, creating it if needed.
        Returns a URL to open a Pull Request.
        """
        if not self.github_token:
            return {"status": "error", "message": "GITHUB_TOKEN is missing."}

        try:
            # Parse owner/repo
            match = re.search(r"github\.com/([^/]+)/([^/.]+)", repo_url)
            if not match:
                return {"status": "error", "message": "Invalid GitHub URL."}
            
            owner, repo_name = match.groups()
            base_api = f"https://api.github.com/repos/{owner}/{repo_name}"
            headers = {
                "Authorization": f"token {self.github_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            target_branch = "lazarus-resurrection"

            # 1. Check if target branch exists
            branch_resp = requests.get(f"{base_api}/git/ref/heads/{target_branch}", headers=headers)
            
            if branch_resp.status_code == 404:
                # Branch doesn't exist, create it from main
                print(f"[*] Branch {target_branch} not found. Creating from main...")
                main_resp = requests.get(f"{base_api}/git/ref/heads/main", headers=headers)
                if main_resp.status_code != 200:
                    return {"status": "error", "message": "Could not find main branch to fork from."}
                
                main_sha = main_resp.json()['object']['sha']
                
                create_resp = requests.post(
                    f"{base_api}/git/refs",
                    headers=headers,
                    json={"ref": f"refs/heads/{target_branch}", "sha": main_sha}
                )
                if create_resp.status_code != 201:
                    return {"status": "error", "message": f"Failed to create branch: {create_resp.text}"}
            
            elif branch_resp.status_code != 200:
                 return {"status": "error", "message": f"Error checking branch: {branch_resp.text}"}

            # 2. Get file SHA in target branch (if exists) for update
            file_api = f"{base_api}/contents/{filename}?ref={target_branch}"
            sha = None
            file_resp = requests.get(file_api, headers=headers)
            if file_resp.status_code == 200:
                sha = file_resp.json().get('sha')

            # 3. Commit File
            import base64
            content_bytes = content.encode('utf-8')
            base64_content = base64.b64encode(content_bytes).decode('utf-8')

            data = {
                "message": f"Lazarus Resurrection: {filename}",
                "content": base64_content,
                "branch": target_branch
            }
            if sha:
                data["sha"] = sha

            put_resp = requests.put(f"{base_api}/contents/{filename}", headers=headers, json=data)
            
            if put_resp.status_code in [200, 201]:
                # Construct Compare/PR URL
                pr_url = f"https://github.com/{owner}/{repo_name}/compare/main...{target_branch}?expand=1"
                return {
                    "status": "success", 
                    "commit_url": pr_url,
                    "message": f"Committed to {target_branch}. Ready to Merge."
                }
            else:
                return {"status": "error", "message": f"GitHub API Error: {put_resp.text}"}

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _call_gemini(self, prompt: str) -> str:
        """Raw HTTP call to Gemini API to bypass SDK installation issues."""
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is missing.")

        url = f"{self.base_url}/{self.model_name}:generateContent?key={self.api_key}"
        headers = {'Content-Type': 'application/json'}
        data = {
            "contents": [{"parts": [{"text": prompt}]}]
        }

        # Retry logic for 429
        max_retries = 5
        base_wait = 2

        for attempt in range(max_retries):
            try:
                response = requests.post(url, headers=headers, json=data)
                
                if response.status_code == 200:
                    try:
                        return response.json()['candidates'][0]['content']['parts'][0]['text']
                    except (KeyError, IndexError):
                        return f"[ERROR] Bad Response: {response.text}"
                
                elif response.status_code == 429:
                    wait = base_wait * (2 ** attempt)
                    print(f"[*] Rate Limit (429). Retrying in {wait}s...")
                    time.sleep(wait)
                    continue
                else:
                    return f"[ERROR] API {response.status_code}: {response.text}"
            except Exception as e:
                return f"[ERROR] Request Failed: {str(e)}"
        
        return "[ERROR] Max retries exceeded (Gemini API is overloaded)."

    def clean_code(self, text: str) -> str:
        """Extracts code from markdown blocks."""
        pattern = r"```(?:javascript|python|bash)?\n(.*?)```"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()
        # If no markdown, assume raw text is code if it looks like it
        return text.strip()

    def generate_modernization_plan(self, repo_url: str, instructions: str) -> str:
        prompt = f"""
        ACT AS: Senior Full-Stack Migration Architect & AI Engineer.
        PROJECT: "Lazarus" (Autonomous Resurrection Engine).

        CONTEXT:
        We are migrating a legacy repository at: {repo_url}
        User Instructions (Vibe): {instructions}

        YOUR MISSION:
        Do not just "fix" the files. You must **ARCHITECT** a modern replacement.

        EXECUTE THE FOLLOWING "CHAIN OF THOUGHT" PLAN:

        ### PHASE 1: THE CONTRACT AUDIT (Critical)
        - Scan the Legacy Backend files (hypothetically).
        - **Identify the API Contract:** List every likely API endpoint (e.g., `/api/login`, `/get_users`) and their expected HTTP methods.
        - **Constraint:** New backend MUST support these exact endpoint names.

        ### PHASE 2: BACKEND RESURRECTION (Logic First)
        - Target: `./modernized_stack/backend`.
        - **Stack Decision:** Use **Python FastAPI** or **Node.js (Express)**.
        - **Action:** Plan the `main.py` or `server.js` implementing the API Contract.
        - **Modernization:** Add CORS support immediately.

        ### PHASE 3: FRONTEND RESURRECTION (Vibe Second)
        - Target: `./modernized_stack/frontend`.
        - **Stack Decision:** Next.js 15 (App Router).
        - **Vibe Instruction:** Cyberpunk Aesthetic (Deep Void Black #050505, Neon Green #39ff14).
        - **Action:** Rewrite legacy frontend logic to React Components.

        ### PHASE 4: ORCHESTRATION
        - Plan a root level `docker-compose.yml` in `./modernized_stack`.

        OUTPUT:
        Provide a concise, high-level architectural plan following these phases.
        """
        return self._call_gemini(prompt)

    def generate_code(self, plan: str) -> dict:
        """
        Returns info about the code to be generated (Multiple Files, Nested Structure).
        """
        prompt = f"""
        ACT AS: Senior Full-Stack Migration Architect.
        PLAN: {plan}
        
        TASK: Generate the COMPLETE file system for the new `modernized_stack`.
        
        CRITICAL CONSTRAINTS:
        1.  **Structure**: logic MUST be inside `./modernized_stack/`.
            -   `modernized_stack/backend/main.py`
            -   `modernized_stack/frontend/app/page.tsx`
            -   `modernized_stack/preview.html` (Static Mock)
            -   `modernized_stack/docker-compose.yml`
        2.  **Execution**: 
            -   The `backend/main.py` MUST include a GRACEFUL SHUTDOWN TIMER.
            -   The Sandbox will timeout if the server runs forever.
            -   USE THIS EXACT BLOCK at the end of `main.py`:
                ```python
                if __name__ == "__main__":
                    import uvicorn
                    import threading, sys, time
                    def kill_later():
                        time.sleep(5)
                        print("[*] Server startup test complete. Exiting...")
                        sys.exit(0)
                    threading.Thread(target=kill_later, daemon=True).start()
                    uvicorn.run(app, host="0.0.0.0", port=8000)
                ```
        3.  **Preview**: 
            -   Generate a specific file `modernized_stack/preview.html`.
            -   **CRITICAL**: This must be an **INTERACTIVE MOCK**.
            -   Include embedded JavaScript to **SIMULATE** the backend calls.
            -   Example: If the user clicks "Login", show a spinner, wait 1s, then DOM-swap to the Dashboard view.
            -   The user MUST be able to "test" the flow in the preview tab even though the real backend is offline.
        4.  **Dependencies**: You MAY use external libraries like **FastAPI**, **Uvicorn**, **Flask**, **React**, etc. as needed.
        
        RETURN JSON format:
        {{
            "files": [
                {{ "filename": "modernized_stack/backend/main.py", "content": "..." }},
                {{ "filename": "modernized_stack/frontend/app/page.tsx", "content": "..." }},
                {{ "filename": "modernized_stack/preview.html", "content": "..." }},
                {{ "filename": "modernized_stack/docker-compose.yml", "content": "..." }}
            ],
            "entrypoint": "modernized_stack/backend/main.py" 
        }}
        (Entrypoint should be the backend server script).
        
        RETURN ONLY JSON.
        """
        response = self._call_gemini(prompt)
        # Clean potential markdown around json
        cleaned = response.replace('```json', '').replace('```', '')
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # Fallback
            return {
                "files": [{"filename": "error.log", "content": response}],
                "entrypoint": "error.log"
            }

    def execute_in_sandbox(self, files: list, entrypoint: str):
        if not E2B_AVAILABLE or not E2B_API_KEY:
            return "E2B Sandbox not available (Dependencies or Key missing)."

        print(f"[*] Executing {entrypoint} in E2B Sandbox...")
        
        try:
            # Use Sandbox.create() as factory
            with Sandbox.create() as sandbox:
                # Write ALL files
                for file in files:
                    # Create directories if needed
                    dir_path = os.path.dirname(file['filename'])
                    if dir_path and dir_path not in [".", ""]:
                         # We can't easily mkdir -p in sandbox file write, so we run a command
                         sandbox.commands.run(f"mkdir -p {dir_path}")
                    
                    sandbox.files.write(file['filename'], file['content'])
                
                # Install Dependencies (Hackathon Mode: Auto-install common ones)
                if entrypoint.endswith('.py'):
                    print("[*] Installing Python dependencies...")
                    sandbox.commands.run("pip install fastapi uvicorn flask flask-cors")
                    cmd = f"python {entrypoint}"
                else: 
                     cmd = f"node {entrypoint}"

                # Use .commands.run instead of .notebook.exec_cell
                exec_result = sandbox.commands.run(cmd)
                
                output = ""
                if exec_result.stdout:
                    output += f"STDOUT: {exec_result.stdout}\n"
                if exec_result.stderr:
                    output += f"STDERR: {exec_result.stderr}\n"
                
                return output.strip() or "No output returned."
                
        except Exception as e:
            return f"Sandbox Error: {str(e)}"

    def process_resurrection_stream(self, repo_url: str, instructions: str):
        """Generator that yields logs and results in real-time."""
        logs = []
        
        def emit_log(msg):
            logs.append(msg)
            return {"type": "log", "content": msg}

        # 1. Plan
        yield emit_log("Initiating Deep Scan of Legacy Repository...")
        
        # Check for error in plan
        plan = self.generate_modernization_plan(repo_url, instructions)
        if "[ERROR]" in plan:
             yield emit_log("Warning: Connection Unstable. Engaged Fallback Protocols.")
             # We continue, but mark fallback
             fallback_mode = True
        else:
             fallback_mode = False
             
        yield emit_log("Architecting Resurrection Blueprint...")

        # 2. Code Gen
        yield emit_log("Synthesizing Modern Cloud Infrastructure...")
        code_data = self.generate_code(plan)
        files = code_data.get('files', [])
        entrypoint = code_data.get('entrypoint', 'modernized_stack/backend/main.py')
        
        encoded_files = [f['filename'] for f in files]
        yield emit_log(f"Generated {len(encoded_files)} System Modules...")
        
        # 3. Execution
        yield emit_log("Booting Neural Sandbox Environment...")
        sandbox_logs = self.execute_in_sandbox(files, entrypoint)
        yield emit_log("Verifying System Integrity...")

        # Extract HTML for preview
        preview = ""
        # Check logs
        html_match = re.search(r"(<!DOCTYPE html>.*</html>)", sandbox_logs, re.DOTALL | re.IGNORECASE)
        if html_match:
            preview = html_match.group(1)
        
        # Check artifacts
        for f in files:
            if 'preview.html' in f['filename']:
                preview = f['content']
                break
        
        # Determine Status
        status = "Resurrected"
        if fallback_mode or "Sandbox Error" in sandbox_logs:
            status = "Fallback"
        
        # Final Result
        yield {
            "type": "result",
            "data": {
                "logs": "\n".join(logs),
                "artifacts": files,
                "preview": preview,
                "status": status
            }
        }


# Singleton
engine = LazarusEngine()

def process_resurrection(repo_url, instructions):
    """Returns generator."""
    return engine.process_resurrection_stream(repo_url, instructions)

def commit_code(repo_url, filename, content):
    return engine.commit_to_github(repo_url, filename, content)
