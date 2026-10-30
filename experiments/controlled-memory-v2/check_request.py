"""One bounded schema probe: at most one output token; not an experimental observation."""
import copy
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

out = Path(sys.argv[1])
key = os.environ.get("ANTHROPIC_API_KEY")
if not key:
    raise SystemExit("API key missing; no request made")
request_record = json.loads((out / "requests.jsonl").read_text().splitlines()[0])
body = copy.deepcopy(request_record["body"])
body["max_tokens"] = 1
request = urllib.request.Request("https://api.anthropic.com/v1/messages",
    data=json.dumps(body).encode(), method="POST",
    headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
result = {"diagnostic_only": True, "max_output_tokens": 1,
          "source_request_hash": request_record["request_hash"]}
try:
    with urllib.request.urlopen(request, timeout=180) as response:
        raw = json.load(response)
        result.update({"http_status": response.status, "model": raw.get("model"),
                       "stop_reason": raw.get("stop_reason"), "usage": raw.get("usage")})
except urllib.error.HTTPError as exc:
    try:
        error = json.loads(exc.read(8192)).get("error", {})
    except (ValueError, UnicodeError):
        error = {"type": "non_json_error", "message": "Provider returned a non-JSON error"}
    result.update({"http_status": exc.code, "error_type": error.get("type"),
                   "message": str(error.get("message", "")).replace(key, "[REDACTED]")[:1600]})
except (OSError, ValueError) as exc:
    result.update({"error_type": type(exc).__name__, "message": "Transport failure; no retry"})
(out / "schema-diagnostic.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
if result.get("http_status") != 200:
    raise SystemExit(1)
