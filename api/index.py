from flask import Flask, Response, redirect, request
import os
import sys

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the necessary modules
from login import app as login_app
from callback import app as callback_app
from view import app as view_app

app = Flask(__name__)

@app.route("/api/login", methods=["GET"])
def login():
    return login_app.dispatch_request()

@app.route("/api/callback", methods=["GET"])
def callback():
    return callback_app.dispatch_request()

@app.route("/api", defaults={"path": ""}, methods=["GET"])
@app.route("/api/<path:path>", methods=["GET"])
def view(path):
    return view_app.dispatch_request(path)

@app.route("/", defaults={"path": ""}, methods=["GET"])
@app.route("/<path:path>", methods=["GET"])
def root(path):
    return redirect("/api", code=302)

if __name__ == "__main__":
    app.run(debug=True) 