import os
import json
import base64
import requests
import traceback
from urllib.parse import parse_qs

# Debug info
print("Starting server...")

# Environment variables
SPOTIFY_CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID")
SPOTIFY_SECRET_ID = os.environ.get("SPOTIFY_SECRET_ID")
BASE_URL = os.environ.get("BASE_URL", "https://spotify-github-profile-kappa-six.vercel.app/api")
FIREBASE_CONFIG = os.environ.get("FIREBASE")

# Initialize Firebase if available
db = None
try:
    if FIREBASE_CONFIG:
        import firebase_admin
        from firebase_admin import credentials
        from firebase_admin import firestore
        
        firebase_dict = json.loads(base64.b64decode(FIREBASE_CONFIG))
        cred = credentials.Certificate(firebase_dict)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("Firebase initialized successfully")
    else:
        print("FIREBASE_CONFIG not found")
except Exception as e:
    print(f"Firebase initialization error: {str(e)}")

# Spotify API endpoints
SPOTIFY_URL_REFRESH_TOKEN = "https://accounts.spotify.com/api/token"
SPOTIFY_URL_NOW_PLAYING = "https://api.spotify.com/v1/me/player/currently-playing"
SPOTIFY_URL_RECENTLY_PLAY = "https://api.spotify.com/v1/me/player/recently-played?limit=10"
SPOTIFY_URL_GENERATE_TOKEN = "https://accounts.spotify.com/api/token"
SPOTIFY_URL_USER_INFO = "https://api.spotify.com/v1/me"

# Redirect URI for Spotify OAuth
REDIRECT_URI = f"{BASE_URL}/callback"

# Helper functions
def get_authorization():
    return base64.b64encode(f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_SECRET_ID}".encode()).decode("ascii")

def generate_token(code):
    data = {
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
        "code": code,
    }
    headers = {"Authorization": f"Basic {get_authorization()}"}
    response = requests.post(SPOTIFY_URL_GENERATE_TOKEN, data=data, headers=headers)
    return response.json()

def refresh_token(refresh_token):
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    headers = {"Authorization": f"Basic {get_authorization()}"}
    response = requests.post(SPOTIFY_URL_REFRESH_TOKEN, data=data, headers=headers)
    return response.json()

def get_user_profile(access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(SPOTIFY_URL_USER_INFO, headers=headers)
    return response.json()

def get_now_playing(access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(SPOTIFY_URL_NOW_PLAYING, headers=headers)
    if response.status_code == 204:
        return {}
    return response.json()

def get_recently_played(access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(SPOTIFY_URL_RECENTLY_PLAY, headers=headers)
    if response.status_code == 204:
        return {}
    return response.json()

def get_access_token(uid):
    """Get access token from Firebase"""
    if not db:
        return None
        
    try:
        doc_ref = db.collection("users").document(uid)
        doc = doc_ref.get()
        
        if not doc.exists:
            print(f"User {uid} not found in database")
            return None
            
        token_info = doc.to_dict()
        return token_info.get("access_token")
    except Exception as e:
        print(f"Error getting access token: {str(e)}")
        return None

def create_spotify_svg(artist_name, song_name, is_playing=False, theme="default", bar_color="53b14f", background_color="121212"):
    """Create an SVG showing Spotify information"""
    title_text = "Now playing" if is_playing else "Recently played"
    
    return f"""<svg width="320" height="145" xmlns="http://www.w3.org/2000/svg">
        <style>
            .container {{ background-color: #{background_color}; border-radius: 10px; padding: 10px; }}
            .title {{ color: #53b14f; font-weight: bold; text-align: center; font-family: sans-serif; }}
            .artist {{ color: #fff; font-weight: bold; font-size: 20px; text-align: center; font-family: sans-serif; }}
            .song {{ color: #b3b3b3; font-size: 16px; text-align: center; font-family: sans-serif; }}
        </style>
        <rect width="320" height="145" fill="#{background_color}" rx="10" />
        <text x="160" y="30" fill="#53b14f" text-anchor="middle" font-family="sans-serif" font-weight="bold">{title_text} on Spotify</text>
        <text x="160" y="70" fill="#ffffff" text-anchor="middle" font-family="sans-serif" font-weight="bold" font-size="20">{artist_name}</text>
        <text x="160" y="100" fill="#b3b3b3" text-anchor="middle" font-family="sans-serif" font-size="16">{song_name}</text>
    </svg>"""

# Route handlers
def handle_login():
    """Handle the /login endpoint to redirect to Spotify"""
    login_url = f"https://accounts.spotify.com/authorize?client_id={SPOTIFY_CLIENT_ID}&response_type=code&scope=user-read-currently-playing,user-read-recently-played&redirect_uri={REDIRECT_URI}"
    
    return {
        "statusCode": 302,
        "headers": {
            "Location": login_url
        },
        "body": ""
    }

def handle_callback(query_params):
    """Handle the /callback endpoint for Spotify OAuth redirect"""
    code = query_params.get("code", [""])[0]
    
    if not code:
        return {
            "statusCode": 400,
            "body": "No authorization code provided"
        }
    
    try:
        # Exchange code for token
        token_info = generate_token(code)
        access_token = token_info.get("access_token")
        
        if not access_token:
            return {
                "statusCode": 400,
                "body": "Failed to get access token"
            }
        
        # Get user profile to get the Spotify user ID
        user_info = get_user_profile(access_token)
        user_id = user_info.get("id")
        
        if not user_id:
            return {
                "statusCode": 400,
                "body": "Failed to get user profile"
            }
        
        # Store token in Firebase
        if db:
            doc_ref = db.collection("users").document(user_id)
            doc_ref.set(token_info)
            print(f"Saved token for user {user_id}")
        
        # Return success HTML
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "text/html"
            },
            "body": f"""
            <html>
                <body style="font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px;">
                    <h1 style="color: #1DB954;">Successfully connected with Spotify!</h1>
                    <p>Your Spotify user ID: <strong>{user_id}</strong></p>
                    <p>To add this to your GitHub profile, use this URL in an img tag:</p>
                    <code style="background: #f1f1f1; padding: 10px; display: block;">{BASE_URL}?uid={user_id}</code>
                    <p>Or add this markdown to your README.md:</p>
                    <pre style="background: #f1f1f1; padding: 10px;">![Spotify Recently Played]({BASE_URL}?uid={user_id})</pre>
                </body>
            </html>
            """
        }
    except Exception as e:
        traceback_str = traceback.format_exc()
        print(f"Callback error: {str(e)}\n{traceback_str}")
        
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "text/html"
            },
            "body": f"""
            <html>
                <body>
                    <h1>Error processing Spotify callback</h1>
                    <p>{str(e)}</p>
                    <pre>{traceback_str}</pre>
                </body>
            </html>
            """
        }

