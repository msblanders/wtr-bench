"""Read-only model access check. Does not request a completion or reveal credentials."""
import json
import os
import urllib.error
import urllib.request

key = os.environ.get("ANTHROPIC_API_KEY")
if not key:
    raise SystemExit("ANTHROPIC_API_KEY is missing; no request made.")
request = urllib.request.Request(
    "https://api.anthropic.com/v1/models/claude-sonnet-4-6",
    headers={"x-api-key": key, "anthropic-version": "2023-06-01"},
)
try:
    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.load(response)
        print(json.dumps({"status": response.status, "model_id": data.get("id"),
                          "message": "Model metadata accessible; this does not verify billing balance."}))
except urllib.error.HTTPError as exc:
    try:
        error = json.loads(exc.read(4096)).get("error", {})
    except (ValueError, UnicodeError):
        error = {"type": "non_json_error", "message": "Provider returned a non-JSON error."}
    result = {"http_status": exc.code, "error_type": error.get("type"),
              "message": str(error.get("message", "")).replace(key, "[REDACTED]")[:800]}
    print(json.dumps(result))
    raise SystemExit(1) from None
