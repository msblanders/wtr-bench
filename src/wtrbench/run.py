"""Minimal runner: send items to a responder, persist strict-parsed answers.

A responder returns text or a ModelOutput with API metadata. Synthetic
responders live in ``synthetic.py``; ``AnthropicResponder`` calls the API
(optional dependency). One call per item, temperature 0, with a neutral
answer-format instruction. Anything that does not parse strictly as A or B
is recorded with ``choice=None``; it is never coerced.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, Protocol

from pydantic import BaseModel

from wtrbench.inference import InferenceItem

FORMAT_SYSTEM = (
    "For each question, reply with exactly one uppercase letter: A or B. "
    "Do not include any explanation or other text."
)


class ModelOutput(BaseModel):
    raw: str
    stop_reason: str | None = None
    returned_model: str | None = None
    request_id: str | None = None
    usage: dict[str, object] | None = None


Responder = Callable[[InferenceItem], str | ModelOutput]


class PromptItem(Protocol):
    prompt: str

#: Full-string match only. Allowed: A, B, (A), (B), A., B., A), B), optionally
#: wrapped in quotes, backticks or asterisks. Anything else, including any
#: prose ("A or C", "B since ...", "Answer: A"), is format drift and is kept
#: as raw text with choice=None. It is never coerced.
_STRICT = re.compile(r"^[\"'`*]*\(?([AB])[\)\.]?[\"'`*]*$", re.IGNORECASE)


def parse_choice(raw: str) -> Literal["A", "B"] | None:
    m = _STRICT.match(raw.strip())
    if not m:
        return None
    return "A" if m.group(1).upper() == "A" else "B"


class Response(ModelOutput):
    item_id: str
    responder: str
    choice: Literal["A", "B"] | None
    keyed: bool | None


class RunExists(FileExistsError):
    """Raised when an output file already exists and resume was not requested."""


def items_hash(items: Iterable[InferenceItem]) -> str:
    h = hashlib.sha256()
    for it in items:
        h.update(it.item_id.encode())
    return h.hexdigest()[:16]


def run(
    items: list[InferenceItem],
    responder: Responder,
    responder_name: str,
    jsonl_path: str | Path | None = None,
    resume: bool = False,
    config: dict[str, object] | None = None,
) -> list[Response]:
    """Call the responder once per item and persist strict-parsed answers.

    With ``jsonl_path``: refuses to touch an existing file unless ``resume`` is
    True, in which case items already answered in that file are skipped and
    only unfinished items are called. A ``<jsonl_path>.config.json`` records
    the run configuration and the hash of the item set; on resume it must
    match. The returned list covers every item (existing plus new).
    """
    existing: dict[str, Response] = {}
    path = Path(jsonl_path) if jsonl_path else None
    cfg = {**(config or {}), "responder": responder_name, "n_items": len(items),
           "items_hash": items_hash(items)}
    # Compare the same JSON representation that is persisted on disk. The CLI
    # supplies tuple-valued ladders, which JSON reads back as lists.
    cfg = json.loads(json.dumps(cfg))
    if path is not None:
        cfg_path = path.with_suffix(path.suffix + ".config.json")
        if path.exists():
            if not resume:
                raise RunExists(f"{path} exists; pass resume=True to continue it")
            prior = json.loads(cfg_path.read_text()) if cfg_path.exists() else {}
            if prior.get("items_hash") != cfg["items_hash"]:
                raise ValueError(f"{path} was produced from a different item set; refusing to resume")
            for key in ("responder", *sorted((config or {}).keys())):
                if prior.get(key) != cfg.get(key):
                    raise ValueError(
                        f"{path} was produced with {key}={prior.get(key)!r}, "
                        f"not {cfg.get(key)!r}; refusing to resume"
                    )
            for r in load_responses(path):
                if r.item_id in existing:
                    raise ValueError(f"duplicate item_id {r.item_id} in {path}")
                existing[r.item_id] = r
        else:
            cfg["started"] = datetime.now(UTC).isoformat(timespec="seconds")
            cfg_path.write_text(json.dumps(cfg, indent=2))
    out: list[Response] = []
    for item in items:
        if item.item_id in existing:
            out.append(existing[item.item_id])
            continue
        result = responder(item)
        output = ModelOutput(raw=result) if isinstance(result, str) else result
        choice = parse_choice(output.raw)
        resp = Response(
            **output.model_dump(), item_id=item.item_id, responder=responder_name, choice=choice,
            keyed=None if choice is None else (choice == item.keyed_option),
        )
        out.append(resp)
        if path is not None:
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(resp.model_dump()) + "\n")
    return out


def load_responses(jsonl_path: str | Path) -> list[Response]:
    with open(jsonl_path, encoding="utf-8") as fh:
        return [Response.model_validate(json.loads(line)) for line in fh if line.strip()]


class AnthropicResponder:
    """Forced-choice API requests, retaining metadata needed to audit failures."""

    def __init__(self, model: str, max_tokens: int = 64, *,
                 format_system: str = FORMAT_SYSTEM) -> None:
        try:
            from anthropic import Anthropic  # type: ignore[import-not-found]
        except ImportError as e:  # pragma: no cover
            raise ImportError("pip install anthropic (or: uv sync --extra eval)") from e
        self._client = Anthropic()
        self.model = model
        self.max_tokens = max_tokens
        self.format_system = format_system
        self.name = f"anthropic:{model}"

    @property
    def request_config(self) -> dict[str, object]:
        return {"temperature": 0, "max_tokens": self.max_tokens, "system": self.format_system}

    def __call__(self, item: PromptItem) -> ModelOutput:
        msg = self._client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            # Haiku 4.5 supports temperature, but SDK 1.x no longer exposes
            # it as a named argument. Send the frozen setting in the body.
            extra_body={"temperature": 0},
            system=self.format_system,
            messages=[{"role": "user", "content": item.prompt}],
        )
        return ModelOutput(
            raw="".join(getattr(block, "text", "") for block in msg.content),
            stop_reason=msg.stop_reason,
            returned_model=msg.model,
            request_id=getattr(msg, "_request_id", None),
            usage=msg.usage.model_dump(mode="json"),
        )