def handle_main_view(query_params):
    """Handle the main view to generate Spotify SVG"""
    uid = query_params.get("uid", [""])[0]
    theme = query_params.get("theme", ["default"])[0]
    bar_color = query_params.get("bar_color", ["53b14f"])[0]
    background_color = query_params.get("background_color", ["121212"])[0]
    
    if not uid:
        return {
            "statusCode": 400,
            "body": "Error: Missing uid parameter"
        }
    
    try:
        # Get access token
        access_token = get_access_token(uid)
        
        if not access_token:
            return {
                "statusCode": 400,
                "body": "Error: User not found or invalid token"
            }
        
        # Try to get currently playing track
        now_playing = get_now_playing(access_token)
        
        if now_playing and 'item' in now_playing:
            item = now_playing['item']
            is_playing = True
        else:
            # Fallback to recently played
            recent = get_recently_played(access_token)
            if recent and 'items' in recent and len(recent['items']) > 0:
                item = recent['items'][0]['track']
                is_playing = False
            else:
                # No track found
                return {
                    "statusCode": 200,
                    "headers": {
                        "Content-Type": "image/svg+xml"
                    },
                    "body": create_spotify_svg("Not playing", "No recent tracks", False, theme, bar_color, background_color)
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
        svg = create_spotify_svg(
            artist_name,
            song_name,
            is_playing,
            theme,
            bar_color,
            background_color
        )
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "image/svg+xml",
                "Cache-Control": "s-maxage=1"
            },
            "body": svg
        }
    except Exception as e:
        traceback_str = traceback.format_exc()
        print(f"View error: {str(e)}\n{traceback_str}")
        
        # Return an error SVG
        error_svg = f"""<svg width="320" height="145" xmlns="http://www.w3.org/2000/svg">
            <rect width="320" height="145" fill="#121212" rx="10" />
            <text x="160" y="50" fill="#ff5555" text-anchor="middle" font-family="sans-serif" font-weight="bold">Error fetching Spotify data</text>
            <text x="160" y="80" fill="#ffffff" text-anchor="middle" font-family="sans-serif" font-size="12">{str(e)[:30]}...</text>
        </svg>"""
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "image/svg+xml"
            },
            "body": error_svg
        }

def handler(req, res):
    """Main handler for Vercel serverless function"""
    try:
        # Extract path and query parameters
        path = req.get("path", "")
        
        # Parse query string
        url = req.get("url", "")
        query_string = url.split("?")[1] if "?" in url else ""
        query_params = {}
        
        if query_string:
            query_params = parse_qs(query_string)
        
        # Log request info
        print(f"Handling request: {path} with params: {query_params}")
        
        # Route based on path
        if path == "/api/login":
            return handle_login()
        elif path == "/api/callback":
            return handle_callback(query_params)
        else:
            return handle_main_view(query_params)
            
    except Exception as e:
        traceback_str = traceback.format_exc()
        print(f"Handler error: {str(e)}\n{traceback_str}")
        
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
                    <pre>{traceback_str}</pre>
                </body>
            </html>
            """
        } 