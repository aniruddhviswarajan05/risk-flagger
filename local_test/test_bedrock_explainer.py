"""
RUN THIS SECOND, after test_rules_engine.py works and you have:
  1. An AWS account with credentials configured (`aws configure`)
  2. Bedrock model access granted for Anthropic Claude models
     (AWS Console -> Bedrock -> Model access -> Manage model access)

This chains the real rules engine output into a real Bedrock call,
so you can see the actual explanation text before wiring up Lambda.

Usage:
    python local_test/test_bedrock_explainer.py RELIANCE
"""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.rules import check_volume_spike
from core.bedrock_prompt import get_explanation, build_prompt


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_bedrock_explainer.py <TICKER>")
        sys.exit(1)

    ticker = sys.argv[1]
    print(f"\nStep 1: Running rules engine on {ticker}...\n")
    result = check_volume_spike(ticker)
    print(json.dumps(result, indent=2))

    print("\nStep 2: Prompt that will be sent to Bedrock:\n")
    print(build_prompt(result))

    print("\nStep 3: Calling Bedrock...\n")
    try:
        explanation = get_explanation(result)
        print("--- BEDROCK EXPLANATION ---")
        print(explanation)
    except Exception as e:
        print(f"ERROR calling Bedrock: {e}")
        print("\nCommon fixes:")
        print("  - Run `aws configure` if you haven't set up credentials")
        print("  - Check Bedrock model access is granted in the console")
        print("  - Check BEDROCK_REGION in core/bedrock_prompt.py matches your account setup")


if __name__ == "__main__":
    main()
