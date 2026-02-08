import os
import json
import re
import requests
import time
import ast
from simple_env import load_env
from prompts import get_code_generation_prompt
from resurrection_memory import (
    load_memory, record_attempt_start, record_failure, 
    record_success, record_dependency_issue, record_decision,
    get_memory_context_for_prompt, get_memory_summary
)

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

    def scan_repository_deep(self, repo_url: str) -> dict:
        """
        DEEP SCAN: Fetches ALL file CONTENTS, not just paths.
        This is the foundation of preservation-first architecture.
        
        Returns: {
            "files": [{"path": str, "content": str, "language": str}],
            "tech_stack": {...},
            "database": {...},
            "must_preserve": [...],
            "can_modernize": [...]
        }
        """
        import base64
        
        result = {
            "files": [],
            "tech_stack": {
                "backend": {"framework": None, "database": None, "auth": None},
                "frontend": {"framework": None, "styling": None},
            },
            "must_preserve": [],
            "can_modernize": [],
            "env_vars": [],
            "api_endpoints": [],
            "database_schemas": []
        }
        
        try:
            # Parse owner/repo
            match = re.search(r"github\.com/([^/]+)/([^/.]+)", repo_url)
            if not match:
                return result
            
            owner, repo_name = match.groups()
            
            headers = {"Accept": "application/vnd.github.v3+json"}
            if self.github_token:
                headers["Authorization"] = f"token {self.github_token}"
            
            # Get default branch
            repo_resp = requests.get(f"https://api.github.com/repos/{owner}/{repo_name}", headers=headers)
            default_branch = "main"
            if repo_resp.status_code == 200:
                default_branch = repo_resp.json().get('default_branch', 'main')
            
            # Get file tree
            tree_url = f"https://api.github.com/repos/{owner}/{repo_name}/git/trees/{default_branch}?recursive=1"
            tree_resp = requests.get(tree_url, headers=headers)
            
            if tree_resp.status_code != 200:
                print(f"[!] Failed to get repository tree: {tree_resp.status_code}")
                return result
            
            tree = tree_resp.json().get('tree', [])
            
            # File extensions to fetch content for
            code_extensions = {
                '.py', '.js', '.ts', '.tsx', '.jsx', '.json', '.yaml', '.yml',
                '.html', '.css', '.scss', '.md', '.txt', '.env', '.env.example',
                '.toml', '.cfg', '.ini', '.sql', '.prisma', '.graphql'
            }
            
            # Files to always fetch
            important_files = {
                'package.json', 'requirements.txt', 'Pipfile', 'pyproject.toml',
                'docker-compose.yml', 'docker-compose.yaml', 'Dockerfile',
                '.env', '.env.example', '.env.local', 'config.py', 'settings.py',
                'schema.prisma', 'models.py', 'schemas.py', 'database.py'
            }
            
            print(f"[*] Deep scanning {len(tree)} files in repository...")
            files_fetched = 0
            # NO LIMIT - Fetch ALL files! Gemini has a large context window.
            
            for item in tree:
                if item['type'] != 'blob':
                    continue
                    
                path = item['path']
                _, ext = os.path.splitext(path)
                filename = os.path.basename(path)
                
                # Check if we should fetch this file
                should_fetch = (
                    ext.lower() in code_extensions or
                    filename in important_files or
                    'model' in path.lower() or
                    'schema' in path.lower() or
                    'route' in path.lower() or
                    'api' in path.lower() or
                    'controller' in path.lower()
                )
                
                # Skip node_modules, venv, etc.
                skip_dirs = ['node_modules', 'venv', '.venv', '__pycache__', '.git', 'dist', 'build']
                if any(skip_dir in path for skip_dir in skip_dirs):
                    should_fetch = False
                
                if should_fetch:  # Fetch ALL files - no limit!
                    try:
                        # Fetch file content
                        content_url = f"https://api.github.com/repos/{owner}/{repo_name}/contents/{path}?ref={default_branch}"
                        content_resp = requests.get(content_url, headers=headers)
                        
                        if content_resp.status_code == 200:
                            content_data = content_resp.json()
                            if content_data.get('encoding') == 'base64':
                                content = base64.b64decode(content_data['content']).decode('utf-8', errors='ignore')
                                
                                # Detect language
                                lang = self._detect_language(path, content)
                                
                                result["files"].append({
                                    "path": path,
                                    "content": content,
                                    "language": lang
                                })
                                
                                # Analyze this file for tech stack
                                self._analyze_file_for_tech_stack(path, content, result)
                                
                                files_fetched += 1
                                print(f"  [+] Fetched: {path}")
                    except Exception as e:
                        print(f"  [!] Error fetching {path}: {e}")
            
            print(f"[*] Deep scan complete: {files_fetched} files analyzed")
            
            # Summarize what must be preserved vs modernized
            self._categorize_preservation_targets(result)
            
            return result
            
        except Exception as e:
            print(f"[!] Deep scan error: {str(e)}")
            return result
    
    def _detect_language(self, path: str, content: str) -> str:
        """Detect programming language from file path and content."""
        ext_map = {
            '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
            '.tsx': 'typescript-react', '.jsx': 'javascript-react',
            '.json': 'json', '.yaml': 'yaml', '.yml': 'yaml',
            '.html': 'html', '.css': 'css', '.sql': 'sql'
        }
        _, ext = os.path.splitext(path)
        return ext_map.get(ext.lower(), 'text')
    
    def _analyze_file_for_tech_stack(self, path: str, content: str, result: dict):
        """Analyze file content to detect tech stack and important patterns."""
        path_lower = path.lower()
        content_lower = content.lower()
        
        # Detect Backend Framework
        if 'fastapi' in content_lower or 'from fastapi' in content_lower:
            result["tech_stack"]["backend"]["framework"] = "FastAPI"
        elif 'flask' in content_lower or 'from flask' in content_lower:
            result["tech_stack"]["backend"]["framework"] = "Flask"
        elif 'express' in content_lower or "require('express')" in content_lower:
            result["tech_stack"]["backend"]["framework"] = "Express.js"
        elif 'django' in content_lower:
            result["tech_stack"]["backend"]["framework"] = "Django"
        
        # Detect Database - CRITICAL FOR PRESERVATION
        if 'mongodb' in content_lower or 'mongoose' in content_lower or 'pymongo' in content_lower:
            result["tech_stack"]["backend"]["database"] = "MongoDB"
            result["must_preserve"].append(f"MongoDB database connection in {path}")
        elif 'postgresql' in content_lower or 'psycopg' in content_lower or 'pg.' in content_lower:
            result["tech_stack"]["backend"]["database"] = "PostgreSQL"
            result["must_preserve"].append(f"PostgreSQL database connection in {path}")
        elif 'mysql' in content_lower or 'pymysql' in content_lower:
            result["tech_stack"]["backend"]["database"] = "MySQL"
            result["must_preserve"].append(f"MySQL database connection in {path}")
        elif 'sqlite' in content_lower:
            result["tech_stack"]["backend"]["database"] = "SQLite"
        elif 'prisma' in content_lower or path.endswith('.prisma'):
            result["must_preserve"].append(f"Prisma schema in {path}")
        
        # Detect Frontend Framework
        if 'react' in content_lower or 'from react' in content_lower or "'react'" in content_lower:
            result["tech_stack"]["frontend"]["framework"] = "React"
        elif 'vue' in content_lower:
            result["tech_stack"]["frontend"]["framework"] = "Vue.js"
        elif 'angular' in content_lower:
            result["tech_stack"]["frontend"]["framework"] = "Angular"
        elif 'next' in content_lower or "'next'" in content_lower:
            result["tech_stack"]["frontend"]["framework"] = "Next.js"
        
        # Detect API Endpoints - MUST PRESERVE
        if 'model' in path_lower or 'schema' in path_lower:
            result["database_schemas"].append(path)
            result["must_preserve"].append(f"Database schema/model in {path}")
        
        if '@app.route' in content or '@app.get' in content or '@app.post' in content:
            result["must_preserve"].append(f"API endpoints in {path}")
            # Extract endpoint patterns
            import re
            endpoints = re.findall(r'@app\.(get|post|put|delete|patch)\([\'"]([^\'"]+)[\'"]', content)
            for method, endpoint in endpoints:
                result["api_endpoints"].append(f"{method.upper()} {endpoint}")
        
        # Detect environment variables
        if '.env' in path or 'config' in path_lower:
            env_vars = re.findall(r'([A-Z_][A-Z0-9_]+)\s*=', content)
            result["env_vars"].extend(env_vars[:10])  # Limit
    
    def _categorize_preservation_targets(self, result: dict):
        """Categorize what must be preserved vs what can be modernized."""
        # Must preserve: database, schemas, core API logic, auth
        # Can modernize: UI, styling, performance optimizations
        
        for file_info in result["files"]:
            path = file_info["path"]
            
            # MUST PRESERVE
            if any(x in path.lower() for x in ['model', 'schema', 'database', 'db.', 'auth', 'middleware']):
                if path not in [p for p in result["must_preserve"]]:
                    result["must_preserve"].append(f"Core logic in {path}")
            
            # CAN MODERNIZE
            elif any(x in path.lower() for x in ['component', 'page', 'view', 'template', 'style', 'css', 'ui']):
                result["can_modernize"].append(path)
        
        # Add summary
        result["preservation_summary"] = {
            "database": result["tech_stack"]["backend"]["database"],
            "total_files": len(result["files"]),
            "must_preserve_count": len(result["must_preserve"]),
            "can_modernize_count": len(result["can_modernize"]),
            "api_endpoints_count": len(result["api_endpoints"])
        }


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

    def generate_modernization_plan(self, repo_url: str, instructions: str, deep_scan_result: dict = None) -> str:
        """
        PRESERVATION-FIRST PLANNING
        Analyzes existing codebase and creates a plan that PRESERVES functionality
        while only modernizing UI and optimizing performance.
        """
        
        # Build context from deep scan
        if deep_scan_result:
            tech_stack = deep_scan_result.get("tech_stack", {})
            must_preserve = deep_scan_result.get("must_preserve", [])
            can_modernize = deep_scan_result.get("can_modernize", [])
            api_endpoints = deep_scan_result.get("api_endpoints", [])
            files = deep_scan_result.get("files", [])
            file_count = len(files)
            
            # Create file contents - NO LIMITS! Send FULL content to Gemini
            files_content = ""
            for f in files:  # ALL files - no limit!
                files_content += f"\n\n=== FILE: {f['path']} ===\n```{f['language']}\n{f['content']}\n```"  # FULL content!
            
            preservation_context = f"""
═══════════════════════════════════════════════════════════════════════════════
EXISTING CODEBASE ANALYSIS (FROM DEEP SCAN)
═══════════════════════════════════════════════════════════════════════════════

DETECTED TECH STACK:
- Backend Framework: {tech_stack.get('backend', {}).get('framework', 'Unknown')}
- Database: {tech_stack.get('backend', {}).get('database', 'Unknown')}
- Frontend Framework: {tech_stack.get('frontend', {}).get('framework', 'Unknown')}

🔒 MUST PRESERVE (DO NOT CHANGE):
{chr(10).join(['- ' + item for item in must_preserve[:20]])}

✅ CAN MODERNIZE (UI/UX ONLY):
{chr(10).join(['- ' + item for item in can_modernize[:20]])}

DETECTED API ENDPOINTS (KEEP EXACTLY AS-IS):
{chr(10).join(['- ' + ep for ep in api_endpoints[:20]])}

───────────────────────────────────────────────────────────────────────────────
FULL FILE CONTENTS (USE THESE AS BASE):
───────────────────────────────────────────────────────────────────────────────
{files_content}
"""
        else:
            preservation_context = "[DEEP SCAN NOT AVAILABLE - Using path-only mode]"
            file_count = 0
        
        prompt = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  LAZARUS ENGINE - PRESERVATION-FIRST MODERNIZATION SYSTEM                   ║
