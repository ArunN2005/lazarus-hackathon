import os
import json
import re
import requests
import time
import ast
from simple_env import load_env
from prompts import get_code_generation_prompt

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

def sanitize_path(path: str) -> str:
    """
    Sanitizes file paths to be safe for bash shell commands.
    Removes characters that break mkdir and other shell commands.
    """
    if not path:
        return path
    
    # Replace problematic characters
    replacements = {
        '(': '',  # Remove parentheses - causes subshell
        ')': '',
        '[': '',  # Remove brackets - causes glob
        ']': '',
        '{': '',  # Remove braces - causes expansion
        '}': '',
        '@': '',  # Remove @ - causes issues
        '#': '',  # Remove # - causes comments
        '$': '',  # Remove $ - causes variable expansion
        '&': '',  # Remove & - causes background
        '*': '',  # Remove * - causes glob
        '?': '',  # Remove ? - causes glob
        '!': '',  # Remove ! - causes history expansion
        '|': '',  # Remove | - causes pipe
        ';': '',  # Remove ; - causes command separator
        '<': '',  # Remove < - causes redirect
        '>': '',  # Remove > - causes redirect
        '`': '',  # Remove ` - causes command substitution
        "'": '',  # Remove ' - causes quoting issues
        '"': '',  # Remove " - causes quoting issues
        ' ': '_',  # Replace spaces with underscores
    }
    
    result = path
    for char, replacement in replacements.items():
        result = result.replace(char, replacement)
    
    # Remove any double underscores
    while '__' in result:
        result = result.replace('__', '_')
    
    # Remove any double slashes
    while '//' in result:
        result = result.replace('//', '/')
    
    return result

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
                # 4. Create Pull Request
                print(f"[*] File committed. Creating Pull Request...")
                
                # Check if PR already exists
                pr_check_resp = requests.get(
                    f"{base_api}/pulls",
                    headers=headers,
                    params={"head": f"{owner}:{target_branch}", "base": "main", "state": "open"}
                )
                
                if pr_check_resp.status_code == 200 and len(pr_check_resp.json()) > 0:
                    # PR already exists, return its URL
                    existing_pr = pr_check_resp.json()[0]
                    return {
                        "status": "success", 
                        "commit_url": existing_pr['html_url'],
                        "message": f"Pull Request already exists. Check it on GitHub."
                    }
                
                # Create new PR
                pr_data = {
                    "title": "🧬 Lazarus Resurrection - Modernized Codebase",
                    "body": "## 🦾 Automated Resurrection by Lazarus Engine\n\nThis PR contains the modernized version of your legacy codebase.\n\n### Changes:\n- ✅ Modern FastAPI backend with CORS, validation, and JWT auth\n- ✅ Next.js 15 frontend with Tailwind CSS\n- ✅ Production-ready code with error handling\n- ✅ Docker Compose for easy deployment\n\n---\n*Generated by [Lazarus Engine](https://github.com/ArunN2005/lazarus-hackathon)*",
                    "head": target_branch,
                    "base": "main"
                }
                
                pr_resp = requests.post(f"{base_api}/pulls", headers=headers, json=pr_data)
                
                if pr_resp.status_code == 201:
                    pr_url = pr_resp.json()['html_url']
                    pr_number = pr_resp.json()['number']
                    return {
                        "status": "success", 
                        "commit_url": pr_url,
                        "message": f"Pull Request #{pr_number} created successfully! Check it on GitHub."
                    }
                elif pr_resp.status_code == 422:
                    # PR might already exist or no changes
                    compare_url = f"https://github.com/{owner}/{repo_name}/compare/main...{target_branch}?expand=1"
                    return {
                        "status": "success", 
                        "commit_url": compare_url,
                        "message": f"Files committed to {target_branch}. Create PR manually or check existing PRs."
                    }
                else:
                    compare_url = f"https://github.com/{owner}/{repo_name}/compare/main...{target_branch}?expand=1"
                    return {
                        "status": "success", 
                        "commit_url": compare_url,
                        "message": f"Files committed. PR creation failed: {pr_resp.text[:100]}"
                    }
            else:
                return {"status": "error", "message": f"GitHub API Error: {put_resp.text}"}

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def commit_all_files_to_github(self, repo_url: str, files: list) -> dict:
        """
        Commits ALL files to a 'lazarus-resurrection' branch and creates a PR.
        files: list of {"filename": str, "content": str}
        """
        if not self.github_token:
            return {"status": "error", "message": "GITHUB_TOKEN is missing."}

        try:
            import base64
            
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

            print(f"[*] Creating PR for {len(files)} files...")

            # 1. Get the base branch (try main, then master)
            base_branch = "main"
            main_resp = requests.get(f"{base_api}/git/ref/heads/main", headers=headers)
            if main_resp.status_code != 200:
                main_resp = requests.get(f"{base_api}/git/ref/heads/master", headers=headers)
                base_branch = "master"
                if main_resp.status_code != 200:
                    return {"status": "error", "message": "Could not find main or master branch."}
            
            base_sha = main_resp.json()['object']['sha']

            # 2. Create or update the target branch
            branch_resp = requests.get(f"{base_api}/git/ref/heads/{target_branch}", headers=headers)
            
            if branch_resp.status_code == 404:
                print(f"[*] Creating branch '{target_branch}'...")
                create_resp = requests.post(
                    f"{base_api}/git/refs",
                    headers=headers,
                    json={"ref": f"refs/heads/{target_branch}", "sha": base_sha}
                )
                if create_resp.status_code != 201:
                    return {"status": "error", "message": f"Failed to create branch: {create_resp.text}"}
            else:
                # Update existing branch to latest base
                print(f"[*] Updating branch '{target_branch}'...")
                requests.patch(
                    f"{base_api}/git/refs/heads/{target_branch}",
                    headers=headers,
                    json={"sha": base_sha, "force": True}
                )

            # 3. Get the base tree
            base_commit_resp = requests.get(f"{base_api}/git/commits/{base_sha}", headers=headers)
            base_tree_sha = base_commit_resp.json()['tree']['sha']

            # 4. Create blobs for each file
            tree_items = []
            for f in files:
                content_bytes = f['content'].encode('utf-8')
                base64_content = base64.b64encode(content_bytes).decode('utf-8')
                
                blob_resp = requests.post(
                    f"{base_api}/git/blobs",
                    headers=headers,
                    json={"content": base64_content, "encoding": "base64"}
                )
                
                if blob_resp.status_code == 201:
                    blob_sha = blob_resp.json()['sha']
                    tree_items.append({
                        "path": f['filename'],
                        "mode": "100644",
                        "type": "blob",
                        "sha": blob_sha
                    })
                    print(f"  [+] Staged: {f['filename']}")
                else:
                    print(f"  [!] Failed to create blob for {f['filename']}")

            if not tree_items:
                return {"status": "error", "message": "No files were staged."}

            # 5. Create a new tree
            tree_resp = requests.post(
                f"{base_api}/git/trees",
                headers=headers,
                json={"base_tree": base_tree_sha, "tree": tree_items}
            )
            
            if tree_resp.status_code != 201:
                return {"status": "error", "message": f"Failed to create tree: {tree_resp.text}"}
            
            new_tree_sha = tree_resp.json()['sha']

            # 6. Create a commit
            commit_resp = requests.post(
                f"{base_api}/git/commits",
                headers=headers,
                json={
                    "message": f"🧬 Lazarus Resurrection: Modernized {len(files)} files",
                    "tree": new_tree_sha,
                    "parents": [base_sha]
                }
            )
            
            if commit_resp.status_code != 201:
                return {"status": "error", "message": f"Failed to create commit: {commit_resp.text}"}
            
            new_commit_sha = commit_resp.json()['sha']
            print(f"[*] Created commit: {new_commit_sha[:7]}")

            # 7. Update the branch reference
            update_resp = requests.patch(
                f"{base_api}/git/refs/heads/{target_branch}",
                headers=headers,
                json={"sha": new_commit_sha}
            )
            
            if update_resp.status_code != 200:
                return {"status": "error", "message": f"Failed to update branch: {update_resp.text}"}

            # 8. Check if PR already exists
            pr_check_resp = requests.get(
                f"{base_api}/pulls",
                headers=headers,
                params={"head": f"{owner}:{target_branch}", "base": base_branch, "state": "open"}
            )
            
            if pr_check_resp.status_code == 200 and len(pr_check_resp.json()) > 0:
                existing_pr = pr_check_resp.json()[0]
                return {
                    "status": "success", 
                    "pr_url": existing_pr['html_url'],
                    "message": f"Pull Request updated with {len(files)} files. Check it on GitHub!"
                }

            # 9. Create new PR
            pr_data = {
                "title": "🧬 Lazarus Resurrection - Modernized Codebase",
                "body": f"""## 🦾 Automated Resurrection by Lazarus Engine

This PR contains the **completely modernized** version of your legacy codebase.

### 📁 Files Changed ({len(files)} files)
{chr(10).join([f"- `{f['filename']}`" for f in files[:20]])}
{"..." if len(files) > 20 else ""}

### ✨ What's Included
- ✅ Modern FastAPI backend with CORS and validation
- ✅ Next.js 15 frontend with Tailwind CSS
- ✅ Production-ready code with error handling
- ✅ Docker Compose for deployment  
- ✅ TypeScript types and Pydantic models

---
*Generated by [Lazarus Engine](https://github.com/ArunN2005/lazarus-hackathon) 🧬*""",
                "head": target_branch,
                "base": base_branch
            }
            
            pr_resp = requests.post(f"{base_api}/pulls", headers=headers, json=pr_data)
            
            if pr_resp.status_code == 201:
                pr_url = pr_resp.json()['html_url']
                pr_number = pr_resp.json()['number']
                print(f"[*] Pull Request #{pr_number} created!")
                return {
                    "status": "success", 
                    "pr_url": pr_url,
                    "message": f"Pull Request #{pr_number} created with {len(files)} files!"
                }
            else:
                compare_url = f"https://github.com/{owner}/{repo_name}/compare/{base_branch}...{target_branch}?expand=1"
                return {
                    "status": "success", 
                    "pr_url": compare_url,
                    "message": f"Files committed. Create PR manually: {pr_resp.text[:100]}"
                }

        except Exception as e:
            print(f"[!] PR Creation Error: {str(e)}")
            return {"status": "error", "message": str(e)}

    def scan_repository(self, repo_url: str) -> list:
        """ Fetches the file tree of the remote repository using GitHub API. """
        try:
            # Parse owner/repo
            match = re.search(r"github\.com/([^/]+)/([^/.]+)", repo_url)
            if not match:
                return ["(Invalid URL - Simulating Scan)"]
            
            owner, repo_name = match.groups()
            
            # Try both 'main' and 'master' branches
            branches = ['main', 'master']
            
            headers = {"Accept": "application/vnd.github.v3+json"}
            if self.github_token:
                headers["Authorization"] = f"token {self.github_token}"
            
            for branch in branches:
                api_url = f"https://api.github.com/repos/{owner}/{repo_name}/git/trees/{branch}?recursive=1"
                
                resp = requests.get(api_url, headers=headers)
                if resp.status_code == 200:
                    tree = resp.json().get('tree', [])
                    # Return list of paths
                    return [item['path'] for item in tree if item['type'] == 'blob']
            
            # If both branches failed, try to get default branch from repo info
            repo_api_url = f"https://api.github.com/repos/{owner}/{repo_name}"
            repo_resp = requests.get(repo_api_url, headers=headers)
            if repo_resp.status_code == 200:
                default_branch = repo_resp.json().get('default_branch', 'main')
                api_url = f"https://api.github.com/repos/{owner}/{repo_name}/git/trees/{default_branch}?recursive=1"
                resp = requests.get(api_url, headers=headers)
                if resp.status_code == 200:
                    tree = resp.json().get('tree', [])
                    return [item['path'] for item in tree if item['type'] == 'blob']
            
            return [f"(API Error - Could not find repository or branch)"]
                 
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
        ACT AS: Elite Full-Stack Architect & AI Systems Engineer.
        PROJECT: "Lazarus Engine" - Autonomous Code Resurrection System.

        CONTEXT:
        - Legacy Repository: {repo_url}
        - User Preferences: "{instructions if instructions else 'Modern, production-ready stack'}"

        YOUR MISSION:
        Architect a complete, production-grade replacement that RESPECTS USER PREFERENCES while maintaining best practices.

        ### STEP 1: PREFERENCE ANALYSIS (CRITICAL)
        Analyze the user's preferences and extract:
        1. **Design Preferences**: Color schemes, UI style (e.g., "dark mode", "minimalist", "cyberpunk")
        2. **Feature Requirements**: Specific functionality they want (e.g., "authentication", "dashboard", "real-time updates")
        3. **Tech Stack Preferences**: Any mentioned frameworks or libraries
        4. **Performance Requirements**: Speed, scalability needs
        
        If user preferences are vague, infer intelligent defaults based on modern best practices.

        ### STEP 2: LEGACY CONTRACT AUDIT
        Based on the repository structure, identify:
        - Likely API endpoints (e.g., `/api/login`, `/api/users`)
        - Data models and schemas
        - Authentication patterns
        - Frontend routes and pages
        
        **Constraint**: New system MUST maintain API compatibility for zero-downtime migration.

        ### STEP 3: ARCHITECTURE DESIGN (Preference-Driven)
        
        **Backend Strategy**:
        - Stack: Python FastAPI (high performance, modern async)
        - Authentication: JWT tokens with secure password hashing
        - Database: SQLite for prototyping (easily upgradable to PostgreSQL)
        - API Design: RESTful with automatic OpenAPI docs
        - **Apply user preferences**: If they want specific features, plan the endpoints
        
        **Frontend Strategy**:
        - Stack: Next.js 15 (App Router) with TypeScript
        - Styling: Tailwind CSS with custom design system
        - **Apply user preferences**: 
          * Use their color scheme in Tailwind config
          * Match their desired UI style (glassmorphism, neumorphism, etc.)
          * Implement requested features (dashboards, charts, forms)
        - State Management: React hooks (simple, effective)
        - API Integration: Environment-based URLs for flexibility

        ### STEP 4: INTEGRATION PLANNING
        - CORS: Wildcard origins for sandbox compatibility
        - Environment Variables: `NEXT_PUBLIC_API_URL` for dynamic backend connection
        - Build Process: Production builds for optimal performance
        - Error Handling: Graceful fallbacks and user-friendly messages

        ### STEP 5: QUALITY ASSURANCE
        Plan for:
        - Type safety (TypeScript, Pydantic)
        - Input validation on both frontend and backend
        - Secure authentication flow
        - Responsive design (mobile-first)
        - Performance optimization (code splitting, lazy loading)

        OUTPUT FORMAT:
        Provide a detailed architectural plan in this structure:
        
        **USER PREFERENCES INTERPRETATION**:
        [Explain how you interpreted their preferences]
        
        **BACKEND ARCHITECTURE**:
        - Endpoints: [List all planned API routes]
        - Models: [Data structures]
        - Security: [Auth strategy]
        
        **FRONTEND ARCHITECTURE**:
        - Pages: [All routes and their purpose]
        - Components: [Key reusable components]
        - Design System: [Colors, typography, spacing based on user preferences]
        
        **INTEGRATION STRATEGY**:
        [How frontend and backend connect]
        
        CRITICAL RULES:
        - DO NOT ask questions or wait for approval
        - OUTPUT the complete plan immediately
        - RESPECT user preferences while maintaining quality
        - Be specific and actionable
        """
        # Use Gemini 3 Pro for complex reasoning
        return self._call_gemini(prompt, model="gemini-3-pro-preview")

    def generate_code(self, plan: str) -> dict:
        """
        Returns info about the code to be generated (Multiple Files, Nested Structure).
        Uses comprehensive prompt from prompts.py module.
        """
        # Get the comprehensive prompt from the prompts module
        prompt = get_code_generation_prompt(plan)
        
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
            # AGGRESSIVE CLEANUP: Kill previous sandbox if exists
            if self.sandbox:
                try:
                    print("[*] Terminating previous Sandbox...")
                    self.sandbox.close()
                    print("[*] Previous Sandbox terminated successfully.")
                except Exception as e:
                    print(f"[*] Sandbox cleanup warning: {str(e)[:100]}")
                finally:
                    self.sandbox = None

            # Create NEW Sandbox (Persistent) defined by self.sandbox
            # Timeout set to 1800s (30m) to allow user to explore preview
            print("[*] Creating new E2B Sandbox (30min timeout)...")
            self.sandbox = Sandbox.create(timeout=1800)
            print(f"[*] Sandbox created successfully. ID: {self.sandbox.id if hasattr(self.sandbox, 'id') else 'N/A'}")
            
            # Write ALL files (with path sanitization for bash compatibility)
            for file in files:
                # Sanitize the filename to prevent bash shell issues
                safe_filename = sanitize_path(file['filename'])
                
                # Log if path was modified
                if safe_filename != file['filename']:
                    print(f"  [!] Path sanitized: {file['filename']} -> {safe_filename}")
                
                # Create directories if needed
                dir_path = os.path.dirname(safe_filename)
                if dir_path and dir_path not in [".", ""]:
                    try:
                        # We can't easily mkdir -p in sandbox file write, so we run a command
                        mkdir_result = self.sandbox.commands.run(f"mkdir -p '{dir_path}'")
                        if mkdir_result.exit_code != 0:
                            print(f"  [!] mkdir warning for {dir_path}: {mkdir_result.stderr}")
                    except Exception as mkdir_err:
                        print(f"  [!] mkdir failed for {dir_path}: {mkdir_err}")
                        # Try alternative - just continue, file write might still work
                        pass
                
                try:
                    self.sandbox.files.write(safe_filename, file['content'])
                except Exception as write_err:
                    print(f"  [!] File write error for {safe_filename}: {write_err}")
            
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
                
                # 4. CRITICAL: Force bcrypt==4.0.1 to prevent version compatibility errors
                print(f"[*] Enforcing bcrypt==4.0.1 (compatibility fix)...")
                self.sandbox.commands.run("pip install --force-reinstall bcrypt==4.0.1", timeout=60)

                # START SERVER IN BACKGROUND (With Logging)
                print(f"[*] Starting Backend {entrypoint} in background (logging to app.log)...")
                self.sandbox.commands.run(f"python {entrypoint} > app.log 2>&1", background=True)
                
                # HEALTH CHECK LOOP (Backend)
                print("[*] Waiting for Backend to boot...")
                backend_success = False
                for i in range(20): # Try for 60 seconds (increased from 45)
                    time.sleep(3)
                    try:
                        # Use Python instead of curl (curl may not be installed)
                        # Note: urlopen throws HTTPError for 4xx/5xx, so we catch it
                        check_script = """
