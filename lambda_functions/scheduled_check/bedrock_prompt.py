"""
Builds the prompt sent to Bedrock and parses the response.
Kept separate from the Lambda handler so you can test prompt
wording locally (with a mocked response) before wiring up
real AWS credentials.
"""

import json
import boto3

# Claude on Bedrock. If this exact model isn't enabled in your AWS
# account/region, go to Bedrock console -> Model access -> request
# access (it's usually instant for Anthropic models).
BEDROCK_MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"
BEDROCK_REGION = "us-east-1"  # change if your account uses a different region


def build_prompt(flag_result: dict) -> str:
    metrics = flag_result["metrics"]
    ticker = flag_result["ticker"]
    market = flag_result.get("market", "IN")
    currency = "₹" if market == "IN" else "$"
    exchange = "NSE" if market == "IN" else "the US market"

    return f"""You are a risk analyst explaining a stock market flag to a retail
investor who has no formal finance background. Be direct and plain-spoken.

Flag detected: {flag_result['rule']}
Stock: {ticker} ({exchange})
Today's trading volume: {metrics['today_volume']:,}
Average volume (last 30 days): {metrics['avg_30d_volume']:,.0f}
Volume ratio: {metrics['volume_ratio']}x normal
Price change today: {metrics['price_change_pct']}%
Today's closing price: {currency}{metrics['today_close']:,}

Write exactly 3 short sentences:
1. What this pattern means in plain language.
2. Why it's worth a second look (not a certainty of anything bad).
3. One concrete thing the investor should check next (e.g. recent news,
   exchange announcements, promoter filings) before deciding anything.

Rules:
- Do NOT tell the investor to buy or sell.
- Do NOT use jargon without explaining it.
- Do NOT claim this proves fraud or manipulation — only that it's unusual.
"""


def _generate_fallback_explanation(flag_result: dict) -> str:
    metrics = flag_result.get("metrics", {})
    ticker = flag_result.get("ticker", "The stock")
    market = flag_result.get("market", "IN")
    ratio = metrics.get("volume_ratio", 1.0)
    pct = metrics.get("price_change_pct", 0.0)
    direction = "up" if pct >= 0 else "down"
    exchange = "NSE" if market == "IN" else "US markets"

    s1 = f"{ticker} on the {exchange} is seeing trading volume {ratio}x higher than its 30-day average, while price moved {abs(pct):.1f}% {direction} today."
    s2 = "An abrupt surge of this magnitude usually indicates either institutional repositioning, significant block deals, or speculation ahead of pending news."
    s3 = "Before acting, investors should review regulatory filings, recent exchange disclosures, or corporate press releases to determine whether fundamental news backs the activity."
    return f"{s1} {s2} {s3}"


def get_explanation(flag_result: dict) -> str:
    """
    Calls Bedrock and returns the plain-language explanation string.
    Requires AWS credentials configured (via `aws configure` or an
    IAM role, if running inside Lambda).
    If Bedrock is unavailable or unconfigured, gracefully falls back
    to an automated risk explanation.
    """
    try:
        client = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)
        prompt = build_prompt(flag_result)

        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 300,
            "messages": [{"role": "user", "content": prompt}],
        }

        response = client.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            body=json.dumps(body),
            contentType="application/json",
            accept="application/json",
        )

        response_body = json.loads(response["body"].read())
        return response_body["content"][0]["text"].strip()
    except Exception as e:
        print(f"[bedrock_prompt] Bedrock not available ({e}). Using automated risk explainer.")
        return _generate_fallback_explanation(flag_result)
