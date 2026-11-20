"""Load pinned upstream game/agent definitions without importing plotting infrastructure.

Upstream files are downloaded unchanged to run artifacts, not redistributed in this repo.
Only the listed AST definitions are executed. No upstream definition is rewritten.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import urllib.request
from collections import OrderedDict
from copy import copy
from pathlib import Path

import numpy as np
import scipy as sp
import scipy.special

COMMIT = "8d7f9946b3cc4ff1d7fae7a1a7a149499c35dede"
HASHES = {
    "games.py": "1fcb6e25de7bfea5fa44ddfbeced6a482b75ffeaee97947241c62a58476ca653",
    "agents.py": "2b387b6a407177566a8783da2875f0243be4cfed9c51c21e9e3b0ec87fa63833",
    "utils.py": "8c52b713a428c15a0ce1fb9fd46e0ee5451633ad7a3eddc5dbafb91ebbfec0fa",
}
DEFINITIONS = {
    "games.py": ("Playable", "Decision", "engine_gen"),
    "utils.py": ("softmax",),
    "agents.py": ("add_tremble", "AgentType", "Agent", "SelfishAgent", "AltruisticAgent"),
}


def verify(folder):
    for name, expected in HASHES.items():
        if hashlib.sha256((Path(folder)/name).read_bytes()).hexdigest() != expected:
            raise ValueError("Upstream checksum mismatch: "+name)


def download(folder):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    for name in HASHES:
        url = f"https://raw.githubusercontent.com/maxkw/evolution/{COMMIT}/{name}"
        with urllib.request.urlopen(url, timeout=60) as response:
            (folder/name).write_bytes(response.read())
    verify(folder)


def load(folder):
    verify(folder)
    namespace = {"np": np, "sp": sp, "array": np.array, "OrderedDict": OrderedDict, "copy": copy}
    for name, selected in DEFINITIONS.items():
        tree = ast.parse((Path(folder)/name).read_text())
        body = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in selected]
        if {node.name for node in body} != set(selected):
            raise ValueError("Missing pinned upstream definitions")
        # Execute only these pinned, checksum-verified upstream definitions.
        exec(compile(ast.Module(body=body, type_ignores=[]), name, "exec"), namespace)  # noqa: S102
    return namespace


def sample_menu(namespace, rng):
    # Upstream uses the legacy global RNG. Restore its state after each draw.
    state = np.random.get_state()
    try:
        np.random.seed(int(rng.integers(0, 2**31-1)))
        game = namespace["engine_gen"](nactions=3, max_players=2, benefit=5, cost=1, tremble=.02)
    finally:
        np.random.set_state(state)
    return game


def actor(namespace, kind):
    name = "AltruisticAgent" if kind else "SelfishAgent"
    return namespace[name]({"beta": 1.0}, world_id=0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    download(parser.parse_args().folder)
