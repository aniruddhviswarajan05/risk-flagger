"""
Local Development Backend Server for RISK-FLAGGER
Emulates the AWS Lambda + API Gateway backend on localhost.

Endpoints:
  - POST /analyze       : Analyzes a stock ticker (IN or US) for volume spike anomalies
  - GET  /history       : Retrieves historical flag events for a ticker
  - GET  /watchlist     : Returns predefined watchlist stocks
  - GET  /health        : Health check endpoint
"""

import sys
import os
import json
import hashlib
import hmac
import base64
import time
import secrets
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timezone

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.rules import check_volume_spike
from core.bedrock_prompt import get_explanation

HISTORY_FILE = os.path.join(BASE_DIR, "local_history.json")
USERS_FILE = os.path.join(BASE_DIR, "local_users.json")
AUTH_SECRET = "signal_market_ai_secret_key_2026_x89f"

# ================= AUTHENTICATION SERVICE =================
def hash_password(password: str, salt: str = None) -> tuple:
    """Hashes a password using PBKDF2-HMAC-SHA256 with 100,000 iterations."""
    if not salt:
        salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    )
    return key.hex(), salt

def verify_password(password: str, password_hash: str, salt: str) -> bool:
    """Verifies a password against the stored hash and salt."""
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    )
    return hmac.compare_digest(key.hex(), password_hash)

def generate_token(user: dict) -> str:
    """Generates an HMAC-SHA256 signed JWT-style token valid for 7 days."""
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "id": user["id"],
        "email": user["email"],
        "name": user["name"],
        "role": user.get("role", "PRO TRADER"),
        "exp": int(time.time()) + (7 * 86400) # 7 days
    }
    
    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    message = f"{header_b64}.{payload_b64}"
    
    signature = hmac.new(
        AUTH_SECRET.encode(),
        message.encode(),
        hashlib.sha256
    ).digest()
    sig_b64 = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    
    return f"{message}.{sig_b64}"

def verify_token(token: str) -> dict:
    """Verifies HMAC signature and expiration timestamp of the token."""
    if not token:
        return None
    
    if token.startswith("Bearer "):
        token = token[7:].strip()
    
    parts = token.split(".")
    if len(parts) != 3:
        return None
    
    header_b64, payload_b64, sig_b64 = parts
    message = f"{header_b64}.{payload_b64}"
    
    # Calculate expected signature
    expected_sig = hmac.new(
        AUTH_SECRET.encode(),
        message.encode(),
        hashlib.sha256
    ).digest()
    expected_b64 = base64.urlsafe_b64encode(expected_sig).decode().rstrip("=")
    
    if not hmac.compare_digest(sig_b64, expected_b64):
        return None
    
    try:
        # Pad base64 if needed
        rem = len(payload_b64) % 4
        if rem > 0:
            payload_b64 += "=" * (4 - rem)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64).decode())
        
        # Check expiration
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None

def load_users() -> list:
    """Loads users from local_users.json and pre-seeds default demo account if empty."""
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    
    # Seed default user
    pwd_hash, salt = hash_password("password123")
    default_users = [{
        "id": "usr_default_01",
        "name": "Anirudh P.",
        "email": "trader@signal.io",
        "password_hash": pwd_hash,
        "salt": salt,
        "role": "PRO ANALYST",
        "created_at": datetime.now(timezone.utc).isoformat()
    }]
    save_users(default_users)
    return default_users

def save_users(users: list):
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=2)
    except Exception as e:
        print(f"[backend] Warning: could not write users file: {e}")

# ================= HISTORY SERVICE =================
def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_history_item(item):
    history = load_history()
    history.insert(0, item)
    history = history[:500]
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        print(f"[backend] Warning: could not write local history: {e}")


