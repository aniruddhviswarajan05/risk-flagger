"""
Lambda handler for POST /analyze
Body: {"ticker": "RELIANCE"}

Flow:
  1. Run the volume spike rule (core/rules.py)
  2. If flagged, get a plain-language explanation from Bedrock
  3. Save the result to DynamoDB (so /history can retrieve it later)
  4. Return the result to the frontend

NOTE: core/ is bundled alongside this file at deploy time by the
SAM template (see infrastructure/template.yaml CodeUri setting).
"""

import json
import os
import boto3
from decimal import Decimal

from rules import check_volume_spike
from bedrock_prompt import get_explanation

dynamodb = boto3.resource("dynamodb")
TABLE_NAME = os.environ.get("TABLE_NAME", "StockFlags")


def _cors_response(status_code: int, body: dict):
    return {
        "statusCode": status_code,
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "OPTIONS,POST",
        },
        "body": json.dumps(body),
    }


def _to_dynamo_safe(obj):
    """DynamoDB doesn't accept Python floats directly — convert to Decimal."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: _to_dynamo_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_dynamo_safe(v) for v in obj]
    return obj


def handler(event, context):
    try:
        body = json.loads(event.get("body") or "{}")
        ticker = body.get("ticker", "").strip()
        market = body.get("market", "IN").strip().upper()  # "IN" (default) or "US"

        if not ticker:
            return _cors_response(400, {"error": "Missing 'ticker' in request body"})

        if market not in ("IN", "US"):
            return _cors_response(400, {"error": "Invalid 'market' — must be 'IN' or 'US'"})

        # Step 1: run the rule
        result = check_volume_spike(ticker, market)

        # Step 2: get explanation only if flagged (saves Bedrock calls otherwise)
        if result["flagged"]:
            explanation = get_explanation(result)
        else:
            explanation = "No unusual pattern detected — volume is within normal range."

        result["explanation"] = explanation

        # Step 3: save to DynamoDB
        table = dynamodb.Table(TABLE_NAME)
        table.put_item(Item=_to_dynamo_safe(result))

        # Step 4: return to frontend
        return _cors_response(200, result)

    except ValueError as e:
        return _cors_response(404, {"error": str(e)})
    except Exception as e:
        print(f"Unhandled error: {e}")
        return _cors_response(500, {"error": "Internal server error", "detail": str(e)})
