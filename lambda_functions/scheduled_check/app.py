"""
Lambda handler triggered on a schedule by EventBridge (every 15 minutes,
market hours only — see the Schedule expression in template.yaml).

This is what makes the product "semi-live" without needing a risky
WebSocket/streaming setup: instead of only checking a stock when a user
manually asks, EventBridge fires this function automatically, which:

  1. Reads a watchlist of tickers from S3 (watchlist.json)
  2. Runs the same volume-spike rule against each one
  3. If flagged, gets a Bedrock explanation
  4. Saves the result to the same DynamoDB table used by /analyze

So a user can add a ticker to their watchlist once, and flags get
generated automatically in the background — no page needs to be open.
"""

import json
import os
import boto3
from decimal import Decimal

from rules import check_volume_spike
from bedrock_prompt import get_explanation

s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")

TABLE_NAME = os.environ.get("TABLE_NAME", "StockFlags")
BUCKET_NAME = os.environ.get("WATCHLIST_BUCKET")
WATCHLIST_KEY = "watchlist.json"


def _to_dynamo_safe(obj):
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: _to_dynamo_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_dynamo_safe(v) for v in obj]
    return obj


def get_watchlist():
    """
    Reads the list of tickers to auto-check from S3.
    Each entry is {"ticker": "...", "market": "IN"|"US"}.
    Falls back to a small default list if the file doesn't exist yet,
    so the function doesn't fail on first deploy before anyone's
    uploaded a watchlist.
    """
    try:
        response = s3.get_object(Bucket=BUCKET_NAME, Key=WATCHLIST_KEY)
        data = json.loads(response["Body"].read())
        return data.get("tickers", [])
    except s3.exceptions.NoSuchKey:
        print(f"No watchlist.json found in {BUCKET_NAME} — using default sample list")
        return [
            {"ticker": "RELIANCE", "market": "IN"},
            {"ticker": "TATASTEEL", "market": "IN"},
            {"ticker": "AAPL", "market": "US"},
        ]
    except Exception as e:
        print(f"Error reading watchlist from S3: {e}")
        return []


def handler(event, context):
    watchlist = get_watchlist()
    table = dynamodb.Table(TABLE_NAME)

    results = []
    for entry in watchlist:
        ticker = entry.get("ticker") if isinstance(entry, dict) else entry
        market = entry.get("market", "IN") if isinstance(entry, dict) else "IN"

        try:
            result = check_volume_spike(ticker, market)

            if result["flagged"]:
                result["explanation"] = get_explanation(result)
            else:
                result["explanation"] = "No unusual pattern detected."

            result["source"] = "scheduled_check"  # distinguishes auto-checks from manual /analyze calls

            table.put_item(Item=_to_dynamo_safe(result))
            results.append({"ticker": ticker, "market": market, "flagged": result["flagged"]})

        except Exception as e:
            print(f"Error checking {ticker} ({market}): {e}")
            results.append({"ticker": ticker, "market": market, "error": str(e)})

    print(f"Scheduled check complete: {json.dumps(results)}")
    return {"statusCode": 200, "body": json.dumps({"checked": len(watchlist), "results": results})}
