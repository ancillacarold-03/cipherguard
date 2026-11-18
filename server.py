import http.server
import socketserver
import json
import os
import urllib.parse

PORT = 8000
PUBLIC_DIR = os.path.join(os.path.dirname(__file__), "public")
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=PUBLIC_DIR, **kwargs)

    def send_json_response(self, data, status_code=200):
        response_bytes = json.dumps(data).encode('utf-8')
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response_bytes)))
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        self.end_headers()
        self.wfile.write(response_bytes)

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query = urllib.parse.parse_qs(parsed_url.query)

        if path == '/api/reports':
            username = query.get('username', [None])[0]
            reports_path = os.path.join(DATA_DIR, 'reports.json')
            
            if not os.path.exists(reports_path):
                self.send_json_response([], 200)
                return

            try:
                with open(reports_path, 'r', encoding='utf-8') as f:
                    reports = json.load(f)
            except Exception:
                reports = []

            # Filter reports by username
            if username:
                filtered_reports = [r for r in reports if r.get('username', '').lower() == username.lower()]
                self.send_json_response(filtered_reports, 200)
            else:
                self.send_json_response(reports, 200)
            return
        
        # Default handler serves static files
        super().do_GET()

    def do_POST(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        if path == '/api/login':
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self.send_json_response({"status": "error", "message": "No data provided"}, 400)
                return
            
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode('utf-8'))
            except Exception:
                self.send_json_response({"status": "error", "message": "Invalid JSON format"}, 400)
                return

            username = data.get('username', '').strip()
            password = data.get('password', '').strip()

            if not username or not password:
                self.send_json_response({"status": "error", "message": "Username and password are required"}, 400)
                return

            # Check credentials in data/users.json
            users_path = os.path.join(DATA_DIR, 'users.json')
            if not os.path.exists(users_path):
                self.send_json_response({"status": "error", "message": "User database not found"}, 500)
                return

            try:
                with open(users_path, 'r', encoding='utf-8') as f:
                    users = json.load(f)
            except Exception:
                self.send_json_response({"status": "error", "message": "Could not read user database"}, 500)
                return

            user_found = False
            for user in users:
                if user.get('username', '').lower() == username.lower() and user.get('password') == password:
                    user_found = True
                    break

            if user_found:
                self.send_json_response({"status": "success", "username": username}, 200)
            else:
                self.send_json_response({"status": "error", "message": "Invalid Username or Password"}, 401)
            return

        elif path == '/api/reports':
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self.send_json_response({"status": "error", "message": "No data provided"}, 400)
                return
            
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode('utf-8'))
            except Exception:
                self.send_json_response({"status": "error", "message": "Invalid JSON format"}, 400)
                return

            reports_path = os.path.join(DATA_DIR, 'reports.json')
            
            reports = []
            if os.path.exists(reports_path):
                try:
                    with open(reports_path, 'r', encoding='utf-8') as f:
                        reports = json.load(f)
                except Exception:
                    pass

            reports.append(data)

            try:
                with open(reports_path, 'w', encoding='utf-8') as f:
                    json.dump(reports, f, indent=2)
                self.send_json_response({"status": "success"}, 200)
            except Exception as e:
                self.send_json_response({"status": "error", "message": f"Failed to save report: {str(e)}"}, 500)
            return

        # Otherwise 404
        self.send_error(404, "File not found")

    def do_DELETE(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query = urllib.parse.parse_qs(parsed_url.query)

        if path == '/api/reports':
            report_id = query.get('id', [None])[0]
            if not report_id:
                self.send_json_response({"status": "error", "message": "Report ID is required"}, 400)
                return

            reports_path = os.path.join(DATA_DIR, 'reports.json')
            if not os.path.exists(reports_path):
                self.send_json_response({"status": "error", "message": "No reports database found"}, 404)
                return

            try:
                with open(reports_path, 'r', encoding='utf-8') as f:
                    reports = json.load(f)
            except Exception:
                self.send_json_response({"status": "error", "message": "Failed to read database"}, 500)
                return

            new_reports = [r for r in reports if r.get('id') != report_id]

            if len(new_reports) == len(reports):
                self.send_json_response({"status": "error", "message": "Report not found"}, 404)
                return

            try:
                with open(reports_path, 'w', encoding='utf-8') as f:
                    json.dump(new_reports, f, indent=2)
                self.send_json_response({"status": "success", "message": "Report deleted"}, 200)
            except Exception as e:
                self.send_json_response({"status": "error", "message": f"Failed to update database: {str(e)}"}, 500)
            return

        self.send_error(404, "File not found")

def run():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    
    if not os.path.exists(PUBLIC_DIR):
        os.makedirs(PUBLIC_DIR)
        
    server_address = ('', PORT)
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(server_address, CustomHandler) as httpd:
        print(f"Starting CipherGuard local server on http://localhost:{PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server...")

if __name__ == '__main__':
    run()
