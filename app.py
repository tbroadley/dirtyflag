import os

from flask import Flask, jsonify, redirect, render_template
from flask import session
from flask import url_for

from dotenv import load_dotenv

load_dotenv()

from authlib.integrations.flask_client import OAuth

from stockfish import Stockfish

from games import get_berserk_client, get_username, get_dirty_flag_data

LICHESS_HOST = os.getenv("LICHESS_HOST", "https://lichess.org")

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
app.config["LICHESS_CLIENT_ID"] = os.getenv("LICHESS_CLIENT_ID")
app.config["LICHESS_AUTHORIZE_URL"] = f"{LICHESS_HOST}/oauth"
app.config["LICHESS_ACCESS_TOKEN_URL"] = f"{LICHESS_HOST}/api/token"

oauth = OAuth(app)
oauth.register("lichess", client_kwargs={"code_challenge_method": "S256"})


@app.route("/")
def index():
    if "token" not in session:
        return render_template("index.html", username=None)

    berserk_client = get_berserk_client(session["token"]["access_token"])
    username = get_username(berserk_client)

    # TODO If the user's dirty flag data are in the cache, we should insert them directly
    # into the template context instead of making another API call.
    return render_template("index.html", username=username)


@app.route("/login")
def login():
    redirect_uri = url_for("authorize", _external=True)
    """
    If you need to append scopes to your requests, add the `scope=...` named argument
    to the `.authorize_redirect()` method. For admissible values refer to https://lichess.org/api#section/Authentication. 
    Example with scopes for allowing the app to read the user's email address:
    `return oauth.lichess.authorize_redirect(redirect_uri, scope="email:read")`
    """
    return oauth.lichess.authorize_redirect(redirect_uri)


@app.route("/api/authorize")
def authorize():
    token = oauth.lichess.authorize_access_token()
    session["token"] = token

    return redirect(url_for("index"))


@app.route("/dirty-flag-summary")
def get_dirty_flag_summary():
    if "token" not in session:
        return jsonify({}), 401

    data = get_dirty_flag_data(session["token"]["access_token"])
    return render_template("dirty_flag_summary.html", **data)


if __name__ == "__main__":
    app.run()
