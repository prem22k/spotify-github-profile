import sys
import os
import json
import requests
import traceback
import random
import html
from base64 import b64decode, b64encode
import functools
from flask import Flask, Response, redirect

# Add the directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Try to import from util
try:
    from util import spotify
except ImportError as e:
    print(f"Error importing spotify module: {str(e)}")
    
# Try to import firebase
try:
    import firebase_admin
    from firebase_admin import credentials
    from firebase_admin import firestore
    
    # Initialize Firebase
    firebase_config = os.environ.get("FIREBASE")
    if firebase_config:
        firebase_dict = json.loads(b64decode(firebase_config))
        cred = credentials.Certificate(firebase_dict)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
    else:
        print("FIREBASE environment variable not set")
        db = None
except ImportError as e:
    print(f"Error importing Firebase: {str(e)}")
    db = None

# Check for template directory
template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
print(f"Template directory: {template_dir}")
print(f"Available templates: {os.listdir(template_dir) if os.path.exists(template_dir) else 'Directory not found!'}")

# Utils
def encode_html_entities(text):
    return html.escape(text)

def generate_css_bar(num_bar=75):
    css_bar = ""
    left = 1
    for i in range(1, num_bar + 1):
        anim = random.randint(350, 500)
        css_bar += ".bar:nth-child({})  {{ left: {}px; animation-duration: {}ms; }}".format(
            i, left, anim
        )
        left += 4
    return css_bar

def make_simple_svg(artist_name, song_name, is_now_playing, theme="default", bar_color="53b14f", background_color="121212"):
    """Generate a simple SVG without using templates"""
    height = 145
    
    # Sanitize input
    artist_name = encode_html_entities(artist_name)
    song_name = encode_html_entities(song_name)
    
    title_text = "Now playing" if is_now_playing else "Recently played"
    
    # Create a simple SVG directly
    return f"""<svg width="320" height="{height}" xmlns="http://www.w3.org/2000/svg">
        <style>
            .container {{ background-color: #{background_color}; border-radius: 10px; padding: 10px; }}
            .title {{ color: #53b14f; font-weight: bold; text-align: center; margin-bottom: 8px; font-family: sans-serif; }}
            .artist {{ color: #fff; font-weight: bold; font-size: 20px; text-align: center; margin-bottom: 5px; font-family: sans-serif; }}
            .song {{ color: #b3b3b3; font-size: 16px; text-align: center; margin-bottom: 22px; font-family: sans-serif; }}
            .bar {{ background: #{bar_color}; bottom: 1px; height: 3px; position: absolute; width: 3px; animation: sound 0ms -800ms linear infinite alternate; }}
            @keyframes sound {{ 0% {{ opacity: .35; height: 3px; }} 100% {{ opacity: 1; height: 22px; }} }}
        </style>
        <rect width="320" height="{height}" fill="#{background_color}" rx="10" />
        <text x="160" y="30" fill="#53b14f" text-anchor="middle" font-family="sans-serif" font-weight="bold">{title_text} on Spotify</text>
        <text x="160" y="70" fill="#ffffff" text-anchor="middle" font-family="sans-serif" font-weight="bold" font-size="20">{artist_name}</text>
        <text x="160" y="100" fill="#b3b3b3" text-anchor="middle" font-family="sans-serif" font-size="16">{song_name}</text>
    </svg>"""

def get_access_token(uid):
    """Get access token from Firestore"""
    if not db:
        return None
        
    doc_ref = db.collection("users").document(uid)
    doc = doc_ref.get()
    
    if not doc.exists:
        return None
        
    token_info = doc.to_dict()
    return token_info.get("access_token")

def handle_login(request):
    """Handle login redirect to Spotify"""
    login_url = f"https://accounts.spotify.com/authorize?client_id={spotify.SPOTIFY_CLIENT_ID}&response_type=code&scope=user-read-currently-playing,user-read-recently-played&redirect_uri={spotify.REDIRECT_URI}"
    
    return {
        'statusCode': 302,
        'headers': {
            'Location': login_url,
        },
        'body': ''
    }

