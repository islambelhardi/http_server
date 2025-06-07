import json
import socket
import threading
import os
import mimetypes
import urllib.parse
from datetime import datetime


class Server:
    def __init__(self,host='localhost',port=8080,document_root='./public'):
        self.host = host
        self.port = port
        self.document_root = os.path.abspath(document_root)
        self.socket = None
        self.routes= {}
        self.middleware= []

        # ensure document root exists
        os.makedirs(self.document_root, exist_ok=True)

    def add_route(self,path,handler,method= 'GET'):
        """Add a custom route handler"""
        if path not in self.routes:
            self.routes[path] = {}

        self.routes[path][method] = handler

    def add_middleware(self,middleware):
        """Add a custom middleware"""
        self.middleware.append(middleware)

    def start(self):
        """Start the server"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print('Socket created')
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            self.socket.bind((self.host, self.port))
            self.socket.listen(5)
            print(f"Server starting on http://{self.host}:{self.port}")
            print(f"Documents root is {self.document_root}")
            print('Press Ctrl+C to exit')

            while True:
                client_socket, address = self.socket.accept()
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, address)
                )
                client_thread.daemon = True
                client_thread.start()

        except KeyboardInterrupt:
            print('Server stopped')
        except Exception as e:
            print(f"Server error: {e}")
        finally:
            if self.socket:
                self.socket.close()

    def handle_client(self,client_socket, address):
        """Handle a client connection"""
        try:
            request_data = client_socket.recv(4096).decode('utf-8')
            if not request_data:
                return

            request = self.parse_request(request_data)
            if not request:
                self.send_error(client_socket,400,"Bad Request")
                return

            #apply moddleware
            for middleware in self.middleware:
                request = middleware(request)
                if request is None:
                    return

            response = self.route_request(request)

            #send response
            client_socket.send(response.encode('utf-8'))

        except Exception as e:
            print(f"Server error: {e}")
            self.send_error(client_socket,500,"Internal Server Error")

        finally:
            client_socket.close()

    def parse_request(self,data):
        """Parse a request into a disctionary"""
        lines = data.split('\r\n')
        if not lines:
            return None

        request_line = lines[0].split()
        if len(request_line) != 3:
            return None

        method, path, version = request_line

        # Parse headers
        headers = {}
        body = ""
        body_start = False

        for line in lines[1:]:
            if not body_start:
                if line == "":  # Empty line indicates start of body
                    body_start = True
                    continue
                if ':' in line:
                    key, value = line.split(':', 1)
                    headers[key.strip().lower()] = value.strip()
            else:
                body += line + '\r\n'

            # Parse query parameters
        if '?' in path:
            path, query_string = path.split('?', 1)
            query_params = urllib.parse.parse_qs(query_string)
        else:
            query_params = {}

        return {
            'method': method,
            'path': path,
            'version': version,
            'headers': headers,
            'body': body.strip(),
            'query_params': query_params,
            'client_ip': None  # Would need to be set by caller
        }

    def route_request(self, request):
        """Route request to appropriate handler"""
        path = request['path']
        method = request['method']

        # Check custom routes first
        if path in self.routes and method in self.routes[path]:
            try:
                return self.routes[path][method](request)
            except Exception as e:
                print(f"❌ Route handler error: {e}")
                return self.build_response(500, "Internal Server Error")

        # Handle static files
        if method == 'GET':
            return self.serve_static_file(path)

        # Method not allowed
        return self.build_response(405, "Method Not Allowed")

    def serve_static_file(self, path):
        """Serve static files from document root"""
        # Remove leading slash and resolve path
        if path.startswith('/'):
            path = path[1:]

        if path == '' or path.endswith('/'):
            path += 'index.html'

        file_path = os.path.join(self.document_root, path)

        # Security check - prevent directory traversal
        if not os.path.abspath(file_path).startswith(self.document_root):
            return self.build_response(403, "Forbidden")

        try:
            if os.path.isfile(file_path):
                with open(file_path, 'rb') as f:
                    content = f.read()

                # Determine content type
                content_type, _ = mimetypes.guess_type(file_path)
                if content_type is None:
                    content_type = 'application/octet-stream'

                return self.build_response(
                    200, "OK",
                    content,
                    {'Content-Type': content_type}
                )

            elif os.path.isdir(file_path):
                # Directory listing
                return self.generate_directory_listing(path, file_path)

            else:
                return self.build_response(404, "Not Found")

        except PermissionError:
            return self.build_response(403, "Forbidden")
        except Exception as e:
            print(f"❌ File serving error: {e}")
            return self.build_response(500, "Internal Server Error")

    def generate_directory_listing(self, url_path, file_path):
        """Generate HTML directory listing"""
        try:
            files = sorted(os.listdir(file_path))
            html = f"""<!DOCTYPE html>
    <html>
    <head>
        <title>Directory listing for /{url_path}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            h1 {{ color: #333; }}
            ul {{ list-style-type: none; padding: 0; }}
            li {{ margin: 5px 0; }}
            a {{ text-decoration: none; color: #0066cc; }}
            a:hover {{ text-decoration: underline; }}
            .file {{ color: #666; }}
            .dir {{ color: #0066cc; font-weight: bold; }}
        </style>
    </head>
    <body>
        <h1>Directory listing for /{url_path}</h1>
        <ul>
    """

            if url_path:  # Add parent directory link
                html += '<li><a href="../" class="dir">📁 ..</a></li>\n'

            for filename in files:
                full_path = os.path.join(file_path, filename)
                if os.path.isdir(full_path):
                    html += f'<li><a href="{filename}/" class="dir">📁 {filename}/</a></li>\n'
                else:
                    html += f'<li><a href="{filename}" class="file">📄 {filename}</a></li>\n'

            html += """    </ul>
    </body>
    </html>"""

            return self.build_response(200, "OK", html.encode('utf-8'), {'Content-Type': 'text/html'})

        except Exception as e:
            print(f"❌ Directory listing error: {e}")
            return self.build_response(500, "Internal Server Error")

    def build_response(self, status, status_text, body=None, headers=None):
        """Build HTTP response string"""
        if body is None:
            body = f"<h1>{status} {status_text}</h1>".encode('utf-8')
        elif isinstance(body, str):
            body = body.encode('utf-8')

        if headers is None:
            headers = {}

        # Default headers
        default_headers = {
            'Server': 'MYHttpServer/1.0',
            'Date': datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT'),
            'Content-Length': str(len(body)),
            'Connection': 'close',
            'author':'Islam'
        }

        # Merge headers
        response_headers = {**default_headers, **headers}

        # Build response
        response = f"HTTP/1.1 {status} {status_text}\r\n"
        for key, value in response_headers.items():
            response += f"{key}: {value}\r\n"
        response += "\r\n"

        # Add body
        response = response.encode('utf-8') + body
        return response.decode('utf-8', errors='ignore')

    def send_error(self, client_socket, status, status_text):
        """Send error response"""
        response = self.build_response(status, status_text)
        try:
            client_socket.send(response.encode('utf-8'))
        except:
            pass


# Example usage and demo routes
def demo_api_handler(request):
    """Example API endpoint"""
    data = {
        'message': 'Hello from the API!',
        'method': request['method'],
        'path': request['path'],
        'timestamp': datetime.now().isoformat()
    }

    json_data = json.dumps(data, indent=2)
    return server.build_response(
        200, "OK",
        json_data,
        {'Content-Type': 'application/json'}
    )


def logging_middleware(request):
    """Log all requests"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {request['method']} {request['path']}")
    return request


if __name__ == "__main__":
    server = Server(host='localhost', port=8080, document_root='./public')

    # Add custom routes
    server.add_route('/api/hello', demo_api_handler, 'GET')

    # Add middleware
    server.add_middleware(logging_middleware)

    server.start()