import urllib.request
import urllib.error
try:
    response = urllib.request.urlopen('http://127.0.0.1:8000', timeout=2)
    print(response.status)
except urllib.error.HTTPError as e:
    print(e.code)
except Exception as e:
    print('error')
"""
                        check = self.sandbox.commands.run(f"python -c \"{check_script}\"")
                        status_code = check.stdout.strip()
                        print(f"[*] Backend Health Check {i+1}/20: HTTP {status_code if status_code and status_code != 'error' else 'No Response'}")
                        
                        # Accept any valid HTTP response (200, 404, etc.) as success
                        if status_code and status_code.isdigit() and int(status_code) < 600: 
                            print(f"[*] Backend Health Check: SUCCESS ✓ (HTTP {status_code})")
                            backend_success = True
                            break
                    except Exception as e:
                        print(f"[*] Backend Health Check {i+1}/20: Exception - {str(e)[:50]}")
                        pass
                    
                    # Early log check after 5 attempts to diagnose issues faster
                    if i == 4:
                        try:
                            early_log = self.sandbox.files.read("app.log")
                            if early_log and len(early_log) > 10:
                                print(f"[DEBUG] Early Log Check (Backend may have crashed):\n{early_log[:300]}")
                        except:
                            pass

                if not backend_success:
                    print("[!] Backend FAILED to start. Retrieving logs...")
                    try:
                        log_content = self.sandbox.files.read("app.log")
                        print(f"[DEBUG] App Log Preview:\n{log_content[:500]}")
                    except:
                        log_content = "Could not read app.log"
                    return f"FATAL: Backend failed to start after 60 seconds.\\n\\n=== APP.LOG ===\\n{log_content}\\n==============="

                # Get Backend URL
                backend_host = self.sandbox.get_host(8000)
                backend_url = f"https://{backend_host}"
                print(f"[*] Backend Live at: {backend_url}")

                # --- PHASE 2: FRONTEND LAUNCH (Dual Stack) ---
                # Check if we have a frontend package.json
                has_frontend = any("frontend/package.json" in f['filename'] for f in files)
                
                if has_frontend:
                    print("🚀 Detected Frontend. Initiating Dual-Stack Launch...")
                    frontend_dir = "modernized_stack/frontend"
                    
                    # CRITICAL: Create .env.local with backend URL BEFORE building
                    # Next.js bakes env vars at build time, not runtime
                    print(f"[*] Injecting Backend URL into .env.local...")
                    env_content = f"NEXT_PUBLIC_API_URL={backend_url}\n"
                    self.sandbox.files.write(f"{frontend_dir}/.env.local", env_content)
                    print(f"[DEBUG] Created .env.local with: NEXT_PUBLIC_API_URL={backend_url}")
                    
                    print("[*] Installing Node dependencies (Timeout: 300s)...")
                    self.sandbox.commands.run(f"cd {frontend_dir} && npm install --force", timeout=300)
                    
                    print(f"[*] Building Frontend for production (Backend URL: {backend_url})...")
                    # Now the build will include the backend URL
                    build_result = self.sandbox.commands.run(f"cd {frontend_dir} && npm run build", timeout=300)
                    
                    # Check for build errors
                    if build_result.exit_code != 0:
                        error_output = build_result.stderr + build_result.stdout
                        print(f"[!] Frontend build failed. Error output:\n{error_output[:500]}")
                        
                        # Return error with context for potential retry
                        return f"FRONTEND BUILD FAILED:\\n\\n{error_output}\\n\\nThis error will trigger automatic code regeneration."
                    
                    print(f"[*] Starting Frontend in production mode...")
                    # Start production server (API URL already baked into build)
                    start_cmd = f"cd {frontend_dir} && npm start -- -p 3000"
                    self.sandbox.commands.run(f"{start_cmd} > frontend.log 2>&1", background=True)
                    
                    # Wait for Frontend
                    time.sleep(10) # Give Next.js a moment to spin up
                    frontend_host = self.sandbox.get_host(3000)
                    frontend_url = f"https://{frontend_host}"
                    
                    print(f"[*] Frontend Live at: {frontend_url}")
                    print(f"[*] Frontend → Backend Connection: {backend_url}")
                    
                    return f"Dual-Stack Deployed Successfully.\\n[PREVIEW_URL] {frontend_url}\\n[BACKEND_URL] {backend_url}"
                
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
             fallback_mode = True
        else:
             fallback_mode = False
             
        yield emit_log("Architecting Resurrection Blueprint...")

        # 2. Code Gen with Auto-Retry
        max_retries = 2
        retry_count = 0
        sandbox_logs = None
        files = []
        entrypoint = 'modernized_stack/backend/main.py'
        
        while retry_count <= max_retries:
            if retry_count > 0:
                yield emit_log(f"Auto-Healing: Regenerating code (Attempt {retry_count + 1}/{max_retries + 1})...")
                # Add error context to plan for retry
                error_context = f"\n\nPREVIOUS BUILD ERROR:\n{sandbox_logs}\n\nFIX THE ABOVE ERROR. Pay special attention to TypeScript syntax (use 'string' not 'str', 'number' not 'int')."
                plan_with_error = plan + error_context
                code_data = self.generate_code(plan_with_error)
            else:
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
            
            # Check if build failed
            if "FRONTEND BUILD FAILED" in sandbox_logs or "GENERATION FAILED" in sandbox_logs:
                if retry_count < max_retries:
                    yield emit_log(f"Build Error Detected. Initiating Auto-Heal...")
                    retry_count += 1
                    continue  # Retry
                else:
                    yield emit_log("Auto-Heal Failed. Manual intervention required.")
                    break
            else:
                # Success!
                yield emit_log("Verifying System Integrity...")
                break
        
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
        if fallback_mode or "Sandbox Error" in sandbox_logs or "BUILD FAILED" in sandbox_logs:
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

def commit_all_files(repo_url, files):
    """Commits ALL files and creates a PR in one action."""
    return engine.commit_all_files_to_github(repo_url, files)
