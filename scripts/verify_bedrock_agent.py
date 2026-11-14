#!/usr/bin/env python3
"""One-time smoke test: is live Bedrock access actually usable on whatever AWS
credentials are currently active? This is P0 of the Ripple Investigation Agent plan
(docs/RIPPLE_INVESTIGATION.md) -- run this FIRST, before trusting any live agent path,
because every prior check on the personal dev account (011356580161) found
bedrock:InvokeModel access-denied (see docs/KNOWN_LIMITATIONS.md). If this script
fails here too, the deterministic fallback (investigation.loop.run_ripple_investigation,
already the default) remains the only path for today's demo -- and that's fine, it has
its own test suite and does not depend on this succeeding.

Usage: python3 scripts/verify_bedrock_agent.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend" / "src"))

import boto3  # noqa: E402
from botocore.exceptions import ClientError, NoCredentialsError  # noqa: E402

REGION = os.environ.get("BEDROCK_REGION", "us-east-1")
MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-5-20250929-v1:0")


def _print_header(title: str) -> None:
    print(f"\n=== {title} ===")


def check_identity() -> bool:
    _print_header("1. Caller identity")
    try:
        identity = boto3.client("sts").get_caller_identity()
    except NoCredentialsError:
        print("FAIL: no AWS credentials found in this environment at all.")
        return False
    print(f"Account: {identity['Account']}")
    print(f"ARN:     {identity['Arn']}")
    if identity["Account"] == "011356580161":
        print(
            "WARNING: this is the personal dev account already documented as "
            "bedrock:InvokeModel access-denied. If the hackathon issued new "
            "temporary credentials, configure them (e.g. `aws configure` or "
            "AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY env vars) before re-running this."
        )
    return True


def check_list_foundation_models() -> bool:
    _print_header(f"2. bedrock:ListFoundationModels ({REGION})")
    try:
        client = boto3.client("bedrock", region_name=REGION)
        resp = client.list_foundation_models()
    except ClientError as e:
        print(f"FAIL: {e.response['Error']['Code']}: {e.response['Error']['Message']}")
        return False
    model_ids = [m["modelId"] for m in resp.get("modelSummaries", [])]
    print(f"PASS: {len(model_ids)} models listed in {REGION}.")
    matching = [m for m in model_ids if MODEL_ID in m or m in MODEL_ID]
    if matching:
        print(f"Configured BEDROCK_MODEL_ID ('{MODEL_ID}') matches: {matching}")
    else:
        print(
            f"WARNING: configured BEDROCK_MODEL_ID ('{MODEL_ID}') not found among listed "
            f"models in {REGION}. Pick an available Claude model ID from the list above "
            "and set BEDROCK_MODEL_ID accordingly."
        )
    return True


def check_agent_invocation() -> bool:
    _print_header("3. Live agent invocation (smallest agent: regulatory watchdog, 1 tool)")
    try:
        from riskripple.agents.definitions import build_regulatory_watchdog_agent
    except Exception as e:  # import-time failure is also informative
        print(f"FAIL: could not import agent definitions: {e!r}")
        return False

    try:
        agent = build_regulatory_watchdog_agent()
        result = agent(
            "Call list_new_documents and tell me, in one sentence, how many "
            "documents are available for investigation."
        )
        print("PASS: live agent call returned a response:")
        print(str(result)[:500])
        return True
    except ClientError as e:
        print(f"FAIL: {e.response['Error']['Code']}: {e.response['Error']['Message']}")
        return False
    except Exception as e:
        print(f"FAIL: unexpected error invoking the agent: {e!r}")
        return False


def main() -> None:
    print(f"Verifying live Bedrock access (region={REGION}, model_id={MODEL_ID})...")
    identity_ok = check_identity()
    models_ok = check_list_foundation_models() if identity_ok else False
    agent_ok = check_agent_invocation() if models_ok else False

    _print_header("Summary")
    print(f"Identity check:        {'OK' if identity_ok else 'FAILED'}")
    print(f"ListFoundationModels:  {'OK' if models_ok else 'FAILED'}")
    print(f"Live agent invocation: {'OK' if agent_ok else 'FAILED'}")

    if agent_ok:
        print(
            "\nLive Bedrock agent path is usable. The Ripple Investigation Agent's "
            "agent-driven mode can be enabled for the demo."
        )
    else:
        print(
            "\nLive Bedrock is NOT usable right now. This is not a blocker for the "
            "demo: the deterministic fallback (investigation.loop.run_ripple_investigation) "
            "is already the default and does not require any of the above to succeed."
        )
    sys.exit(0 if agent_ok else 1)


if __name__ == "__main__":
    main()
