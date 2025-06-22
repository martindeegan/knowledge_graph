#!/usr/bin/env python3
"""
Simple server to serve the Knowledge Engine frontend
"""
import argparse
import webbrowser
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
import os

def main():
    parser = argparse.ArgumentParser(description='Knowledge Engine Frontend Server')
    parser.add_argument('--api', default='http://127.0.0.1:6969', 
                       help='Knowledge Engine API URL (default: http://127.0.0.1:6969)')
    parser.add_argument('--port', type=int, default=3000,
                       help='Port to run the frontend on (default: 3000)')
    parser.add_argument('--no-open', action='store_true',
                       help='Do not automatically open browser')
    
    args = parser.parse_args()
    
    # Change to the frontend directory
    frontend_dir = Path(__file__).parent
    os.chdir(frontend_dir)
    
    print(f"Knowledge Engine Frontend Server")
    print(f"Frontend URL: http://localhost:{args.port}")
    print(f"API Backend: {args.api}")
    print(f"Serving from: {frontend_dir}")
    print(f"\nConnect the frontend to your API by entering: {args.api}")
    print("Press Ctrl+C to stop the server")
    
    # Create a custom handler that serves our HTML file as index
    class KnowledgeEngineHandler(SimpleHTTPRequestHandler):
        def end_headers(self):
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', '*')
            super().end_headers()
        
        def do_GET(self):
            if self.path == '/' or self.path == '/index.html':
                self.path = '/frontend.html'
            return super().do_GET()
    
    # Start the server
    server = HTTPServer(('localhost', args.port), KnowledgeEngineHandler)
    
    if not args.no_open:
        webbrowser.open(f'http://localhost:{args.port}')
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.shutdown()

if __name__ == '__main__':
    main() 