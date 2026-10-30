"""Generic inherited state updates; no willingness/ability masks or named banks."""
from __future__ import annotations

import numpy as np
import torch
from torch import nn
from worlds import INPUTS

HIDDEN = 4
QUERY = 6  # Three public context indicators, two option payoffs, one query-kind indicator.
WIDTH = 8
RECURRENT = (INPUTS+HIDDEN+1)*HIDDEN
PARAMETERS = 2*RECURRENT+(HIDDEN+QUERY+1)*WIDTH+WIDTH+1


def initial_mean():
    theta = np.zeros(PARAMETERS, dtype=np.float32)
    # Domain-independent initial retention bias, shared by search and matched gradient control.
    theta[RECURRENT-HIDDEN:RECURRENT] = -2
    return theta


def unpack(theta):
    p = len(theta)
    gate = theta[:, :RECURRENT].reshape(p, INPUTS+HIDDEN+1, HIDDEN)
    proposal = theta[:, RECURRENT:2*RECURRENT].reshape(p, INPUTS+HIDDEN+1, HIDDEN)
    readout = theta[:, 2*RECURRENT:-(WIDTH+1)].reshape(p, HIDDEN+QUERY+1, WIDTH)
    output = theta[:, -(WIDTH+1):].reshape(p, WIDTH+1, 1)
    return gate, proposal, readout, output


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


def small(theta, data_inputs, no_memory=False, lesion=None, return_state=False):
    x, lengths, query, mask = data_inputs
    gate, proposal, readout, output = unpack(theta)
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
    k = query.shape[1]
    z = torch.cat((state[:, :, None].expand(-1, -1, k, -1), query[None].expand(p, -1, -1, -1),
                   torch.ones((p, b, k, 1), dtype=theta.dtype)), -1).reshape(p, b*k, -1)
    middle = torch.bmm(z, readout).tanh()
    middle = torch.cat((middle, torch.ones((p, b*k, 1), dtype=theta.dtype)), -1)
    logits = torch.bmm(middle, output).reshape(p, b, k)
    pred = probabilities(logits, mask)
    return (*pred, state) if return_state else pred


class Small(nn.Module):
    def __init__(self, theta):
        super().__init__()
        self.theta = nn.Parameter(torch.tensor(theta, dtype=torch.float32))

    def forward(self, data_inputs, no_memory=False, lesion=None):
        return small(self.theta[None], data_inputs, no_memory=no_memory, lesion=lesion)


class Dense(nn.Module):
    def __init__(self):
        super().__init__()
        self.core = nn.GRU(INPUTS, 16, batch_first=True)
        self.readout = nn.Sequential(nn.Linear(16+QUERY, 16), nn.Tanh(), nn.Linear(16, 1))

    def forward(self, data_inputs, no_memory=False, lesion=None):
        x, lengths, query, mask = data_inputs
        states, _ = self.core(x)
        state = states[torch.arange(len(x)), (lengths-1).clamp_min(0)]*(lengths > 0)[:, None]
        if no_memory:
            state = state*0
        if lesion is not None:
            keep = torch.ones(16)
            keep[lesion] = 0
            state = state*keep
        z = torch.cat((state[:, None].expand(-1, query.shape[1], -1), query), -1)
        return probabilities(self.readout(z)[..., 0][None], mask)


def observed_loss(pred, data):
    """Future observed outcomes only: no truth fields, posterior, or actor labels."""
    choice, ability = pred
    y = torch.from_numpy(data["y_choice"]).long()
    selected = choice.gather(-1, y[None, :, None].expand(len(choice), -1, 1))[..., 0]
    choice_loss = .5*(choice.square().sum(-1)-2*selected+1)
    a = torch.from_numpy(data["y_ability"])
    if bool((a < 0).all()):
        return choice_loss.mean(-1)
    if bool((a < 0).any()):
        raise ValueError("Partially missing future execution targets")
    return (.5*(choice_loss+(ability-a).square())).mean(-1)


def resources(method):
    if method == "dense_gradient":
        model = Dense()
        return {"parameters": sum(p.numel() for p in model.parameters()), "state_values": 16,
                "update_matrix_macs_per_event": 3*16*(INPUTS+16), "readout_matrix_macs_per_option": (16+QUERY)*16+16}
    return {"parameters": PARAMETERS, "state_values": HIDDEN,
            "update_matrix_macs_per_event": 2*(INPUTS+HIDDEN)*HIDDEN,
            "readout_matrix_macs_per_option": (HIDDEN+QUERY)*WIDTH+WIDTH}
