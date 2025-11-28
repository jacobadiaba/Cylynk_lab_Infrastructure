#!/usr/bin/env python3
"""
Simple HTTP server to serve the CyberLab test app.
Run: python serve.py
Then open: http://localhost:8080
"""

import http.server
import socketserver
import os
import sys

PORT = 8080

# Change to the script's directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

class CORSRequestHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP handler with CORS headers for local development."""
    
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Api-Key')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        super().end_headers()
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

def main():
    with socketserver.TCPServer(("", PORT), CORSRequestHandler) as httpd:
        print(f"""
================================================================
                                                              
           CyberLab Test App - Local Server                   
                                                              
   Open in browser: http://localhost:{PORT}                    
                                                              
   Press Ctrl+C to stop the server                            
                                                              
================================================================
        """)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")
            sys.exit(0)

if __name__ == "__main__":
    main()

