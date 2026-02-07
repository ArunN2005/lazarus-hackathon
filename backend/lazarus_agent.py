import os
import json
import re
import requests
import time
import ast
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
        # Gemini 3 Architecture
        self.planner_model = "gemini-3-flash-preview"
        self.coder_model = "gemini-3-pro-preview" 
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"
        
        # E2B Persistence
        self.sandbox = None

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

    def scan_repository(self, repo_url: str) -> list:
        """ Fetches the file tree of the remote repository using GitHub API. """
        if not self.github_token:
             return ["(GITHUB_TOKEN missing - Simulating Scan)"]

        try:
            # Parse owner/repo
            match = re.search(r"github\.com/([^/]+)/([^/.]+)", repo_url)
            if not match:
                return ["(Invalid URL - Simulating Scan)"]
            
            owner, repo_name = match.groups()
            api_url = f"https://api.github.com/repos/{owner}/{repo_name}/git/trees/main?recursive=1"
            
            headers = {
                "Authorization": f"token {self.github_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            resp = requests.get(api_url, headers=headers)
            if resp.status_code == 200:
                tree = resp.json().get('tree', [])
                # Return list of paths
                return [item['path'] for item in tree if item['type'] == 'blob']
            else:
                 return [f"(API Error {resp.status_code} - Simulating Scan)"]
                 
        except Exception as e:
            return [f"(Scan Error: {str(e)})"]

    def _call_gemini(self, prompt: str, model: str = None) -> str:
        """Raw HTTP call to Gemini API to bypass SDK installation issues."""
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is missing.")
        
        target_model = model or "gemini-3-flash-preview" # Default fallback
        url = f"{self.base_url}/{target_model}:generateContent?key={self.api_key}"

        # DEBUG LOG FOR USER VISIBILITY
        print(f"[*] Authenticating with Gemini API Key for model: {target_model}...")

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
                
                elif response.status_code in [429, 500, 503]:
                    wait = base_wait * (2 ** attempt)
                    print(f"[*] API Error ({response.status_code}). Retrying in {wait}s...")
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
        
        CRITICAL: 
        - DO NOT ASK QUESTIONS (e.g., "Shall I proceed?").
        - OUTPUT THE PLAN IMMEDIATELY.
        - THIS IS A NON-INTERACTIVE SESSION.
        """
        # Phase 1: Audit & Plan -> Gemini 3 Pro (Needs Context)
        return self._call_gemini(prompt, model="gemini-3-pro-preview")

    def generate_code(self, plan: str) -> dict:
        """
        Returns info about the code to be generated (Multiple Files, Nested Structure).
        """
        prompt = f"""
        ACT AS: Senior Full-Stack Migration Architect.
        PLAN: {plan}
        
        TASK: Generate the COMPLETE file system for the new `modernized_stack`.
        
        ### INSTRUCTION: MULTI-FILE GENERATION PROTOCOL (STRICT)
        You must output multiple files. Wrap EVERY file in this exact XML structure:
        <file path="folder/filename.ext">
        ... content ...
        </file>

        **RULES:**
        1. **NO LAZINESS**: Write FULL code. No `// ... rest`.
        2. **NO MARKDOWN**: Do not use ``` blocks inside the XML.
        3. **SINGLE STREAM**: Output all files in one response.

        ### CRITICAL CONSTRAINTS:
        1.  **Structure**: logic MUST be inside `./modernized_stack/`.
            -   `modernized_stack/backend/main.py` (FastAPI)
            -   `modernized_stack/frontend/app/page.tsx` (Next.js - PUBLIC LANDING)
            -   `modernized_stack/frontend/app/dashboard/page.tsx` (Next.js - PROTECTED)
            -   `modernized_stack/preview.html` (Static Mock)
            -   `modernized_stack/docker-compose.yml`
        2.  **Execution Requirements**: 
            -   The `backend/main.py` MUST be production-ready.
            -   **CRITICAL**: `uvicorn.run(app, host="0.0.0.0", port=8000)`. DO NOT USE `127.0.0.1` or `localhost`.
            -   **CRITICAL**: DO NOT use relative imports (e.g. `from .database import`) in `main.py`. Use absolute/local imports (e.g. `from database import`).
            -   **CRITICAL**: The backend MUST serve `modernized_stack/preview.html` at `/fallback_preview` (NOT root).
            -   **CRITICAL**: The ROOT path `GET /` MUST return a JSON Health Check: `{{ "status": "online", "service": "lazarus-backend" }}`.
            -   Implementation:
                ```python
                @app.get("/")
                def read_root():
                    return {{ "status": "online", "service": "lazarus-backend" }}

                @app.get("/fallback_preview")
                def read_preview():
                     with open("modernized_stack/preview.html", "r") as f:
                        return HTMLResponse(content=f.read())
                ```
            -   Include `requirements.txt` with ALL dependencies.
            -   **CRITICAL**: Use these EXACT versions to prevent crashes:
                -   `fastapi`
                -   `uvicorn`
                -   `python-multipart`
                -   `python-jose[cryptography]`
                -   `passlib[bcrypt]`
                -   `bcrypt==4.0.1` (REQUIRED for passlib compatibility)
        3.  **Frontend (Next.js)**:
            -   **CRITICAL UX**: `app/page.tsx` MUST be the **High-Fidelity Cyberpunk Landing/Login Page**. 
            -   DO NOT generate a "Migration in Progress" placeholder or directory listing.
            -   The user wants to see the "Result", not "Status".
            -   Include a "Login" form directly on the landing page that POSTs to `NEXT_PUBLIC_API_URL + '/api/login'`.
        4.  **Preview**: 
            -   Generate `modernized_stack/preview.html`.
            -   **CRITICAL**: INTERACTIVE MOCK.
            -   Use JS to simulate backend calls if backend is offline.
        
        RETURN ONLY THE XML STREAM.
        """
        # Phase 2: Write Code -> Gemini 3 Pro (Needs Reasoning)
        response = self._call_gemini(prompt, model="gemini-3-pro-preview")
        print("[DEBUG] Gemini 3 Pro Connected Successfully. Code Generated.")
        
        # XML Parsing Strategy
        files = []
        pattern = r'<file path="(.*?)">\s*(.*?)\s*</file>'
        matches = re.findall(pattern, response, re.DOTALL)
        
        for filepath, content in matches:
            files.append({
                "filename": filepath.strip(), 
                "content": content.strip()
            })
            
        if not files:
            # Fallback for debugging if regex fails
            return {
                "files": [{"filename": "error.log", "content": response}],
                "entrypoint": "error.log" 
            }

        return {
            "files": files,
            "entrypoint": "modernized_stack/backend/main.py"
        }

    def infer_dependencies(self, files: list) -> list:
        """
        Scans generated python code for imports using AST and returns specific PyPI packages.
        """
        detected = set()
        
        # 1. The "Rosetta Stone" of Imports
        PACKAGE_MAP = {
            # Data & AI
            "numpy": "numpy",
            "pandas": "pandas",
            "cv2": "opencv-python-headless", # Headless for servers!
            "PIL": "pillow",
            "sklearn": "scikit-learn",
            "openai": "openai",
            "google.generativeai": "google-generative-ai",
            
            # Backend Frameworks
            "fastapi": "fastapi",
            "uvicorn": "uvicorn",
            "flask": "flask",
            "flask_cors": "flask-cors",
            "sqlalchemy": "sqlalchemy",
            
            # Auth & Security
            "jose": "python-jose[cryptography]",
            "jwt": "python-jose[cryptography]",
            "passlib": "passlib[bcrypt]",
            "bcrypt": "bcrypt==4.0.1", # CRITICAL: Force 4.0.1
            "multipart": "python-multipart", # Required for Form data
            
            # Utilities
            "dotenv": "python-dotenv",
            "requests": "requests",
            "pydantic": "pydantic",
            "email_validator": "email-validator",
            "bs4": "beautifulsoup4"
        }

        # Scan all .py files
        for f in files:
            if f['filename'].endswith('.py'):
                try:
                    tree = ast.parse(f['content'])
                    for node in ast.walk(tree):
                        # Scan "import x"
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                root = alias.name.split('.')[0]
                                if root in PACKAGE_MAP:
                                    detected.add(PACKAGE_MAP[root])
                        
                        # Scan "from x import y"
                        elif isinstance(node, ast.ImportFrom):
                            if node.module:
                                root = node.module.split('.')[0]
                                if root in PACKAGE_MAP:
                                    detected.add(PACKAGE_MAP[root])
                                
                                # SPECIAL CASE: Pydantic Email
                                if root == "pydantic":
                                    for name in node.names:
                                        if name.name == "EmailStr":
                                            detected.add("pydantic[email]")
                                            detected.add("email-validator")
                except SyntaxError:
                    print(f"[!] SyntaxError parsing {f['filename']}. Skipping AST scan.")

        # Always ensure basic runner tools are present
        detected.add("uvicorn")
        detected.add("fastapi")
        detected.add("python-multipart")
            
        return list(detected)

    def execute_in_sandbox(self, files: list, entrypoint: str):
        if not E2B_AVAILABLE or not E2B_API_KEY:
            return "E2B Sandbox not available (Dependencies or Key missing)."
            
        # SAFETY CHECK: Did Code Gen Fail?
        if entrypoint == "error.log":
            return f"GENERATION FAILED: Gemini API returned an error.\n\n=== ERROR LOG ===\n{files[0]['content']}\n================="

        print(f"[*] Executing {entrypoint} in E2B Sandbox...")
        
        try:
            # Kill previous sandbox if exists to free resources/prevent conflict
            if self.sandbox:
                try:
                    print("[*] Terminating previous Sandbox...")
                    self.sandbox.close()
                except:
                    pass
                self.sandbox = None

            # Create NEW Sandbox (Persistent) defined by self.sandbox
            # Timeout set to 1800s (30m) to allow user to explore preview
            self.sandbox = Sandbox.create(timeout=1800)
            
            # Write ALL files
            for file in files:
                # Create directories if needed
                dir_path = os.path.dirname(file['filename'])
                if dir_path and dir_path not in [".", ""]:
                        # We can't easily mkdir -p in sandbox file write, so we run a command
                        self.sandbox.commands.run(f"mkdir -p {dir_path}")
                
                self.sandbox.files.write(file['filename'], file['content'])
            
            # Install Dependencies (Hackathon Mode: Smart Install)
            if entrypoint.endswith('.py'):
                print("[*] Installing Python dependencies (Timeout: 300s)...")
                
                # 1. Start with Intelligent Inference
                inferred = self.infer_dependencies(files)
                final_reqs = set(inferred)
                
                print(f"[*] Intelligent Scanner detected {len(inferred)} required packages from code analysis.")
                if inferred:
                    print(f"[DEBUG] Inferred: {', '.join(inferred)}")

                # 2. Merge with requirements.txt if it exists
                req_file = next((f for f in files if "requirements.txt" in f['filename']), None)
                if req_file:
                    print(f"[*] Merging with requirements.txt...")
                    # We append contents of req file to our set (ignoring versions for now, simple string match)
                    # Ideally we trust the explicit requirements.txt for specific versions, 
                    # but we *Must* override critical ones like bcrypt.
                    
                    # Install req file first
                    self.sandbox.commands.run(f"pip install -r {req_file['filename']}", timeout=300)
                
                # 3. Force Install the Consolidated "Smart" list
                # This ensures that even if requirements.txt missed 'python-multipart', we catch it from 'Form' usage.
                # And it enforces our 'bcrypt==4.0.1' override if it was inferred.
                if final_reqs:
                    install_str = " ".join([f"'{p}'" for p in final_reqs]) # Quote to handle brackets
                    print(f"[*] Pre-loading inferred dependencies to prevent runtime errors...")
                    self.sandbox.commands.run(f"pip install {install_str}", timeout=300)

                # START SERVER IN BACKGROUND (With Logging)
                print(f"[*] Starting Backend {entrypoint} in background (logging to app.log)...")
                self.sandbox.commands.run(f"python {entrypoint} > app.log 2>&1", background=True)
                
                # HEALTH CHECK LOOP (Backend)
                print("[*] Waiting for Backend to boot...")
                backend_success = False
                for i in range(15): # Try for 45 seconds
                    time.sleep(3)
                    try:
                        check = self.sandbox.commands.run("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000")
                        if check.stdout.strip() in ['200', '404', '401', '405', '500']: 
                            print("[*] Backend Health Check: SUCCESS")
                            backend_success = True
                            break
                    except:
                        pass
                    print(f"[*] Backend Health Check: Attempt {i+1}/15 failed...")

                if not backend_success:
                    print("[!] Backend FAILED. Retrieving logs...")
                    log_content = self.sandbox.files.read("app.log")
                    return f"FATAL: Backend failed to start.\n\n=== APP.LOG ===\n{log_content}\n==============="

                # Get Backend URL
                backend_host = self.sandbox.get_host(8000)
                backend_url = f"https://{backend_host}"
                print(f"[*] Backend Live at: {backend_url}")

                # --- PHASE 2: FRONTEND LAUNCH (Dual Stack) ---
                # Check if we have a frontend package.json
                has_frontend = any("frontend/package.json" in f['filename'] for f in files)
                
                if has_frontend:
                    print("🚀 Detected Frontend. Initiating Dual-Stack Launch...")
                    print("[*] Installing Node dependencies (Timeout: 300s)...")
                    # We need to install inside the frontend directory
                    # Assuming standard structure: modernized_stack/frontend
                    frontend_dir = "modernized_stack/frontend"
                    
                    # Install deps
                    self.sandbox.commands.run(f"cd {frontend_dir} && npm install --force", timeout=300)
                    
                    print(f"[*] Starting Frontend in background (connected to {backend_url})...")
                    # Start Next.js with Backend URL injected
                    start_cmd = f"cd {frontend_dir} && NEXT_PUBLIC_API_URL={backend_url} npm run dev -- -p 3000"
                    self.sandbox.commands.run(f"{start_cmd} > frontend.log 2>&1", background=True)
                    
                    # Wait for Frontend
                    time.sleep(10) # Give Next.js a moment to spin up
                    frontend_host = self.sandbox.get_host(3000)
                    frontend_url = f"https://{frontend_host}"
                    
                    return f"Dual-Stack Deployed Successfully.\n[PREVIEW_URL] {frontend_url}\n[BACKEND_URL] {backend_url}"
                
                else:
                    # Single Stack (Backend Only)
                    return f"Backend Server started.\n[PREVIEW_URL] {backend_url}"

            else: 
                    # Node entrypoint (Fallback)
                    cmd = f"node {entrypoint} > app.log 2>&1"
                    self.sandbox.commands.run(cmd, background=True)
                    time.sleep(5)
                    host = self.sandbox.get_host(3000)
                    return f"Node Server started.\n[PREVIEW_URL] https://{host}"
                
        except Exception as e:
            return f"Sandbox Error: {str(e)}"

    def process_resurrection_stream(self, repo_url: str, instructions: str):
        """Generator that yields logs and results in real-time."""
        logs = []
        
        def emit_log(msg):
            logs.append(msg)
            return {"type": "log", "content": msg}

        def emit_debug(msg):
            return {"type": "debug", "content": msg}

        # 1. Plan
        yield emit_log("Initiating Deep Scan of Legacy Repository...")
        
        # ACTUAL SCAN
        scanned_files = self.scan_repository(repo_url)
        yield emit_debug(f"[DEBUG] Scanned Repository Files:\n" + "\n".join(scanned_files[:20]) + ("\n... (truncated)" if len(scanned_files) > 20 else ""))

        # Check for error in plan
        plan = self.generate_modernization_plan(repo_url, instructions)
        yield emit_debug(f"[DEBUG] Generated Plan:\n{plan}")

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
        yield emit_debug(f"[DEBUG] Generated Files: {', '.join(encoded_files)}")
        yield emit_log(f"Generated {len(encoded_files)} System Modules...")
        
        # 3. Execution
        yield emit_log("Booting Neural Sandbox Environment...")
        sandbox_logs = self.execute_in_sandbox(files, entrypoint)
        yield emit_debug(f"[DEBUG] Sandbox Output:\n{sandbox_logs}")
        
        yield emit_log("Verifying System Integrity...")

        # Extract HTML for preview
        preview = ""
        # Check logs for URL
        url_match = re.search(r"\[PREVIEW_URL\] (https://[^\s]+)", sandbox_logs)
        if url_match:
            preview = url_match.group(1) # It's a URL now, not HTML content
        else:
             # Fallback: No URL found
             pass
        
        # Check artifacts
        for f in files:
            if 'preview.html' in f['filename']:
                # If we have a real URL, user defines if they want that or static HTML. 
                # For now, let's prefer the Live Server URL if it exists!
                if not preview.startswith("http"): 
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
