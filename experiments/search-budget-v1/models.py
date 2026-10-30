"""Parameter-matched readouts over the same four unnamed recurrent states."""
from __future__ import annotations

import numpy as np
import torch
from torch import nn
from worlds import INPUTS

HIDDEN, QUERY, WIDTH = 4, 6, 8
RECURRENT = (INPUTS+HIDDEN+1)*HIDDEN
BASE = 2*RECURRENT+(HIDDEN+QUERY+1)*WIDTH+WIDTH+1
PARAMETERS = BASE+12
READOUTS = ("interaction", "wide_control")


def initial_mean():
    theta = np.zeros(PARAMETERS, dtype=np.float32)
    theta[RECURRENT-HIDDEN:RECURRENT] = -2
    return theta


def unpack(theta):
    p = len(theta)
    gate = theta[:, :RECURRENT].reshape(p, INPUTS+HIDDEN+1, HIDDEN)
    proposal = theta[:, RECURRENT:2*RECURRENT].reshape(p, INPUTS+HIDDEN+1, HIDDEN)
    readout = theta[:, 2*RECURRENT:BASE-(WIDTH+1)].reshape(p, HIDDEN+QUERY+1, WIDTH)
    output = theta[:, BASE-(WIDTH+1):BASE].reshape(p, WIDTH+1, 1)
    return gate, proposal, readout, output, theta[:, BASE:]


def inputs(data):
    x = torch.from_numpy(data["x"])
    lengths = torch.from_numpy(data["lengths"]).long()
    b, k, _ = data["query"].shape
    query = np.zeros((b, k+1, QUERY), dtype=np.float32)
    query[:, :, :3] = np.eye(3)[data["query_context"]][:, None]
    query[:, :k, 3:5] = np.arcsinh(data["query"]/4)
    query[:, k, 5] = 1
    return x, lengths, torch.from_numpy(query), torch.from_numpy(data["query_mask"])


def probabilities(logits, mask):
    return logits[..., :-1].masked_fill(~mask[None], -1e9).softmax(-1), logits[..., -1].sigmoid()


def readout_logits(state, query, readout_weights, output, extra, readout, drop_extra=False):
    if readout not in READOUTS:
        raise ValueError("Unknown readout")
    p, b, _ = state.shape
    k = query.shape[1]
    z = torch.cat((state[:, :, None].expand(-1, -1, k, -1), query[None].expand(p, -1, -1, -1),
                   torch.ones((p, b, k, 1), dtype=state.dtype)), -1).reshape(p, b*k, -1)
    middle = torch.bmm(z, readout_weights).tanh()
    middle = torch.cat((middle, torch.ones((p, b*k, 1), dtype=state.dtype)), -1)
    logits = torch.bmm(middle, output).reshape(p, b, k)
    if not drop_extra:
        if readout == "interaction":
            # Each of four anonymous states can interact with either payoff or query kind.
            coefficients = torch.bmm(state, extra.reshape(p, HIDDEN, 3))
            logits = logits+(coefficients[:, :, None]*query[None, :, :, 3:6]).sum(-1)
        else:
            # One additional ordinary tanh unit: 10 inputs, bias and output weight = 12.
            extra_hidden = torch.bmm(z, extra[:, :11, None]).tanh()
            logits = logits+(extra_hidden*extra[:, None, 11:12]).reshape(p, b, k)
    return logits


def small(theta, data_inputs, readout, no_memory=False, lesion=None, return_state=False, drop_extra=False):
    x, lengths, query, mask = data_inputs
    gate, proposal, readout_weights, output, extra = unpack(theta)
    p, b, t = len(theta), len(x), x.shape[1]
    state = torch.zeros((p, b, HIDDEN), dtype=theta.dtype)
    ones = torch.ones((p, b, 1), dtype=theta.dtype)
    if not no_memory:
        for step in range(t):
            z = torch.cat((x[None, :, step].expand(p, -1, -1), state, ones), -1)
            g, v = torch.bmm(z, gate).sigmoid(), torch.bmm(z, proposal).tanh()
            changed = state+g*(v-state)
            if lesion is not None:
                keep = torch.ones(HIDDEN, dtype=state.dtype)
                keep[lesion] = 0
                changed = changed*keep
            state = torch.where((step < lengths)[None, :, None], changed, state)
    logits = readout_logits(state, query, readout_weights, output, extra, readout, drop_extra)
    pred = probabilities(logits, mask)
    return (*pred, state) if return_state else pred


class Small(nn.Module):
    def __init__(self, theta, readout):
        super().__init__()
        if readout not in READOUTS:
            raise ValueError("Unknown readout")
        self.theta = nn.Parameter(torch.tensor(theta, dtype=torch.float32))
        self.readout = readout

    def forward(self, data_inputs, no_memory=False, lesion=None, drop_extra=False):
        return small(self.theta[None], data_inputs, self.readout, no_memory, lesion, drop_extra=drop_extra)


def resources(method, readout):
    return {"parameters": PARAMETERS, "state_values": HIDDEN,
            "update_matrix_macs_per_event": 2*(INPUTS+HIDDEN)*HIDDEN,
            "base_readout_matrix_macs_per_option": (HIDDEN+QUERY)*WIDTH+WIDTH,
            "extra_macs_per_target": 12 if readout == "interaction" else 0,
            "extra_macs_per_option": 3 if readout == "interaction" else 11,
            "note": "Parameter and exposure matched, not equal FLOPs or function-space initialization."}
