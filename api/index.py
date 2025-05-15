from flask import Flask, Response, redirect, request, jsonify, render_template
import os
import sys
import traceback

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the necessary modules
from util import spotify
from base64 import b64decode
import json
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

# Initialize Firebase
try:
    firebase_config = os.environ.get("FIREBASE")
    if firebase_config:
        firebase_dict = json.loads(b64decode(firebase_config))
        cred = credentials.Certificate(firebase_dict)
        firebase_admin.initialize_app(cred)
except Exception as e:
    print(f"Firebase initialization error: {str(e)}")

app = Flask(__name__)

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
                
                return render_template("callback.html.j2", **rendered_data)
            except Exception as e:
                traceback_str = traceback.format_exc()
                return jsonify({"error": str(e), "traceback": traceback_str}), 500
        
        # Default view route - handle in the main function
        else:
            return jsonify({"message": "API is running", "path": path})
            
    except Exception as e:
        traceback_str = traceback.format_exc()
        return jsonify({"error": str(e), "traceback": traceback_str}), 500

# Vercel serverless function handler
def handler(request, response):
    return app(request, response)

# For local development
if __name__ == "__main__":
    app.run(debug=True, port=3000) 