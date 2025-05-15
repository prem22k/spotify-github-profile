import sys
import os
import traceback

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from index import app
    
    # WSGI handler for Vercel
    def handler(environ, start_response):
        try:
            return app.wsgi_app(environ, start_response)
        except Exception as e:
            # Log the error
            error_msg = f"WSGI handler error: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            
            # Return a 500 error response
            start_response('500 Internal Server Error', [
                ('Content-Type', 'text/html')
            ])
            return [f"""
            <html>
                <body>
                    <h1>Internal Server Error</h1>
                    <p>{str(e)}</p>
                    <pre>{traceback.format_exc()}</pre>
                </body>
            </html>
            """.encode('utf-8')]

except Exception as init_error:
    # This handles any errors during import
    def handler(environ, start_response):
        start_response('500 Internal Server Error', [
            ('Content-Type', 'text/html')
        ])
        error_msg = f"Failed to initialize app: {str(init_error)}\n{traceback.format_exc()}"
        print(error_msg)
        return [f"""
        <html>
            <body>
                <h1>Initialization Error</h1>
                <p>{str(init_error)}</p>
                <pre>{traceback.format_exc()}</pre>
            </body>
        </html>
        """.encode('utf-8')] 