║  VERSION: 4.0 - PRESERVE & ENHANCE (NOT REPLACE!)                           ║
╚══════════════════════════════════════════════════════════════════════════════╝

ROLE: You are an elite architect who PRESERVES working systems while enhancing them.

═══════════════════════════════════════════════════════════════════════════════
🎯 THE GOLDEN RULE
═══════════════════════════════════════════════════════════════════════════════

"IF IT WORKS, DON'T BREAK IT. IF IT'S UGLY, MAKE IT PRETTY. IF IT'S SLOW, MAKE IT FAST."

YOU MUST:
1. PRESERVE all existing functionality - every API endpoint, every database query
2. KEEP the same database (MongoDB stays MongoDB, PostgreSQL stays PostgreSQL)
3. MAINTAIN all existing data schemas and models
4. ONLY modernize the UI/UX layer
5. OPTIMIZE slow code (but output must remain identical)
6. ADD new features ON TOP of existing ones (don't replace)

YOU MUST NOT:
❌ Change the database type (e.g., MongoDB → SQLite is FORBIDDEN)
❌ Rename or remove existing API endpoints
❌ Modify existing data schemas
❌ Remove any existing functionality
❌ Create a "new architecture" - you are ENHANCING, not replacing!

═══════════════════════════════════════════════════════════════════════════════
📦 LEGACY REPOSITORY
═══════════════════════════════════════════════════════════════════════════════

Repository URL: {repo_url}
User Preferences: "{instructions if instructions else 'Modernize UI while preserving all functionality'}"

{preservation_context}

═══════════════════════════════════════════════════════════════════════════════
📋 YOUR PLANNING TASK
═══════════════════════════════════════════════════════════════════════════════

PHASE 1: PRESERVATION AUDIT
Analyze the existing codebase and list:
1. All API endpoints that MUST work exactly as before
2. Database type and connection (DO NOT CHANGE)
3. Data models/schemas (PRESERVE EXACTLY)
4. Authentication method (KEEP SAME)
5. Core business logic (KEEP SAME)

PHASE 2: ENHANCEMENT TARGETS (NOT REPLACEMENT!)
Identify what can be ENHANCED IN-PLACE:
1. HTML files - Add modern CSS classes, better structure (KEEP SAME FILES!)
2. CSS files - Modernize styling (dark mode, better colors, animations)
3. JavaScript - Convert var→const, add async/await (KEEP SAME FILES!)
4. Server files - Add error handling, logging (KEEP ALL ENDPOINTS!)
5. Performance - Optimize slow code (SAME OUTPUT!)

⚠️ YOU ARE NOT CREATING A NEW FRAMEWORK! ⚠️
- If original uses HTML files → KEEP HTML files (modernize them!)
- If original uses Vue.js → KEEP Vue.js (enhance it!)
- If original uses Express → KEEP Express (optimize it!)
- DO NOT replace HTML with React/Next.js
- DO NOT create a new folder structure

PHASE 3: IN-PLACE ENHANCEMENT PLAN

**Backend (Express.js - PRESERVE COMPLETELY)**:
- KEEP: Same framework (Express stays Express!)
- KEEP: Same database and connection strings
- KEEP: ALL API endpoints (exact same paths and methods)
- KEEP: Same authentication flow
- KEEP: Same file structure
- ADD: Better error handling, logging
- ADD: CORS middleware

**Frontend (ENHANCE EXISTING FILES, NOT REPLACE)**:
- KEEP: All original HTML/CSS/JS files
- KEEP: Same file paths and structure
- ENHANCE: Add modern CSS to existing HTML
- ENHANCE: Add responsive design
- ENHANCE: Improve JavaScript (ES6+)
- DO NOT: Create new React/Next.js/Vue files

PHASE 4: OUTPUT REQUIREMENTS

Your plan MUST include:

1. **PRESERVATION CHECKLIST**:
   - [ ] All {file_count} original files will be output
   - [ ] All existing API endpoints preserved
   - [ ] Database type unchanged
   - [ ] Same file paths used

2. **BACKEND ENHANCEMENT**:
   - Files to enhance: [list ALL server files from original]
   - Endpoints to preserve: [list ALL - no exceptions!]
   - Additions: [only logging, error handling if missing]

3. **FRONTEND ENHANCEMENT**:
   - HTML files to enhance: [list ALL HTML files from original]
   - CSS changes: [describe modern styling to add]
   - JavaScript improvements: [list syntax upgrades]

4. **FILE OUTPUT**:
   List ALL files you will output:
   - [PRESERVE] - Original path, enhanced content
   
   Example:
   - [PRESERVE] Home/Home/admin.html
   - [PRESERVE] Home/Home/adminserver.js
   - [PRESERVE] Home/Home/styles.css

⚠️ CRITICAL: You must output ALL {file_count} original files!

Output format: Plain text architectural plan with clear sections.
"""
        # Use Gemini 3 Pro for complex reasoning
        return self._call_gemini(prompt, model="gemini-3-pro-preview")

    def generate_code(self, plan: str, deep_scan_result: dict = None, repo_url: str = None) -> dict:
        """
        Returns info about the code to be generated (Multiple Files, Nested Structure).
        Uses PRESERVATION-FIRST prompt from prompts.py module.
        
        deep_scan_result: Contains existing codebase info for preservation.
        repo_url: Repository URL for loading resurrection memory.
        """
        # Load resurrection memory for this repository
        memory_context = ""
        if repo_url:
            memory_context = get_memory_context_for_prompt(repo_url)
            memory_summary = get_memory_summary(repo_url)
            if memory_summary["total_attempts"] > 0:
                print(f"[*] 🧠 Resurrection Memory Loaded: {memory_summary['total_attempts']} past attempts, {memory_summary['failed_attempts']} failures")
        
        # Get the comprehensive prompt from the prompts module
        # Pass deep_scan_result for preservation context (existing code, database, etc.)
        # Pass memory_context for cross-session learning
        prompt = get_code_generation_prompt(plan, deep_scan_result, memory_context)
        
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
                "entrypoint": "error.log",
                "runtime": "unknown"
            }

        # SMART ENTRYPOINT DETECTION
        # Detect runtime and entrypoint based on generated files
        entrypoint = None
        runtime = "python"  # Default
        
        # Priority order for entrypoints
        node_entrypoints = [
            "server.js", "index.js", "app.js", "main.js",
            "adminserver.js", "backend.js"
        ]
        python_entrypoints = [
            "main.py", "app.py", "server.py", "run.py"
        ]
        
        for f in files:
            filename = f["filename"]
            basename = os.path.basename(filename)
            
            # Check for Node.js entrypoints
            if basename in node_entrypoints or filename.endswith("server.js"):
                entrypoint = filename
                runtime = "node"
                print(f"[*] Detected Node.js entrypoint: {entrypoint}")
                break
            
            # Check for Python entrypoints
            if basename in python_entrypoints:
                entrypoint = filename
                runtime = "python"
                print(f"[*] Detected Python entrypoint: {entrypoint}")
                break
        
        # Fallback: Look for package.json (Node.js) or requirements.txt (Python)
        if not entrypoint:
            for f in files:
                if f["filename"].endswith("package.json"):
                    # Node.js project - find the main server file
                    runtime = "node"
                    for ff in files:
                        if ff["filename"].endswith(".js") and "server" in ff["filename"].lower():
                            entrypoint = ff["filename"]
                            break
                    if not entrypoint:
                        # Try to find any .js file
                        for ff in files:
                            if ff["filename"].endswith(".js"):
                                entrypoint = ff["filename"]
                                break
                    break
                elif f["filename"].endswith("requirements.txt") or f["filename"].endswith(".py"):
                    runtime = "python"
                    # Python project - use default
                    entrypoint = "modernized_stack/backend/main.py"
                    break
        
        # Final fallback
        if not entrypoint:
            if any(f["filename"].endswith(".js") for f in files):
                runtime = "node"
                entrypoint = next((f["filename"] for f in files if f["filename"].endswith(".js")), None)
            else:
                runtime = "python"
                entrypoint = "modernized_stack/backend/main.py"
        
        print(f"[*] Smart Detection: Runtime={runtime}, Entrypoint={entrypoint}")

        return {
            "files": files,
            "entrypoint": entrypoint,
            "runtime": runtime
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

    def execute_in_sandbox(self, files: list, entrypoint: str, runtime: str = "python", deep_scan_result: dict = None):
        """
        Execute generated code in E2B sandbox.
        Supports both Python and Node.js runtimes.
        
        runtime: "python" or "node"
        deep_scan_result: Original repository scan result for dependency detection
        """
        if not E2B_AVAILABLE or not E2B_API_KEY:
            return "E2B Sandbox not available (Dependencies or Key missing)."
            
        # SAFETY CHECK: Did Code Gen Fail?
        if entrypoint == "error.log":
            return f"GENERATION FAILED: Gemini API returned an error.\n\n=== ERROR LOG ===\n{files[0]['content']}\n================="

        print(f"[*] Executing {entrypoint} in E2B Sandbox (Runtime: {runtime})...")
        
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
            
            # Install Dependencies Based on Runtime
            if runtime == "node" or entrypoint.endswith('.js'):
                # ═══════════════════════════════════════════════════════════
                # NODE.JS EXECUTION PATH
                # ═══════════════════════════════════════════════════════════
                print("[*] 🟢 Node.js Runtime Detected")
                
                # Find the directory containing package.json
                entrypoint_dir = os.path.dirname(entrypoint)
                if not entrypoint_dir:
                    entrypoint_dir = "."
                
                # CRITICAL: Look for package.json in ORIGINAL deep_scan first (uses 'path' key)
                # Then fall back to generated files (uses 'filename' key)
                original_package = None
                if deep_scan_result:
                    original_files = deep_scan_result.get("files", [])
                    original_package = next((f for f in original_files if f.get('path', '').endswith('package.json')), None)
                    if original_package:
                        print(f"[*] Found ORIGINAL package.json from repository scan: {original_package.get('path')}")
                
                # Also check generated files (fallback)
                gen_package_json = next((f for f in files if f['filename'].endswith('package.json')), None)
                
                # Check for package.json in entrypoint directory specifically
                entrypoint_package = next((f for f in files if f['filename'] == f"{entrypoint_dir}/package.json"), None)
                
                # Use ORIGINAL package.json for dependencies, fall back to generated
                package_source = original_package if original_package else gen_package_json
                package_dir = entrypoint_dir  # Default to entrypoint dir
                
                if package_source:
                    # Determine the directory
                    if original_package:
                        package_dir = os.path.dirname(original_package.get('path', '')) or "."
                    elif gen_package_json:
                        package_dir = os.path.dirname(gen_package_json.get('filename', '')) or "."
                    
                    print(f"[*] Found package.json - extracting dependencies...")
                    
                    # DYNAMIC DEPENDENCY DETECTION - Parse the package.json content!
                    try:
                        # Get the content of package.json
                        package_content = package_source.get('content', '')
                        if package_content:
                            import json as json_module
                            pkg_data = json_module.loads(package_content)
                            deps = list(pkg_data.get('dependencies', {}).keys())
                            dev_deps = list(pkg_data.get('devDependencies', {}).keys())
                            all_deps = deps + dev_deps
                            
                            if all_deps:
                                print(f"[*] 📦 Detected {len(all_deps)} dependencies: {', '.join(all_deps[:10])}{'...' if len(all_deps) > 10 else ''}")
                                # Install ALL detected dependencies in entrypoint directory
                                deps_str = ' '.join(all_deps)
                                print(f"[*] Installing dependencies in {entrypoint_dir}...")
                                install_result = self.sandbox.commands.run(f"cd {entrypoint_dir} && npm init -y && npm install {deps_str}", timeout=300)
                            else:
                                print("[*] No dependencies found in package.json, installing common packages...")
                                install_result = self.sandbox.commands.run(f"cd {entrypoint_dir} && npm init -y && npm install express mongoose cors dotenv bcrypt multer node-fetch xlsx cookie-parser", timeout=300)
                        else:
                            print("[*] Package.json has no content, installing common packages...")
                            install_result = self.sandbox.commands.run(f"cd {entrypoint_dir} && npm init -y && npm install express mongoose cors dotenv bcrypt multer node-fetch xlsx cookie-parser", timeout=300)
                    except Exception as pkg_err:
                        print(f"[!] Error parsing package.json: {pkg_err}, installing common packages...")
                        install_result = self.sandbox.commands.run(f"cd {entrypoint_dir} && npm init -y && npm install express mongoose cors dotenv bcrypt multer node-fetch xlsx cookie-parser", timeout=300)
                    
                    if install_result.exit_code != 0:
                        print(f"[!] npm install warning: {install_result.stderr[:200] if install_result.stderr else 'No stderr'}")
                    
                    # CRITICAL: If entrypoint is in a subdirectory, also install there
                    # This handles cases like: package.json in root, server in server/
                    if entrypoint_dir and entrypoint_dir != "." and entrypoint_dir != package_dir:
                        # Check if there's a package.json in the server directory
                        if entrypoint_package:
                            print(f"[*] Found separate package.json in server directory: {entrypoint_dir}")
                            print(f"[*] Installing dependencies in {entrypoint_dir}...")
                            self.sandbox.commands.run(f"cd {entrypoint_dir} && npm install", timeout=300)
                        else:
                            # No package.json in server dir - install common packages there
                            print(f"[*] No package.json in {entrypoint_dir}, installing common packages...")
                            self.sandbox.commands.run(f"cd {entrypoint_dir} && npm init -y && npm install express mongoose cors dotenv bcrypt multer node-fetch xlsx", timeout=180)
                else:
                    # No package.json anywhere, install common packages in entrypoint directory
                    print("[*] No package.json found, installing common packages...")
                    package_dir = entrypoint_dir
                    self.sandbox.commands.run(f"cd {entrypoint_dir} && npm init -y", timeout=30)
                    self.sandbox.commands.run(f"cd {entrypoint_dir} && npm install express mongoose cors dotenv bcrypt multer node-fetch xlsx", timeout=180)
                
                # START NODE SERVER IN BACKGROUND
                print(f"[*] Starting Node.js Server: {entrypoint} (logging to app.log)...")
                
                # Run from entrypoint directory (where we installed dependencies)
                # Just run the entrypoint file directly
                server_basename = os.path.basename(entrypoint)
                
                if entrypoint_dir and entrypoint_dir != ".":
                    print(f"[*] Node.js Command: cd {entrypoint_dir} && node {server_basename}")
                    node_cmd = f"cd {entrypoint_dir} && node {server_basename} > app.log 2>&1"
                else:
                    print(f"[*] Node.js Command: node {entrypoint}")
                    node_cmd = f"node {entrypoint} > app.log 2>&1"
                
                self.sandbox.commands.run(node_cmd, background=True)
                
                # HEALTH CHECK LOOP (for Node.js - check ports 3000 and 8000)
                print("[*] Waiting for Node.js Backend to boot...")
                backend_success = False
                node_port = None
                
                for i in range(20):  # Try for 60 seconds
                    time.sleep(3)
                    try:
                        # Check ALL common Node.js ports (3001 is very common!)
                        for port in [3000, 3001, 8000, 8080, 5000, 4000, 5001]:
                            check_script = f"""
import urllib.request
import urllib.error
try:
    response = urllib.request.urlopen('http://127.0.0.1:{port}', timeout=2)
    print('PORT_{port}_OK')
except urllib.error.HTTPError as e:
    print('PORT_{port}_OK')  # 4xx/5xx still means server is running
except:
    pass
"""
                            result = self.sandbox.commands.run(f"python3 -c \"{check_script}\"")
                            if f"PORT_{port}_OK" in result.stdout:
                                node_port = port
                                backend_success = True
                                break
                        
                        if backend_success:
                            break
                            
                        print(f"[*] Node.js Health Check {i+1}/20: Waiting...")
                        
                        # Early log check for crash detection
                        if i == 4:
                            log_check = self.sandbox.commands.run(f"cd {package_dir} && cat app.log 2>/dev/null | head -10")
                            if log_check.stdout:
                                print(f"[DEBUG] Early Log Check:\n{log_check.stdout[:300]}")
                                
                    except Exception as e:
                        print(f"[*] Node.js Health Check {i+1}/20: {str(e)[:50]}...")
                
                if not backend_success:
                    # Get logs for debugging
                    log_result = self.sandbox.commands.run(f"cd {package_dir} && cat app.log 2>/dev/null")
                    return f"FATAL: Node.js Backend failed to start after 60 seconds.\n\n=== APP.LOG ===\n{log_result.stdout[:1000]}\n==============="
                
                backend_url = f"https://{self.sandbox.get_host(node_port)}"
                print(f"[*] Node.js Backend Live at: {backend_url}")
                
                # ═══════════════════════════════════════════════════════════
                # COMPREHENSIVE FRONTEND/PROJECT DETECTION
                # Detects: React, Vue, Next.js, Vite, Angular, Static HTML,
                #          PHP, Flask templates, Django templates, and more
                # ═══════════════════════════════════════════════════════════
                frontend_dirs = []
                frontend_type = "unknown"
                has_static_html = False
                static_html_dirs = set()
                
                for f in files:
                    path = f['filename']
                    path_lower = path.lower()
                    basename = os.path.basename(path)
                    dirname = os.path.dirname(path)
                    
                    # ───────────────────────────────────────────────────────────
                    # JavaScript Framework Detection (Need npm build)
                    # ───────────────────────────────────────────────────────────
                    
                    # Next.js
                    if 'next.config' in basename.lower():
                        frontend_dirs.append(dirname)
                        frontend_type = "Next.js"
                    
                    # Vite (React, Vue, Svelte)
                    elif 'vite.config' in basename.lower():
                        frontend_dirs.append(dirname)
                        frontend_type = "Vite"
                    
                    # Angular
                    elif basename == 'angular.json':
                        frontend_dirs.append(dirname)
                        frontend_type = "Angular"
                    
                    # Vue CLI
                    elif basename == 'vue.config.js':
                        frontend_dirs.append(dirname)
                        frontend_type = "Vue CLI"
                    
                    # Create React App
                    elif basename == 'package.json' and ('frontend' in path_lower or 'client' in path_lower or 'web' in path_lower):
                        frontend_dirs.append(dirname)
                        frontend_type = "React/NPM"
                    
                    # Nuxt.js
                    elif 'nuxt.config' in basename.lower():
                        frontend_dirs.append(dirname)
                        frontend_type = "Nuxt.js"
                    
                    # Gatsby
                    elif basename == 'gatsby-config.js':
                        frontend_dirs.append(dirname)
                        frontend_type = "Gatsby"
                    
                    # SvelteKit
                    elif basename == 'svelte.config.js':
                        frontend_dirs.append(dirname)
                        frontend_type = "SvelteKit"
                    
                    # ───────────────────────────────────────────────────────────
                    # Static HTML Detection (Served directly by backend)
                    # ───────────────────────────────────────────────────────────
                    if path.endswith('.html'):
                        # Common static directories
                        static_patterns = ['public', 'static', 'views', 'templates', 'www', 'html', 'pages']
                        for pattern in static_patterns:
                            if pattern in path_lower:
                                static_html_dirs.add(dirname)
                                has_static_html = True
                                break
                        
                        # Any HTML at root or in recognized folder
                        if dirname and not has_static_html:
                            static_html_dirs.add(dirname)
                            has_static_html = True
                    
                    # ───────────────────────────────────────────────────────────
                    # Template Engine Detection (Served by backend)
                    # ───────────────────────────────────────────────────────────
                    
                    # EJS (Express)
                    if path.endswith('.ejs'):
                        has_static_html = True
                        static_html_dirs.add(dirname)
                    
                    # Pug/Jade (Express)
                    elif path.endswith('.pug') or path.endswith('.jade'):
                        has_static_html = True
                        static_html_dirs.add(dirname)
                    
                    # Handlebars (Express)
                    elif path.endswith('.hbs') or path.endswith('.handlebars'):
                        has_static_html = True
                        static_html_dirs.add(dirname)
                    
                    # Jinja2 (Flask/Python)
                    elif path.endswith('.jinja2') or path.endswith('.j2'):
                        has_static_html = True
                        static_html_dirs.add(dirname)
                    
                    # Django templates
                    elif '/templates/' in path and path.endswith('.html'):
                        has_static_html = True
                        static_html_dirs.add(dirname)
                    
                    # PHP
                    elif path.endswith('.php'):
                        has_static_html = True
                        static_html_dirs.add(dirname)
                    
                    # Ruby ERB
                    elif path.endswith('.erb'):
                        has_static_html = True
                        static_html_dirs.add(dirname)
                
                # Deduplicate JS framework dirs
                frontend_dirs = list(set(frontend_dirs))
                
                # Log what was detected
                if has_static_html:
                    static_dirs_str = ', '.join(list(static_html_dirs)[:3])
                    print(f"[*] 📄 Static HTML/Templates Detected: {static_dirs_str}")
                    print(f"[*] ℹ️  Static content will be served directly by the Node.js backend")
                
                if frontend_dirs:
                    frontend_dir = frontend_dirs[0]
                    print(f"[*] 🎨 JS Framework Detected: {frontend_type} at {frontend_dir}")
                    
                    # Install frontend dependencies
                    print(f"[*] Installing Frontend dependencies (npm install)...")
                    install_result = self.sandbox.commands.run(f"cd {frontend_dir} && npm install --force", timeout=300)
                    if install_result.exit_code != 0:
                        print(f"[!] npm install warning: {install_result.stderr[:200] if install_result.stderr else 'No stderr'}")
                    
                    # Inject Backend URL into .env.local for Next.js
                    print(f"[*] Injecting Backend URL into frontend environment...")
                    env_content = f"NEXT_PUBLIC_API_URL={backend_url}\nVITE_API_URL={backend_url}\nREACT_APP_API_URL={backend_url}\n"
                    self.sandbox.files.write(f"{frontend_dir}/.env.local", env_content)
                    self.sandbox.files.write(f"{frontend_dir}/.env", env_content)
                    
                    # Build frontend (for Next.js, React)
                    print(f"[*] Building Frontend for production...")
                    build_result = self.sandbox.commands.run(f"cd {frontend_dir} && npm run build", timeout=300)
                    
                    if build_result.exit_code != 0:
                        error_output = (build_result.stderr or '') + (build_result.stdout or '')
                        print(f"[!] Frontend build failed. Error:\n{error_output[:500]}")
                        # Return with just backend URL if frontend fails
                        return f"Node.js Backend started (Frontend build failed).\n[PREVIEW_URL] {backend_url}\n\n=== BUILD ERROR ===\n{error_output[:500]}"
                    
                    # Start frontend in production mode
                    print(f"[*] Starting Frontend in production mode...")
                    # Try different start commands based on framework
                    start_cmd = f"cd {frontend_dir} && npm start -- -p 3000 > frontend.log 2>&1"
                    self.sandbox.commands.run(start_cmd, background=True)
                    
                    # Wait for frontend to boot
                    time.sleep(10)
                    
                    # Get frontend URL
                    frontend_host = self.sandbox.get_host(3000)
                    frontend_url = f"https://{frontend_host}"
                    
                    print(f"[*] 🎨 Frontend Live at: {frontend_url}")
                    print(f"[*] Frontend → Backend Connection: {backend_url}")
                    
                    return f"Dual-Stack Deployed Successfully.\n[PREVIEW_URL] {frontend_url}\n[BACKEND_URL] {backend_url}"
                
                # No frontend detected - just return backend URL
                return f"Node.js Server started successfully.\n[PREVIEW_URL] {backend_url}"
                
            elif runtime == "python" or entrypoint.endswith('.py'):
                # ═══════════════════════════════════════════════════════════
                # PYTHON EXECUTION PATH (Original)
                # ═══════════════════════════════════════════════════════════
                print("[*] 🐍 Python Runtime Detected")
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
                    self.sandbox.commands.run(f"pip install -r {req_file['filename']}", timeout=300)
                
                # 3. Force Install the Consolidated "Smart" list
                if final_reqs:
                    install_str = " ".join([f"'{p}'" for p in final_reqs])
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
        deep_scan_result = None  # Store deep scan for reuse
        
        def emit_log(msg):
            logs.append(msg)
            return {"type": "log", "content": msg}

        def emit_debug(msg):
            return {"type": "debug", "content": msg}

        # Record resurrection attempt start in memory
        record_attempt_start(repo_url, None)
        
        # 1. DEEP SCAN - Fetch ALL file contents for preservation
        yield emit_log("🔍 Initiating DEEP SCAN of Legacy Repository...")
        yield emit_log("📂 Fetching ALL file contents for preservation analysis...")
        
        # DEEP SCAN (fetches full file contents)
        deep_scan_result = self.scan_repository_deep(repo_url)
        
        tech_stack = deep_scan_result.get("tech_stack", {})
        must_preserve = deep_scan_result.get("must_preserve", [])
        files_analyzed = len(deep_scan_result.get("files", []))
        
        # Update memory with tech stack
        record_attempt_start(repo_url, tech_stack)
        
        yield emit_debug(f"[DEBUG] Deep Scan Complete:\n  Files Analyzed: {files_analyzed}\n  Tech Stack: {tech_stack}\n  Must Preserve: {len(must_preserve)} items")
        
        if tech_stack.get("backend", {}).get("database"):
            yield emit_log(f"🔒 Detected Database: {tech_stack['backend']['database']} (WILL BE PRESERVED)")
        if tech_stack.get("backend", {}).get("framework"):
            yield emit_log(f"⚙️ Detected Backend: {tech_stack['backend']['framework']}")
        if tech_stack.get("frontend", {}).get("framework"):
            yield emit_log(f"🎨 Detected Frontend: {tech_stack['frontend']['framework']}")

        # 2. PRESERVATION-FIRST PLANNING
        yield emit_log("📋 Creating PRESERVATION-FIRST Modernization Plan...")
        
        plan = self.generate_modernization_plan(repo_url, instructions, deep_scan_result)
        yield emit_debug(f"[DEBUG] Generated Plan:\n{plan}")

        if "[ERROR]" in plan:
             yield emit_log("⚠️ Warning: Connection Unstable. Engaged Fallback Protocols.")
             fallback_mode = True
        else:
             fallback_mode = False
             
        yield emit_log("🏗️ Architecting Enhanced Blueprint (Preserving Core Logic)...")

        # 2. Code Gen with COMPREHENSIVE Auto-Healing Loop
        MAX_RETRIES = 3  # Increased from 2
        retry_count = 0
        sandbox_logs = None
        files = []
        entrypoint = 'modernized_stack/backend/main.py'
        all_errors = []  # Track all errors for context accumulation
        
        while retry_count <= MAX_RETRIES:
            try:
                if retry_count > 0:
                    yield emit_log(f"🔧 Auto-Healing: Regenerating code (Attempt {retry_count + 1}/{MAX_RETRIES + 1})...")
                    
                    # Build comprehensive error context for AI
                    error_context = self._build_error_context(all_errors)
                    plan_with_error = plan + error_context
                    # Pass deep_scan_result for preservation context
                    code_data = self.generate_code(plan_with_error, deep_scan_result, repo_url)
                else:
                    yield emit_log("🔨 Synthesizing Enhanced Infrastructure (Preserving Core Logic)...")
                    # Pass deep_scan_result for preservation context
                    code_data = self.generate_code(plan, deep_scan_result, repo_url)
                
                files = code_data.get('files', [])
                entrypoint = code_data.get('entrypoint', 'modernized_stack/backend/main.py')
                runtime = code_data.get('runtime', 'python')  # NEW: Get runtime from code_data
                
                # Validate generated files
                if not files:
                    raise Exception("CODE GENERATION FAILED: No files were generated")
                
                encoded_files = [f['filename'] for f in files]
                yield emit_debug(f"[DEBUG] Generated Files: {', '.join(encoded_files)}")
                yield emit_log(f"Generated {len(encoded_files)} System Modules...")
                yield emit_log(f"📦 Detected Runtime: {runtime.upper()} | Entrypoint: {entrypoint}")
                
                # 3. Execution (Pass runtime for Node.js vs Python handling)
                yield emit_log("Booting Neural Sandbox Environment...")
                sandbox_logs = self.execute_in_sandbox(files, entrypoint, runtime, deep_scan_result)
                yield emit_debug(f"[DEBUG] Sandbox Output:\n{sandbox_logs}")
                
                # 4. Comprehensive Error Detection
                error_detected, error_type, error_message = self._detect_errors(sandbox_logs)
                
                if error_detected:
                    all_errors.append({
                        "attempt": retry_count + 1,
                        "type": error_type,
                        "message": error_message
                    })
                    
                    if retry_count < MAX_RETRIES:
                        yield emit_log(f"⚠️ {error_type} Detected. Initiating Auto-Heal...")
                        retry_count += 1
                        continue  # Retry
                    else:
                        record_failure(repo_url, error_type, error_context[:200], f"Attempt {retry_count + 1}")
                        yield emit_log(f"❌ Auto-Heal Failed after {MAX_RETRIES + 1} attempts. Proceeding with partial result.")
                        break
                else:
                    # Success!
                    record_success(repo_url, decisions=["Resurrection completed successfully"], patterns_used=[f"Runtime: {runtime}", f"Entrypoint: {entrypoint}"])
                    yield emit_log("✅ Verifying System Integrity... All checks passed!")
                    break
                    
            except Exception as loop_error:
                error_str = str(loop_error)
                all_errors.append({
                    "attempt": retry_count + 1,
                    "type": "EXCEPTION",
                    "message": error_str
                })
                
                if retry_count < MAX_RETRIES:
                    yield emit_log(f"⚠️ Exception caught: {error_str[:100]}... Retrying...")
                    retry_count += 1
                    sandbox_logs = f"EXCEPTION: {error_str}"
                    continue
                else:
                    record_failure(repo_url, "EXCEPTION", error_str[:200], "Max retries exceeded")
                    yield emit_log(f"❌ Max retries exceeded. Error: {error_str[:100]}")
                    sandbox_logs = f"FATAL ERROR: {error_str}"
                    break
        
        # Extract HTML for preview
        preview = ""
        # Check logs for URL
        url_match = re.search(r"\[PREVIEW_URL\] (https://[^\s]+)", sandbox_logs or "")
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
        if fallback_mode or (sandbox_logs and ("Sandbox Error" in sandbox_logs or "BUILD FAILED" in sandbox_logs or "FATAL ERROR" in sandbox_logs)):
            status = "Fallback"
        elif preview.startswith("http"):
            status = "Resurrected"  # Successfully got live URLs
        
        # Final Result
        yield {
            "type": "result",
            "data": {
                "logs": "\n".join(logs),
                "artifacts": files,
                "preview": preview,
                "status": status,
                "retry_count": retry_count,
                "errors": all_errors
            }
        }
    
    def _detect_errors(self, sandbox_logs: str) -> tuple:
        """
        Comprehensive error detection for self-healing loop.
        Returns: (error_detected: bool, error_type: str, error_message: str)
        """
        if not sandbox_logs:
            return False, "", ""
        
        # Error patterns to detect with their types
        error_patterns = [
            # ═══════════════════════════════════════════════════════════
            # NODE.JS SPECIFIC ERRORS (CRITICAL FOR AUTO-HEALING)
            # ═══════════════════════════════════════════════════════════
            (r"Cannot find module", "NODE_MODULE_NOT_FOUND"),
            (r"Error: Cannot find module", "NODE_MODULE_NOT_FOUND"),
            (r"MODULE_NOT_FOUND", "NODE_MODULE_NOT_FOUND"),
            (r"node:internal/modules", "NODE_INTERNAL_ERROR"),
            (r"throw err;", "NODE_CRASH"),
            (r"ReferenceError:", "NODE_REFERENCE_ERROR"),
            (r"Error: listen EADDRINUSE", "NODE_PORT_IN_USE"),
            (r"ENOENT: no such file", "NODE_FILE_NOT_FOUND"),
            (r"SyntaxError: Unexpected", "NODE_SYNTAX_ERROR"),
            (r"Error: ENOENT", "NODE_FILE_NOT_FOUND"),
            
            # Server Failures
            (r"FATAL: Node\.js Backend failed", "NODE_SERVER_CRASH"),
            (r"FATAL: Backend failed", "BACKEND_CRASH"),
            (r"Backend failed to start", "BACKEND_STARTUP_FAILED"),
            (r"No such file or directory", "FILE_NOT_FOUND"),
            (r"can't open file", "FILE_NOT_FOUND"),
            
            # Build Errors
            (r"FRONTEND BUILD FAILED", "FRONTEND_BUILD_ERROR"),
            (r"npm ERR!", "NPM_ERROR"),
            (r"error TS\d+:", "TYPESCRIPT_ERROR"),
            (r"SyntaxError:", "SYNTAX_ERROR"),
            (r"Module not found", "MODULE_NOT_FOUND"),
            
            # Sandbox Errors
            (r"Sandbox Error:", "SANDBOX_ERROR"),
            (r"Command exited with code [^0]", "COMMAND_FAILED"),
            (r"syntax error near unexpected token", "BASH_SYNTAX_ERROR"),
            (r"mkdir.*failed", "MKDIR_ERROR"),
            (r"Permission denied", "PERMISSION_ERROR"),
            
            # Python Errors  
            (r"ModuleNotFoundError:", "PYTHON_IMPORT_ERROR"),
            (r"ImportError:", "PYTHON_IMPORT_ERROR"),
            (r"IndentationError:", "PYTHON_SYNTAX_ERROR"),
            (r"NameError:", "PYTHON_NAME_ERROR"),
            (r"TypeError:", "PYTHON_TYPE_ERROR"),
            (r"FileNotFoundError:", "PYTHON_FILE_NOT_FOUND"),
            
            # Connection Errors
            (r"ECONNREFUSED", "CONNECTION_ERROR"),
            (r"Failed to connect", "CONNECTION_ERROR"),
            (r"Backend connection failed", "BACKEND_ERROR"),
            
            # Generation Errors
            (r"GENERATION FAILED", "GENERATION_ERROR"),
            (r"No files were generated", "EMPTY_GENERATION"),
            
            # MongoDB/Database Errors
            (r"MongoNetworkError", "DATABASE_CONNECTION_ERROR"),
            (r"MongoServerError", "DATABASE_ERROR"),
            (r"ECONNREFUSED.*27017", "MONGODB_CONNECTION_ERROR"),
        ]
        
        for pattern, error_type in error_patterns:
            match = re.search(pattern, sandbox_logs, re.IGNORECASE)
            if match:
                # Extract context around the error
                start = max(0, match.start() - 200)
                end = min(len(sandbox_logs), match.end() + 500)
                error_context = sandbox_logs[start:end]
                return True, error_type, error_context
        
        return False, "", ""
    
    def _build_error_context(self, errors: list) -> str:
        """
        Builds comprehensive error context for AI to understand and fix issues.
        """
        if not errors:
            return ""
        
        context = "\n\n" + "=" * 80 + "\n"
        context += "⚠️ AUTOMATIC ERROR RECOVERY - FIX THE FOLLOWING ISSUES ⚠️\n"
        context += "=" * 80 + "\n\n"
        
        for i, error in enumerate(errors, 1):
            context += f"### Error {i} (Attempt {error['attempt']}) - Type: {error['type']}\n"
            context += f"```\n{error['message'][:1000]}\n```\n\n"
        
        context += """
### COMMON FIXES TO APPLY:

1. **TYPESCRIPT ERRORS**: Use `string` not `str`, `number` not `int`, `boolean` not `bool`
2. **MODULE NOT FOUND**: Check import paths, ensure all dependencies in package.json
3. **SYNTAX ERRORS**: Check for missing brackets, semicolons, proper JSX syntax
4. **BASH/PATH ERRORS**: NO parentheses (), brackets [], spaces in file paths!
5. **BUILD ERRORS**: Ensure next.config.mjs (not .ts), all config files present
6. **PYTHON ERRORS**: Check imports, ensure all packages in requirements.txt
7. **CORS ERRORS**: Backend must have CORS middleware with allow_origins=["*"]

### CRITICAL REMINDERS:
- Use ONLY alphanumeric, hyphens, underscores in file paths
- layout.tsx MUST import './globals.css'
- globals.css MUST start with @tailwind directives
- next.config.mjs NOT next.config.ts
- Backend must have health check at GET /
- All TypeScript files need 'use client' for interactive components

FIX ALL ISSUES AND REGENERATE COMPLETE, WORKING CODE.
"""
        return context


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
