# Connecting frontend/index.html to your deployed backend

`frontend/index.html` now calls your real API instead of only showing
demo data. Here's exactly what's wired up and what you still need to do.

## What's already done

- **`POST /analyze`** — the Live Signals page calls this for every ticker
  in `SCAN_STOCKS` (top of the `<script>` tag) and builds the signal cards
  from whatever comes back flagged. If nothing is flagged, or the backend
  isn't reachable, it falls back to 3 sample signals so the UI never looks
  broken.
- **`GET /history`** — the stock detail panel's News tab calls this per
  ticker and lists past flags.
- **Cognito login** — your API's default authorizer is Cognito
  (`template.yaml`), so every `/analyze` and `/history` call needs an
  `Authorization` header carrying a Cognito ID token. There's a "Sign in"
  button in the dashboard topbar that redirects to your Cognito Hosted UI
  (`response_type=token` implicit flow) and reads the token back out of
  the URL fragment on return.
- **Demo mode by default** — until you fill in the config below, the
  dashboard runs entirely on sample data. Nothing breaks; you just won't
  see real flags.

## What you need to do

1. Deploy the backend (see `README.md` Steps 0–4b) and copy the three
   outputs SAM prints: `ApiUrl`, `CognitoDomain`, `CognitoClientId`.

2. Open `frontend/index.html`, find the `CONFIG` object near the top of
   the `<script>` tag, and fill it in:

   ```js
   const CONFIG = {
     API_BASE_URL: 'https://abc123.execute-api.us-east-1.amazonaws.com/Prod',
     COGNITO_DOMAIN: 'https://risk-flagger-111122223333.auth.us-east-1.amazoncognito.com',
     COGNITO_CLIENT_ID: 'xxxxxxxxxxxxxxxxxxxxxxxxxx',
     REDIRECT_URI: window.location.origin + window.location.pathname,
   };
   ```

3. Deploy `frontend/index.html` (Amplify, S3 static hosting, or just open
   it locally for testing) and note its final URL.

4. Redeploy the backend once more with `CallbackURL` set to that real
   frontend URL (`sam deploy --guided` again, or update the parameter and
   redeploy) — Cognito only redirects back to URLs it's told about.

5. Open the dashboard, click **Sign in** (creates you an account via the
   Cognito Hosted UI — email + password, or Google if you configured that
   identity provider), and open **Live Signals**. You should see the
   scan list call your Lambda one ticker at a time and real Bedrock
   explanations appear when you click into a flagged stock.

## Notes / limitations

- `SCAN_STOCKS` in the frontend is a small hardcoded list — it's separate
  from `infrastructure/watchlist.json`, which only feeds the scheduled
  Lambda. Keep them in sync manually, or wire the frontend to read the
  watchlist from S3 later if you want one source of truth.
- The API Gateway authorizer applies to `POST /analyze` and `GET
  /history` only — `OPTIONS` is left open for CORS preflight, which is
  already handled in `template.yaml`.
- If a ticker has no Yahoo Finance data (bad symbol, delisted, etc.)
  `/analyze` returns a 404 and that row just shows "✕ error" in the scan
  list — it won't crash the rest of the scan.
- The volume chart in the stock detail panel's Charts tab is still
  illustrative (not built from `/history`) — real history data only
  powers the News tab for now.
