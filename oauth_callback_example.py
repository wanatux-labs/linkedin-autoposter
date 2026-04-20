#!/usr/bin/env python3
"""
Minimal Flask app to catch the LinkedIn OAuth 2.0 callback.

LinkedIn redirects the user here after they authorize your app.
The auth code is saved to a file so your token-exchange script can read it.

Usage:
    1. Set your LinkedIn app's redirect URI to http://localhost:5000/linkedin/callback
    2. Run this server: python3 oauth_callback_example.py
    3. Open the authorization URL in your browser
    4. After approval, the auth code is saved to /tmp/linkedin_auth_code.txt
    5. Exchange the code for an access token (see exchange_token() below)

Requires: pip install flask requests
"""
from pathlib import Path

import requests
from flask import Flask, request

app = Flask(__name__)

# ---- Configure these for your LinkedIn app ----
CLIENT_ID = "YOUR_CLIENT_ID"
CLIENT_SECRET = "YOUR_CLIENT_SECRET"
REDIRECT_URI = "http://localhost:5000/linkedin/callback"
TOKEN_OUTPUT_PATH = Path("linkedin_token.json")


@app.route("/linkedin/callback")
def linkedin_callback():
    """Catch the OAuth redirect and save the authorization code."""
    code = request.args.get("code", "")
    state = request.args.get("state", "")
    error = request.args.get("error", "")

    if error:
        error_desc = request.args.get("error_description", "")
        return (
            f"<h1>LinkedIn Auth Error</h1><p>{error}: {error_desc}</p>"
        ), 400

    if code:
        Path("/tmp/linkedin_auth_code.txt").write_text(code)
        return (
            "<html><body style='font-family:sans-serif;padding:40px;text-align:center;'>"
            "<h1 style='color:#27ae60;'>LinkedIn Authorization Successful</h1>"
            "<p>Auth code captured and saved. You can close this tab.</p>"
            f"<p style='color:#888;font-size:0.8em;'>State: {state}</p>"
            "</body></html>"
        )

    return "<h1>No code received</h1>", 400


def exchange_token(auth_code: str) -> dict:
    """
    Exchange an authorization code for an access token.

    Call this after the callback saves the auth code:
        code = Path("/tmp/linkedin_auth_code.txt").read_text().strip()
        token_data = exchange_token(code)
    """
    resp = requests.post(
        "https://www.linkedin.com/oauth/v2/accessToken",
        data={
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": REDIRECT_URI,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
        timeout=30,
    )
    resp.raise_for_status()
    token_data = resp.json()

    # Save token to file for the poster script
    import json

    TOKEN_OUTPUT_PATH.write_text(json.dumps(token_data, indent=2))
    print(f"Token saved to {TOKEN_OUTPUT_PATH}")
    print(f"Expires in {token_data.get('expires_in', '?')} seconds")

    return token_data


def get_auth_url() -> str:
    """Generate the LinkedIn OAuth authorization URL."""
    params = (
        f"response_type=code"
        f"&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&state=linkedin-autoposter"
        f"&scope=w_member_social%20openid%20profile"
    )
    return f"https://www.linkedin.com/oauth/v2/authorization?{params}"


if __name__ == "__main__":
    print(f"\nAuthorization URL:\n{get_auth_url()}\n")
    print("Open the URL above in your browser, then approve access.")
    print("Waiting for callback on http://localhost:5000/linkedin/callback ...\n")
    app.run(port=5000, debug=False)
