"""
RUN THIS FIRST. No AWS account needed for this step.

This proves the core data-fetching and flagging logic works
before you wire up Lambda, API Gateway, or Bedrock.

Usage:
    python local_test/test_rules_engine.py RELIANCE          (defaults to India/NSE)
    python local_test/test_rules_engine.py TATASTEEL IN
    python local_test/test_rules_engine.py AAPL US
    python local_test/test_rules_engine.py TSLA US
"""

import sys
import os
import json

# Allow importing from the core/ folder one level up
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.rules import check_volume_spike


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_rules_engine.py <TICKER> [IN|US]")
        print("Example: python test_rules_engine.py RELIANCE IN")
        print("Example: python test_rules_engine.py AAPL US")
        sys.exit(1)

    ticker = sys.argv[1]
    market = sys.argv[2].upper() if len(sys.argv) > 2 else "IN"
    print(f"\nFetching data for {ticker} (market={market})...\n")

    try:
        result = check_volume_spike(ticker, market)
    except ValueError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    print(json.dumps(result, indent=2))

    if result["flagged"]:
        print(f"\n🚩 FLAGGED: Volume is {result['metrics']['volume_ratio']}x normal.")
    else:
        print(f"\n✅ No flag. Volume is {result['metrics']['volume_ratio']}x normal (below {result['metrics']['threshold']}x threshold).")


if __name__ == "__main__":
    main()