class RiskFlaggerHandler(BaseHTTPRequestHandler):
    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With")

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        if path in ("/", "/health"):
            self.send_response(200)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            resp = {
                "status": "healthy",
                "service": "risk-flagger-backend",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "endpoints": ["/auth/login", "/auth/signup", "/auth/me", "/analyze", "/history", "/watchlist", "/health"],
            }
            self.wfile.write(json.dumps(resp).encode("utf-8"))
            return

        if path == "/auth/me":
            auth_header = self.headers.get("Authorization", "")
            user_data = verify_token(auth_header)
            if not user_data:
                self.send_response(401)
                self._send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Unauthorized or expired session token"}).encode("utf-8"))
                return
            
            self.send_response(200)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success", "user": user_data}).encode("utf-8"))
            return

        if path == "/watchlist":
            watchlist_path = os.path.join(BASE_DIR, "infrastructure", "watchlist.json")
            data = {"tickers": [
                {"ticker": "RELIANCE", "market": "IN"},
                {"ticker": "TATASTEEL", "market": "IN"},
                {"ticker": "HDFCBANK", "market": "IN"},
                {"ticker": "INFY", "market": "IN"},
                {"ticker": "AAPL", "market": "US"},
                {"ticker": "NVDA", "market": "US"},
                {"ticker": "TSLA", "market": "US"},
            ]}
            if os.path.exists(watchlist_path):
                try:
                    with open(watchlist_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except Exception as e:
                    print(f"Error loading watchlist: {e}")

            self.send_response(200)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode("utf-8"))
            return

        if path == "/history":
            ticker_list = params.get("ticker", [])
            market_list = params.get("market", [])
            ticker = ticker_list[0].strip().upper() if ticker_list else ""
            market = market_list[0].strip().upper() if market_list else ""

            if not ticker:
                self.send_response(400)
                self._send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Missing 'ticker' query parameter"}).encode("utf-8"))
                return

            history = load_history()
            clean_ticker = ticker.replace(".NS", "")
            matches = [
                h for h in history
                if h.get("ticker", "").upper().replace(".NS", "") == clean_ticker
            ]

            self.send_response(200)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            resp = {
                "ticker": ticker,
                "market": market or ("US" if "." not in ticker and len(ticker) <= 4 else "IN"),
                "history": matches,
            }
            self.wfile.write(json.dumps(resp).encode("utf-8"))
            return

        # 404 for unknown endpoints
        self.send_response(404)
        self._send_cors_headers()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"error": f"Endpoint not found: {path}"}).encode("utf-8"))

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        content_len = int(self.headers.get("Content-Length", 0))
        post_body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"
        try:
            data = json.loads(post_body)
        except json.JSONDecodeError:
            data = {}

        # ----------------- REAL AUTH: SIGN UP -----------------
        if path == "/auth/signup":
            name = str(data.get("name", "")).strip()
            email = str(data.get("email", "")).strip().lower()
            password = str(data.get("password", ""))

            if not name or not email or not password:
                self.send_response(400)
                self._send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Name, email, and password are required"}).encode("utf-8"))
                return

            if len(password) < 6:
                self.send_response(400)
                self._send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Password must be at least 6 characters long"}).encode("utf-8"))
                return

            users = load_users()
            for u in users:
                if u["email"].lower() == email:
                    self.send_response(409)
                    self._send_cors_headers()
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "An account with this email already exists"}).encode("utf-8"))
                    return

            pwd_hash, salt = hash_password(password)
            new_user = {
                "id": f"usr_{secrets.token_hex(6)}",
                "name": name,
                "email": email,
                "password_hash": pwd_hash,
                "salt": salt,
                "role": "PRO TRADER",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            users.append(new_user)
            save_users(users)

            token = generate_token(new_user)
            safe_user = {
                "id": new_user["id"],
                "name": new_user["name"],
                "email": new_user["email"],
                "role": new_user["role"]
            }

            self.send_response(201)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "success",
                "message": "Account created successfully",
                "token": token,
                "user": safe_user
            }).encode("utf-8"))
            return

        # ----------------- REAL AUTH: LOGIN -----------------
        if path == "/auth/login":
            email = str(data.get("email", "")).strip().lower()
            password = str(data.get("password", ""))

            if not email or not password:
                self.send_response(400)
                self._send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Email and password are required"}).encode("utf-8"))
                return

            users = load_users()
            target_user = None
            for u in users:
                if u["email"].lower() == email:
                    target_user = u
                    break

            if not target_user:
                self.send_response(401)
                self._send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "No account found with this email address"}).encode("utf-8"))
                return

            if not verify_password(password, target_user["password_hash"], target_user["salt"]):
                self.send_response(401)
                self._send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Incorrect password. Please verify and try again."}).encode("utf-8"))
                return

            token = generate_token(target_user)
            safe_user = {
                "id": target_user["id"],
                "name": target_user["name"],
                "email": target_user["email"],
                "role": target_user.get("role", "PRO TRADER")
            }

            self.send_response(200)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "success",
                "message": "Authenticated successfully",
                "token": token,
                "user": safe_user
            }).encode("utf-8"))
            return

        # ----------------- STOCK ANALYSIS -----------------
        if path == "/analyze":
            ticker = str(data.get("ticker", "")).strip().upper()
            market = str(data.get("market", "IN")).strip().upper()

            if not ticker:
                self.send_response(400)
                self._send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Missing 'ticker' parameter"}).encode("utf-8"))
                return

            if market not in ("IN", "US"):
                market = "IN"

            print(f"[backend] Analyzing {ticker} ({market})...")
            try:
                result = check_volume_spike(ticker, market)
                if result["flagged"]:
                    explanation = get_explanation(result)
                else:
                    explanation = f"Volume is within normal parameters ({result['metrics']['volume_ratio']}x vs 30-day baseline)."

                result["explanation"] = explanation

                # Save to local history
                save_history_item(result)

                self.send_response(200)
                self._send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(result).encode("utf-8"))
            except ValueError as ve:
                self.send_response(404)
                self._send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(ve)}).encode("utf-8"))
            except Exception as e:
                print(f"[backend] Error analyzing {ticker}: {e}")
                self.send_response(500)
                self._send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Internal server error", "detail": str(e)}).encode("utf-8"))
            return

        self.send_response(404)
        self._send_cors_headers()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"error": f"Endpoint not found: {path}"}).encode("utf-8"))

    def log_message(self, format, *args):
        sys.stderr.write(f"[RiskFlagger Backend] {format % args}\n")


def run(port=8000):
    server_address = ("127.0.0.1", port)
    load_users() # Ensure users db initialized
    httpd = HTTPServer(server_address, RiskFlaggerHandler)
    print(f"\n=======================================================")
    print(f" Risk Flagger Local Backend running on http://127.0.0.1:{port}")
    print(f" Endpoints: /auth/login, /auth/signup, /auth/me, /analyze, /history, /watchlist, /health")
    print(f"=======================================================\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down local backend server.")
        httpd.server_close()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    run(port)
