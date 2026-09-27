"""CPU integration fixture: real tokenizer/grammar/generate, tiny random weights.

Downloads tokenizer/config only (~16 MB), never the 32B weights. Produces no empirical data.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import torch
from huggingface_hub import snapshot_download
from transformers import AutoTokenizer, GenerationConfig, Qwen3Config, Qwen3ForCausalLM
from xgrammar.contrib.hf import LogitsProcessor

from wtrbench.paired import local_checkpoint as local


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=Path("runs/local-smoke-cache"))
    args = parser.parse_args()
    local.verify_freeze()
    backend = local.load_backend()
    small_files = [p for p in local.checkpoint_spec()["files"] if not p.startswith("model")]
    path = snapshot_download(local.MODEL, revision=local.REVISION, cache_dir=str(args.cache),
                             allow_patterns=small_files)
    tokenizer = AutoTokenizer.from_pretrained(path, local_files_only=True, trust_remote_code=False)
    assert tokenizer.encode("</think>", add_special_tokens=False) == [local.CLOSE]
    request = local.schedule()[0]
    prompt = tokenizer.apply_chat_template(request["messages"], tokenize=False,
                                            add_generation_prompt=True, enable_thinking=True)
    assert prompt.endswith("<|im_start|>assistant\n")
    inputs = tokenizer(prompt, return_tensors="pt", add_special_tokens=False)
    n = inputs.input_ids.shape[1]
    grammar = backend.compile_grammar(tokenizer, 151936, request["schema"])
    raw = '<think>Programmed CPU fixture, not a research response.\n</think>\n\n{"brief_basis":"Fixture only","answer":"A"}'
    tokens = tokenizer.encode(raw, add_special_tokens=False) + [local.EOS[0]]

    class ScriptedLogits:
        def __call__(self, input_ids, scores):
            scores.fill_(-float("inf"))
            scores[0, tokens[input_ids.shape[1] - n]] = 0
            return scores

    # Tests both the actual generate call and the grammar's acceptance of every final token.
    torch.set_num_threads(2)
    torch.manual_seed(1)
    model = Qwen3ForCausalLM(Qwen3Config(
        vocab_size=151936, hidden_size=32, intermediate_size=64, num_hidden_layers=1,
        num_attention_heads=4, num_key_value_heads=2, head_dim=8,
        max_position_embeddings=2048, eos_token_id=list(local.EOS), pad_token_id=151643,
    )).eval()
    gate = backend.AfterThinking(LogitsProcessor(grammar), n)
    with torch.inference_mode():
        generated = model.generate(
            **inputs,
            generation_config=GenerationConfig(
                do_sample=True, temperature=.6, top_p=.95, top_k=20, min_p=0.,
                max_new_tokens=len(tokens) + 1, eos_token_id=list(local.EOS), pad_token_id=151643,
            ), logits_processor=[ScriptedLogits(), gate],
        )[0, n:].tolist()
    assert generated == tokens
    assert gate.active
    parts = local.split_tokens(generated, tokenizer.decode)
    assert parts["reasoning"] == "Programmed CPU fixture, not a research response.\n"
    assert local.parsed_response(local.social.generate_items()[0], parts)["answer"] == "A"
    # Before the separator the processor must leave arbitrary reasoning logits unchanged.
    second_gate = backend.AfterThinking(LogitsProcessor(grammar), n)
    scores = torch.zeros((1, 151936))
    assert torch.equal(second_gate(inputs.input_ids, scores.clone()), scores)
    # After the separator, grammar must actually reject a non-JSON first token.
    prefix = torch.cat([inputs.input_ids, torch.tensor([[local.CLOSE]])], dim=1)
    masked = second_gate(prefix, scores.clone())
    bad = tokenizer.encode("banana", add_special_tokens=False)[0]
    assert torch.isneginf(masked[0, bad])
    assert torch.isfinite(masked).any()
    print("PASS: real Transformers/Qwen3 generation, thinking gate, XGrammar enforcement, strict decoding.")
    print("Programmed CPU integration fixture only; no Qwen3-32B behavioral responses collected.")


if __name__ == "__main__":
    main()
