# Custom HTTP Server

A lightweight, extensible HTTP server written in Python with support for static file serving, directory listing, custom routes, and middleware.

## Features

- **Static File Serving**: Automatically serves files from the configured document root
- **Directory Listing**: Generates clean HTML directory listings when accessing folders
- **Custom Routes**: Define custom API endpoints with specific HTTP methods
- **Middleware Support**: Add request processing middleware for logging, authentication, etc.
- **Threading**: Handles multiple concurrent connections using Python threads
- **Content Type Detection**: Automatically detects and sets appropriate MIME types
- **Security**: Basic protection against directory traversal attacks

## Requirements

```
Python 3.6+
```

No external dependencies required! This server uses only Python standard libraries:
- socket
- threading
- os
- json
- mimetypes
- urllib.parse
- datetime

## Installation

1. Clone the repository:


2. No installation steps required - the server is ready to use!

## Usage

### Basic Usage

```python
from server import Server

# Create a server instance
server = Server(host='localhost', port=8080, document_root='./public')

# Start the server
server.start()
```

### Adding Custom Routes

```python
def hello_handler(request):
    return server.build_response(
        200, "OK", 
        "Hello, World!", 
        {'Content-Type': 'text/plain'}
    )

# Register the route
server.add_route('/hello', hello_handler, 'GET')
```

### Adding Middleware

```python
def auth_middleware(request):
    # Check for authorization header
    if 'authorization' not in request['headers']:
        return None  # Return None to end request processing
    return request  # Continue processing

server.add_middleware(auth_middleware)
```

## Project Structure

- `server.py` - Main server implementation
- `public/` - Default document root for static files
  - `index.html` - Example welcome page

## API Reference

### Server Class

- `__init__(host='localhost', port=8080, document_root='./public')` - Initialize server
- `add_route(path, handler, method='GET')` - Register custom route
- `add_middleware(middleware)` - Add request middleware
- `start()` - Start the server and listen for connections
- `build_response(status, status_text, body=None, headers=None)` - Helper to build HTTP responses

### Request Object

The request object passed to handlers and middleware is a dictionary with these keys:
- `method` - HTTP method (GET, POST, etc.)
- `path` - Request path
- `version` - HTTP version
- `headers` - Dictionary of request headers
- `body` - Request body
- `query_params` - Dictionary of query parameters

## Example

The server comes with an example API endpoint at `/api/hello` that returns JSON data.

To run the example:

```bash
python server.py
```

Then visit:
- http://localhost:8080/ - See the welcome page
- http://localhost:8080/api/hello - Test the API endpoint


## Author

Islam