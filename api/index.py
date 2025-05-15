from flask import Flask, Response, redirect, request, jsonify, render_template
import os
import sys
import traceback

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the necessary modules
from util import spotify
from base64 import b64decode, b64encode
import json
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import requests
import random
import html
import functools

# Flag to track if PIL is available
PIL_AVAILABLE = False
try:
    from PIL import Image, ImageFile
    ImageFile.LOAD_TRUNCATED_IMAGES = True
    PIL_AVAILABLE = True
except ImportError:
    print("PIL could not be imported - image processing features will be limited")

# Initialize Firebase
try:
    firebase_config = os.environ.get("FIREBASE")
    if firebase_config:
        firebase_dict = json.loads(b64decode(firebase_config))
        cred = credentials.Certificate(firebase_dict)
        firebase_admin.initialize_app(cred)
except Exception as e:
    print(f"Firebase initialization error: {str(e)}")

# Set up Flask app with proper template folder
template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=template_dir)

# Print debug info
print(f"Template directory: {template_dir}")
print(f"Available templates: {os.listdir(template_dir) if os.path.exists(template_dir) else 'Directory not found!'}")

# Cache for token info
CACHE_TOKEN_INFO = {}

@functools.lru_cache(maxsize=128)
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

def encode_html_entities(text):
    return html.escape(text)

def to_img_b64(content):
    return b64encode(content).decode("ascii")

@functools.lru_cache(maxsize=128)
def load_image(url):
    response = requests.get(url)
    return response.content

def make_simple_svg(artist_name, song_name, is_now_playing, theme="default", bar_color="53b14f", background_color="121212"):
    """Simplified SVG generator that doesn't require PIL"""
    
    height = 145
    num_bar = 75

    # Sanitize input
    artist_name = encode_html_entities(artist_name)
    song_name = encode_html_entities(song_name)
    
    if is_now_playing:
        title_text = "Now playing"
        content_bar = "".join(["<div class='bar'></div>" for i in range(num_bar)])
        css_bar = generate_css_bar(num_bar)
    else:
        title_text = "Recently played"
        content_bar = ""
        css_bar = generate_css_bar(num_bar)
    
    rendered_data = {
        "height": height,
        "num_bar": num_bar,
        "content_bar": content_bar,
        "css_bar": css_bar,
        "title_text": title_text,
        "artist_name": artist_name,
        "song_name": song_name,
        "img": "",
        "cover_image": False,
        "bar_color": bar_color,
        "background_color": background_color,
    }
    
    try:
        return render_template(f"spotify.{theme}.html.j2", **rendered_data)
    except Exception as e:
        print(f"Template rendering error: {str(e)}")
        # Fallback to simpler rendering if template not found
        return f"""<svg width="320" height="145" xmlns="http://www.w3.org/2000/svg">
            <rect width="320" height="145" fill="#{background_color}" rx="10" />
            <text x="160" y="45" fill="#53b14f" text-anchor="middle" font-family="sans-serif" font-weight="bold">{title_text} on Spotify</text>
            <text x="160" y="85" fill="#ffffff" text-anchor="middle" font-family="sans-serif" font-weight="bold" font-size="20">{artist_name}</text>
            <text x="160" y="115" fill="#b3b3b3" text-anchor="middle" font-family="sans-serif" font-size="16">{song_name}</text>
        </svg>"""

def get_cache_token_info(uid):
    token_info = CACHE_TOKEN_INFO.get(uid, None)
    return token_info

def delete_cache_token_info(uid):
    if uid in CACHE_TOKEN_INFO:
        del CACHE_TOKEN_INFO[uid]

def get_access_token(uid):
    # Get firestore database
    db = firestore.client()
    
    # Load from firebase
    doc_ref = db.collection("users").document(uid)
    doc = doc_ref.get()
    
    if not doc.exists:
        print("User not found in database: {}".format(uid))
        return None
    
    token_info = doc.to_dict()
    access_token = token_info.get("access_token")
    
    return access_token

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def catch_all(path):
    """Main handler for all routes"""
    try:
        # Login route
        if path == "login":
            login_url = f"https://accounts.spotify.com/authorize?client_id={spotify.SPOTIFY_CLIENT_ID}&response_type=code&scope=user-read-currently-playing,user-read-recently-played&redirect_uri={spotify.REDIRECT_URI}"
            return redirect(login_url)
        
        # Callback route
        elif path == "callback":
            code = request.args.get("code")
            if code is None:
                return Response("No authorization code provided", status=400)
            
            try:
                token_info = spotify.generate_token(code)
                access_token = token_info["access_token"]
                
                spotify_user = spotify.get_user_profile(access_token)
                user_id = spotify_user["id"]
                
                db = firestore.client()
                doc_ref = db.collection("users").document(user_id)
                doc_ref.set(token_info)
                
                rendered_data = {
                    "uid": user_id,
                    "BASE_URL": spotify.BASE_URL,
                }
                
                try:
                    return render_template("callback.html.j2", **rendered_data)
                except Exception as template_error:
                    return f"""
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
            except Exception as e:
                traceback_str = traceback.format_exc()
                return jsonify({"error": str(e), "traceback": traceback_str}), 500
        
        # Main view route (SVG generation)
        else:
            uid = request.args.get("uid")
            theme = request.args.get("theme", default="default")
            bar_color = request.args.get("bar_color", default="53b14f")
            background_color = request.args.get("background_color", default="121212")
            
            # Handle invalid request
            if not uid:
                return Response("Error: Missing uid parameter", status=400)
            
            try:
                access_token = get_access_token(uid)
                
                if access_token is None:
                    return Response("Error: User not found or invalid token", status=400)
                
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
                        return Response("No recent tracks found", status=404)
                
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
                
                resp = Response(svg, mimetype="image/svg+xml")
                resp.headers["Cache-Control"] = "s-maxage=1"
                return resp
                
            except Exception as e:
                traceback_str = traceback.format_exc()
                return jsonify({
                    "error": str(e), 
                    "traceback": traceback_str,
                    "message": "Error generating Spotify card"
                }), 500
            
    except Exception as e:
        traceback_str = traceback.format_exc()
        return jsonify({"error": str(e), "traceback": traceback_str}), 500

# Vercel serverless function handler
def handler(request, response):
    return app(request, response)

# For local development
if __name__ == "__main__":
    app.run(debug=True, port=3000) 