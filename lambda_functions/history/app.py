"""
Lambda handler for GET /history?ticker=RELIANCE.NS

Returns past flags stored in DynamoDB for a given ticker,
so the frontend can show "this stock was flagged N times".
"""

import json
import os
import boto3
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb")
TABLE_NAME = os.environ.get("TABLE_NAME", "StockFlags")


def _cors_response(status_code: int, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "OPTIONS,GET",
        },
        "body": json.dumps(body, default=str),
    }


def handler(event, context):
    params = event.get("queryStringParameters") or {}
    ticker = params.get("ticker", "").strip()

    if not ticker:
        return _cors_response(400, {"error": "Missing 'ticker' query parameter"})

    market = params.get("market", "").strip().upper()
    ticker = ticker.upper()
    if market == "IN" and not ticker.endswith(".NS"):
        ticker = ticker + ".NS"
    elif market != "US" and not ticker.endswith(".NS"):
        # Default behavior: if not US, check if user provided NSE ticker without .NS
        # Tickers with dots or specifically marked US won't have .NS appended
        pass

    table = dynamodb.Table(TABLE_NAME)

    try:
        response = table.query(
            KeyConditionExpression=Key("ticker").eq(ticker),
            ScanIndexForward=False,  # newest first
            Limit=20,
        )
        return _cors_response(200, {"ticker": ticker, "history": response.get("Items", [])})
    except Exception as e:
        print(f"Error querying history: {e}")
        return _cors_response(500, {"error": "Internal server error", "detail": str(e)})
