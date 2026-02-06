import os
import requests
import base64
from simple_env import load_env

load_env()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_OWNER = "ArunN2005"
REPO_NAME = "demo-repo"
BRANCH = "main"

if not GITHUB_TOKEN:
    print("[!] GITHUB_TOKEN not found.")
    exit(1)

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

BASE_API = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents"

# Legacy Codebase Assets
FILES = {
    "backend/api.py": """
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Legacy Database (In-Memory)
users = [
    {"id": 1, "name": "Admin", "role": "superuser"},
    {"id": 2, "name": "Guest", "role": "viewer"}
]

@app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify({"system": "online", "version": "1.0.4 (Legacy)"})

@app.route('/api/users', methods=['GET'])
def get_users():
    return jsonify(users)

if __name__ == '__main__':
    app.run(port=5000, debug=True)
""",
    
    "backend/requirements.txt": """
flask==2.0.1
flask-cors==3.0.10
""",

    "frontend/index.html": """
<!DOCTYPE html>
<html>
<head>
    <title>Enterprise Dashboard v1.0</title>
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div class="container">
        <h1>Legacy Enterprise Portal</h1>
        <div id="status-panel">System Status: <span id="status">Loading...</span></div>
        <hr>
        <h2>User Directory</h2>
        <ul id="user-list"></ul>
    </div>

    <script src="app.js"></script>
</body>
</html>
""",

    "frontend/style.css": """
body {
    font-family: 'Times New Roman', serif;
    background-color: #f0f0f0;
    color: #333;
    margin: 20px;
}
.container {
    background: white;
    padding: 20px;
    border: 1px solid #999;
}
h1 { color: #000080; }
#status-panel { font-weight: bold; }
""",

    "frontend/app.js": """
$(document).ready(function() {
    // Legacy API Call
    const API_URL = "http://localhost:5000/api";

    // Get Status
    $.get(API_URL + "/status", function(data) {
        $("#status").text(data.system + " [" + data.version + "]");
        if(data.system === "online") {
            $("#status").css("color", "green");
        }
    }).fail(function() {
        $("#status").text("OFFLINE");
        $("#status").css("color", "red");
    });

    // Get Users
    $.get(API_URL + "/users", function(data) {
        data.forEach(function(user) {
            $("#user-list").append("<li>" + user.name + " (" + user.role + ")</li>");
        });
    });
});
"""
}

def upload_file(path, content):
    url = f"{BASE_API}/{path}"
    
    # Check if exists to get SHA
    sha = None
    resp = requests.get(url, headers=HEADERS)
    if resp.status_code == 200:
        sha = resp.json()['sha']

    encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')
    data = {
        "message": f"Setup Legacy Architecture: {path}",
        "content": encoded,
        "branch": BRANCH
    }
    if sha:
        data['sha'] = sha

    print(f"[*] Uploading {path}...")
    put_resp = requests.put(url, headers=HEADERS, json=data)
    if put_resp.status_code in [200, 201]:
        print(f"    [+] Success")
    else:
        print(f"    [!] Failed: {put_resp.text}")

print(f"[*] Populating {REPO_OWNER}/{REPO_NAME} with Legacy Code...")
for path, content in FILES.items():
    upload_file(path, content)

print("[*] Legacy Repo Population Complete.")
