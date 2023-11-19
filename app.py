import os

from flask import Flask, jsonify, render_template
from flask import session
from flask import url_for

from dotenv import load_dotenv

load_dotenv()

from authlib.integrations.flask_client import OAuth

import berserk
from stockfish import Stockfish

from games import get_games, get_dirty_flag_games, get_end_of_game_link

LICHESS_HOST = os.getenv("LICHESS_HOST", "https://lichess.org")

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
app.config["LICHESS_CLIENT_ID"] = os.getenv("LICHESS_CLIENT_ID")
app.config["LICHESS_AUTHORIZE_URL"] = f"{LICHESS_HOST}/oauth"
app.config["LICHESS_ACCESS_TOKEN_URL"] = f"{LICHESS_HOST}/api/token"

oauth = OAuth(app)
oauth.register("lichess", client_kwargs={"code_challenge_method": "S256"})


stockfish = Stockfish("./stockfish/src/stockfish")


def get_berserk_client(access_token: str) -> berserk.Client:
    berserk_session = berserk.TokenSession(access_token)
    return berserk.Client(session=berserk_session)


def get_username(berserk_client: berserk.Client) -> str:
    return berserk_client.account.get()["username"]


@app.route("/")
def index():
    if "token" not in session:
        return render_template("index.html", username=None)

    berserk_client = get_berserk_client(session["token"]["access_token"])
    username = get_username(berserk_client)

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


@app.route("/api/dirty-flags")
def get_dirty_flags():
    if "token" not in session:
        return jsonify({}), 401

    berserk_client = get_berserk_client(session["token"]["access_token"])
    username = berserk_client.account.get()["username"]

    games = get_games(berserk_client, username)
    dirty_flag_games = get_dirty_flag_games(games, username, stockfish)

    response = {
        "count": len(dirty_flag_games),
        "links": [get_end_of_game_link(game) for game in dirty_flag_games],
    }
    return jsonify(response)


if __name__ == "__main__":
    app.run()
