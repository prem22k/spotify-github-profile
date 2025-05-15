from http.server import BaseHTTPRequestHandler
import json
import sys
import os
import traceback

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import our Flask app
try:
    from index import app
    
    class VercelHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            try:
                # Simple test response
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b'Hello from Vercel Serverless Function!')
                
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                error_msg = f"Error in handler: {str(e)}\n{traceback.format_exc()}"
                print(error_msg)
                self.wfile.write(f"""
                <html>
                    <body>
                        <h1>Server Error</h1>
                        <p>{str(e)}</p>
                        <pre>{traceback.format_exc()}</pre>
                    </body>
                </html>
                """.encode('utf-8'))
    
    def handler(request, response):
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'text/html',
            },
            'body': 'Hello from Vercel Function!'
        }
        
except Exception as init_error:
    def handler(request, response):
        error_msg = f"Initialization error: {str(init_error)}\n{traceback.format_exc()}"
        print(error_msg)
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'text/html',
            },
            'body': f"""
            <html>
                <body>
                    <h1>Initialization Error</h1>
                    <p>{str(init_error)}</p>
                    <pre>{traceback.format_exc()}</pre>
                </body>
            </html>
            """
        } 