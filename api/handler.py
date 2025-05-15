import os
import sys
import json
import traceback

# For debugging
print("Python version:", sys.version)
print("Current directory:", os.getcwd())
print("Files in directory:", os.listdir("."))
print("Files in /api:", os.listdir("api") if os.path.exists("api") else "api directory not found")

def create_svg(artist_name="Unknown Artist", song_name="Not Playing", is_playing=False):
    """Create a simple SVG showing Spotify information"""
    title_text = "Now playing" if is_playing else "Recently played"
    
    return f"""<svg width="320" height="145" xmlns="http://www.w3.org/2000/svg">
        <rect width="320" height="145" fill="#121212" rx="10" />
        <text x="160" y="30" fill="#53b14f" text-anchor="middle" font-family="sans-serif" font-weight="bold">{title_text} on Spotify</text>
        <text x="160" y="70" fill="#ffffff" text-anchor="middle" font-family="sans-serif" font-weight="bold" font-size="20">{artist_name}</text>
        <text x="160" y="100" fill="#b3b3b3" text-anchor="middle" font-family="sans-serif" font-size="16">{song_name}</text>
    </svg>"""

# Handler for Vercel
def handler(request, response):
    """Simple handler that returns a static SVG for testing"""
    try:
        # Return a simple SVG with hardcoded data for testing
        svg = create_svg("Demo Artist", "Demo Track", True)
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "image/svg+xml"
            },
            "body": svg
        }
    except Exception as e:
        error_msg = f"Handler error: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "text/html"
            },
            "body": f"""
            <html>
                <body>
                    <h1>Server Error</h1>
                    <p>{str(e)}</p>
                    <pre>{traceback.format_exc()}</pre>
                </body>
            </html>
            """
        } 