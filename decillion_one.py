"""DECILLION THE ONE: explicit-provider E2E vertical slice (Python standard library)."""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import sys
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def execute(prompt: str, endpoint: str | None = None, token: str | None = None, timeout: float = 20.0):
    """No implicit fallback: absent provider means no inference, not a fabricated answer."""
    if not prompt.strip():
        raise ValueError("prompt must not be empty")
    request_id = str(uuid.uuid4())
    request = {"request_id": request_id, "prompt": prompt}
    outcome = {"request_id": request_id, "status": "not_executed", "provider": None,
               "output": None, "error": "No provider endpoint configured"}
    if endpoint:
        if not endpoint.startswith(("https://", "http://127.0.0.1:", "http://localhost:")):
            raise ValueError("Provider endpoint must use HTTPS or loopback HTTP")
        body = canonical(request)
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = "Bearer " + token
        req = urllib.request.Request(endpoint, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                data = json.loads(response.read(2_000_001).decode("utf-8"))
            if not isinstance(data, dict) or not isinstance(data.get("output"), str):
                raise ValueError("Provider response must contain string 'output'")
            if data.get("request_id") != request_id:
                raise ValueError("Provider request_id mismatch")
            outcome.update(status="completed", provider=endpoint, output=data["output"], error=None)
        except (urllib.error.URLError, ValueError, UnicodeError, json.JSONDecodeError) as exc:
            outcome.update(status="failed", provider=endpoint, error=type(exc).__name__ + ": " + str(exc))
    evidence = {"schema": "i.decillion.e2e.v1", "request": request,
                "outcome": outcome, "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "model_identity": "unverified", "verification": "not_verified"}
    receipt = {"evidence": evidence, "sha256": digest(evidence), "signature": None,
               "signature_algorithm": None}
    return receipt


def sign(receipt, key: bytes):
    """Optional local HMAC integrity, not model correctness or third-party attestation."""
    if not key:
        raise ValueError("signing key cannot be empty")
    if not verify(receipt):
        raise ValueError("cannot sign invalid receipt")
    signed = dict(receipt)
    signed["signature_algorithm"] = "HMAC-SHA256"
    signed["signature"] = hmac.new(key, canonical(receipt["evidence"]), hashlib.sha256).hexdigest()
    return signed


def verify(receipt, key: bytes | None = None):
    try:
        if not hmac.compare_digest(receipt["sha256"], digest(receipt["evidence"])):
            return False
        signature = receipt.get("signature")
        if signature is None:
            return receipt.get("signature_algorithm") is None
        if receipt.get("signature_algorithm") != "HMAC-SHA256" or not key:
            return False
        expected = hmac.new(key, canonical(receipt["evidence"]), hashlib.sha256).hexdigest()
        return hmac.compare_digest(signature, expected)
    except (KeyError, TypeError, ValueError):
        return False


def main(argv=None):
    parser = argparse.ArgumentParser(description="DECILLION THE ONE E2E evidence CLI")
    parser.add_argument("prompt", help="Request to send to an explicitly configured provider")
    parser.add_argument("--endpoint", default=os.environ.get("I_ONE_PROVIDER_ENDPOINT"))
    parser.add_argument("--out", default="receipt.json")
    args = parser.parse_args(argv)
    receipt = execute(args.prompt, endpoint=args.endpoint, token=os.environ.get("I_ONE_PROVIDER_TOKEN"))
    key = os.environ.get("I_ONE_RECEIPT_KEY")
    if key:
        receipt = sign(receipt, key.encode("utf-8"))
    target = Path(args.out)
    if target.exists():
        parser.error(f"Refusing to overwrite existing receipt: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as file:
        json.dump(receipt, file, indent=2, ensure_ascii=False)
        file.write("\n")
    print(json.dumps({"receipt": str(target), "status": receipt["evidence"]["outcome"]["status"],
                      "integrity_valid": verify(receipt, key.encode("utf-8") if key else None)}))
    return 0 if receipt["evidence"]["outcome"]["status"] == "completed" else 2


if __name__ == "__main__":
    sys.exit(main())
