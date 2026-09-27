"""Optional GPU backend. Imported only by the local-checkpoint CLI at runtime."""
from __future__ import annotations

import importlib.metadata
import json
import platform
import time
from pathlib import Path
from typing import Any

import torch
import xgrammar as xgr
from huggingface_hub import snapshot_download
from transformers import AutoModelForCausalLM, AutoTokenizer, GenerationConfig, set_seed
from xgrammar.contrib.hf import LogitsProcessor

VERSIONS = {"torch": "2.8.0", "transformers": "4.56.2", "accelerate": "1.10.1",
            "xgrammar": "0.1.25", "huggingface-hub": "0.35.1", "numpy": "2.3.3"}
CLOSE = 151668
EOS = [151645, 151643]


def compile_grammar(tokenizer: Any, vocab_size: int, schema: dict[str, Any]) -> Any:
    info = xgr.TokenizerInfo.from_huggingface(
        tokenizer, vocab_size=vocab_size, stop_token_ids=EOS,
    )
    # The schema converter omits JSON's legal surrounding whitespace. Qwen normally
    # emits two newlines after </think>; accept these without inserting/stripping text.
    whitespace = xgr.Grammar.from_ebnf(r"root ::= [ \n\r\t]*")
    grammar = xgr.Grammar.concat(whitespace, xgr.Grammar.from_json_schema(json.dumps(schema)),
                                whitespace)
    return xgr.GrammarCompiler(info).compile_grammar(grammar)


class AfterThinking:
    """Apply the final-answer grammar only after the generated thinking-end token.

    One instance per single-sequence generation. No changes to reasoning logits.
    XGrammar's first active call treats the entire reasoning prefix as prefill.
    """

    def __init__(self, processor: Any, prompt_length: int):
        self.processor = processor
        self.prompt_length = prompt_length
        self.active = False

    def __call__(self, input_ids: Any, scores: Any) -> Any:
        if input_ids.shape[0] != 1:
            raise ValueError("Only batch size one is supported")
        if input_ids.shape[1] > self.prompt_length and input_ids[0, -1].item() == CLOSE:
            self.active = True
        return self.processor(input_ids, scores) if self.active else scores


def doctor() -> dict[str, Any]:
    versions = {p: importlib.metadata.version(p) for p in VERSIONS}
    if any(versions[p].split("+")[0] != v for p, v in VERSIONS.items()):
        raise ValueError("GPU package version mismatch; use the separate frozen environment")
    if platform.system() != "Linux" or platform.machine() != "x86_64":
        raise ValueError("This protocol requires Linux x86_64")
    if platform.python_version_tuple()[:2] != ("3", "11"):
        raise ValueError("This protocol requires Python 3.11")
    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise ValueError("Expose exactly one NVIDIA GPU, e.g. CUDA_VISIBLE_DEVICES=0")
    if not torch.cuda.is_bf16_supported():
        raise ValueError("GPU must support BF16")
    free, total = torch.cuda.mem_get_info()
    if free < 74 * 2**30:
        raise ValueError("Need at least 74 GiB free VRAM; use an otherwise idle 80 GB GPU")
    return {"packages": versions, "python": platform.python_version(),
            "platform": platform.platform(), "torch_cuda": torch.version.cuda,
            "gpu": torch.cuda.get_device_name(0),
            "gpu_capability": list(torch.cuda.get_device_capability(0)),
            "vram_free_bytes": free, "vram_total_bytes": total,
            "attention_implementation": "sdpa", "dtype": "bfloat16",
            "tensor_parallelism": 1, "quantization": None}


def download(spec: dict[str, Any], cache: Path) -> Path:
    return Path(snapshot_download(repo_id=spec["model"], revision=spec["revision"],
                                  cache_dir=str(cache), allow_patterns=list(spec["files"])))


def cached_snapshot(spec: dict[str, Any], cache: Path) -> Path:
    return Path(snapshot_download(repo_id=spec["model"], revision=spec["revision"],
                                  cache_dir=str(cache), allow_patterns=list(spec["files"]),
                                  local_files_only=True))


class Backend:
    def __init__(self, snapshot: Path, schema: dict[str, Any]):
        self.tokenizer = AutoTokenizer.from_pretrained(snapshot, local_files_only=True,
                                                       trust_remote_code=False)
        if self.tokenizer.encode("</think>", add_special_tokens=False) != [CLOSE]:
            raise ValueError("Unexpected thinking separator token")
        self.model = AutoModelForCausalLM.from_pretrained(
            snapshot, local_files_only=True, trust_remote_code=False,
            torch_dtype=torch.bfloat16, device_map={"": 0}, attn_implementation="sdpa",
        ).eval()
        if {p.device.type for p in self.model.parameters()} != {"cuda"}:
            raise ValueError("CPU offload is outside this frozen configuration")
        if {p.dtype for p in self.model.parameters()} != {torch.bfloat16}:
            raise ValueError("Unexpected weight dtype")
        self.grammar = compile_grammar(self.tokenizer, self.model.config.vocab_size, schema)

    def __call__(self, request: dict[str, Any], progress_path: Path) -> dict[str, Any]:
        # Set every item's seed independently; no retries or answer-based selection.
        set_seed(request["seed"])
        prompt = self.tokenizer.apply_chat_template(
            request["messages"], tokenize=False, add_generation_prompt=True, enable_thinking=True,
        )
        inputs = self.tokenizer(prompt, return_tensors="pt", add_special_tokens=False).to("cuda")
        prompt_ids = inputs.input_ids[0].tolist()
        if len(prompt_ids) + request["max_new_tokens"] > self.model.config.max_position_embeddings:
            raise ValueError("Prompt plus output allowance exceeds native context")
        processor = AfterThinking(LogitsProcessor(self.grammar), len(prompt_ids))
        generation = GenerationConfig(
            do_sample=True, temperature=0.6, top_p=0.95, top_k=20, min_p=0.0,
            max_new_tokens=request["max_new_tokens"], repetition_penalty=1.0,
            eos_token_id=EOS, pad_token_id=151643, bos_token_id=151643,
            num_beams=1, num_return_sequences=1, use_cache=True,
        )
        # Preserve the exact rendered input before generation, even if the GPU fails.
        progress_path.write_text(json.dumps({"rendered_prompt": prompt,
                                            "input_token_ids": prompt_ids}) + "\n")
        started = time.monotonic()
        torch.cuda.reset_peak_memory_stats()
        with torch.inference_mode():
            output = self.model.generate(**inputs, generation_config=generation,
                                         logits_processor=[processor])
        tokens = output[0, len(prompt_ids):].tolist()
        from wtrbench.paired.local_checkpoint import split_tokens
        parts = split_tokens(tokens, self.tokenizer.decode)
        return {**parts, "rendered_prompt": prompt, "input_token_ids": prompt_ids,
                "generated_token_ids": tokens,
                "raw_text": self.tokenizer.decode(tokens, skip_special_tokens=False),
                "elapsed_seconds": time.monotonic() - started,
                "peak_cuda_allocated_bytes": torch.cuda.max_memory_allocated(),
                "peak_cuda_reserved_bytes": torch.cuda.max_memory_reserved()}