def handle_callback(request):
    """Handle Spotify OAuth callback"""
    # Extract query parameters
    query = request.get('query', {})
    code = query.get('code')
    
    if not code:
        return {
            'statusCode': 400,
            'body': 'No authorization code provided'
        }
    
    try:
        # Generate token from code
        token_info = spotify.generate_token(code)
        access_token = token_info["access_token"]
        
        # Get user profile
        spotify_user = spotify.get_user_profile(access_token)
        user_id = spotify_user["id"]
        
        # Store token in Firebase
        if db:
            doc_ref = db.collection("users").document(user_id)
            doc_ref.set(token_info)
        
        # Return simple HTML response
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'text/html',
            },
            'body': f"""
            <html>
                <body>
                    <h1>Successfully authenticated with Spotify!</h1>
                    <p>Your user ID: {user_id}</p>
                    <p>To create your Spotify GitHub profile, use this URL:</p>
                    <code>{spotify.BASE_URL}?uid={user_id}</code>
                    <p>Add it to your GitHub profile README.md using this Markdown:</p>
                    <pre>![Spotify Recently Played]({spotify.BASE_URL}?uid={user_id})</pre>
                </body>
            </html>
            """
        }
    except Exception as e:
        traceback_str = traceback.format_exc()
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
            },
            'body': json.dumps({
                'error': str(e),
                'traceback': traceback_str
            })
        }

def handle_view(request):
    """Handle main view to generate Spotify SVG"""
    # Extract query parameters
    query = request.get('query', {})
    uid = query.get('uid')
    theme = query.get('theme', 'default')
    bar_color = query.get('bar_color', '53b14f')
    background_color = query.get('background_color', '121212')
    
    if not uid:
        return {
            'statusCode': 400,
            'body': 'Error: Missing uid parameter'
        }
    
    try:
        # Get access token
        access_token = get_access_token(uid)
        
        if not access_token:
            return {
                'statusCode': 400,
                'body': 'Error: User not found or invalid token'
            }
        
        # Get current playing or recent track
        now_playing = spotify.get_now_playing(access_token)
        
        if now_playing and 'item' in now_playing:
            item = now_playing['item']
            is_now_playing = True
        else:
            # Get recently played
            recent = spotify.get_recently_play(access_token)
            if recent and 'items' in recent and len(recent['items']) > 0:
                item = recent['items'][0]['track']
                is_now_playing = False
            else:
                return {
                    'statusCode': 404,
                    'body': 'No recent tracks found'
                }
        
        # Extract artist and song name
        if 'artists' in item:
            # It's a track
            artist_name = item['artists'][0]['name']
            song_name = item['name']
        elif 'show' in item:
            # It's a podcast/episode
            artist_name = item['show']['publisher']
            song_name = item['name']
        else:
            artist_name = "Unknown Artist"
            song_name = item.get('name', 'Unknown Track')
        
        # Generate SVG
        svg = make_simple_svg(
            artist_name,
            song_name,
            is_now_playing,
            theme,
            bar_color,
            background_color
        )
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'image/svg+xml',
                'Cache-Control': 's-maxage=1'
            },
            'body': svg
        }
            
    except Exception as e:
        traceback_str = traceback.format_exc()
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
            },
            'body': json.dumps({
                'error': str(e),
                'traceback': traceback_str,
                'message': 'Error generating Spotify card'
            })
        }

def handler(request, response):
    """Main handler for all Vercel requests"""
    try:
        path = request.get('path', '')
        
        if path == '/api/login':
            return handle_login(request)
        elif path == '/api/callback':
            return handle_callback(request)
        else:
            return handle_view(request)
            
    except Exception as e:
        traceback_str = traceback.format_exc()
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
            },
            'body': json.dumps({
                'error': str(e),
                'traceback': traceback_str
            })
        } 