import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from lazarus_agent import process_resurrection, commit_code
import sys

PORT = 8000

class LazarusHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        if self.path == '/api/resurrect':
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                request_json = json.loads(post_data)
                
                repo_url = request_json.get('repo_url')
                vibe_instructions = request_json.get('vibe_instructions')

                self.send_response(200)
                # Use NDJSON (Newline Delimited JSON) for easy parsing
                self.send_header('Content-Type', 'application/x-ndjson')
                self.send_header('Access-Control-Allow-Origin', '*')
                # Disable buffering
                self.send_header('Cache-Control', 'no-cache')
                self.send_header('Connection', 'keep-alive')
                self.end_headers()

                # Call the generator
                for chunk in process_resurrection(repo_url, vibe_instructions):
                    # Write chunk as JSON line + newline
                    line = json.dumps(chunk) + "\n"
                    self.wfile.write(line.encode('utf-8'))
                    self.wfile.flush()
                
            except Exception as e:
                # Can't send 500 if headers already sent, but we try
                print(f"Error: {e}")
                pass

        elif self.path == '/api/commit':
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                request_json = json.loads(post_data)
                
                repo_url = request_json.get('repo_url')
                filename = request_json.get('filename')
                content = request_json.get('content')

                # Call commit logic
                result = commit_code(repo_url, filename, content)
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(result).encode())

            except Exception as e:
                self.send_error(500, str(e))
        else:
            self.send_response(404)
            self.end_headers()

def run(server_class=HTTPServer, handler_class=LazarusHandler, port=PORT):
    server_address = ('', port)
    print(f"[*] Lazarus Backend running on port {port}...")
    httpd = server_class(server_address, handler_class)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()

if __name__ == "__main__":
    run()
