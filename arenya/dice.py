"""Dice expressions.

Grammar (case-insensitive, spaces ignored):
    expr   := term (('+'|'-') term)* [' adv' | ' dis']
    term   := [N]dM[kh K | kl K] | integer
Examples: d20+5, d20+5 adv, 4d6kh3, 2d8+1d6+3, d100, 1d20-1 dis
`adv`/`dis` roll the first d20 term twice and keep the higher/lower.
"""
from __future__ import annotations

import random
import re

TERM_RE = re.compile(r"([+-]?)(?:(\d*)d(\d+)(?:(kh|kl)(\d+))?|(\d+))")
MAX_DICE = 200


class DiceError(ValueError):
    pass


def roll(expr: str, seed: int | None = None) -> dict:
    seed = seed if seed is not None else random.SystemRandom().getrandbits(48)
    rng = random.Random(seed)
    text = expr.lower().strip()
    mode = None
    for m in ("adv", "dis"):
        if text.endswith(m):
            mode, text = m, text[: -len(m)]
    text = text.replace(" ", "")
    if not text:
        raise DiceError("empty dice expression")

    pos, total, parts, n_dice = 0, 0, [], 0
    adv_used = False
    natural = None  # kept face of the first single d20, for crit/fumble calls
    while pos < len(text):
        m = TERM_RE.match(text, pos)
        if not m or m.end() == pos:
            raise DiceError(f"can't parse '{expr}' near '{text[pos:]}'")
        if pos > 0 and not m.group(1):
            raise DiceError(f"missing + or - in '{expr}'")
        sign = -1 if m.group(1) == "-" else 1
        if m.group(6):
            val = int(m.group(6))
            parts.append(f"{'-' if sign < 0 else '+'}{val}")
        else:
            count, sides = int(m.group(2) or 1), int(m.group(3))
            if count < 1 or sides < 2:
                raise DiceError(f"bad dice '{m.group(0)}'")
            n_dice += count
            if n_dice > MAX_DICE:
                raise DiceError("too many dice")
            rolls = [rng.randint(1, sides) for _ in range(count)]
            note = ""
            if mode and sides == 20 and count == 1 and not adv_used:
                second = rng.randint(1, 20)
                pick = max(rolls[0], second) if mode == "adv" else min(rolls[0], second)
                note = f" {mode} [{rolls[0]}, {second}]"
                rolls, adv_used = [pick], True
            kept = rolls
            if m.group(4):
                k = int(m.group(5))
                kept = sorted(rolls, reverse=(m.group(4) == "kh"))[:k]
                note += f" {m.group(4)}{k} of {rolls}"
            val = sum(kept)
            if natural is None and sides == 20 and count == 1:
                natural = kept[0]
            parts.append(f"{'-' if sign < 0 else '+'}{count}d{sides}{note} = {val}"
                         if note else f"{'-' if sign < 0 else '+'}{count}d{sides} {rolls} = {val}")
        total += sign * val
        pos = m.end()
    if mode and not adv_used:
        raise DiceError(f"'{mode}' needs a single d20 term")

    breakdown = " ".join(parts).lstrip("+")
    return {"expr": expr, "total": total, "breakdown": breakdown, "natural": natural, "seed": seed}
