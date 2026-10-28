# Running the game

## Setup (once)

```bash
uv sync                      # installs claude-agent-sdk + pyyaml into .venv
claude auth status           # must show loggedIn: true (claude.ai subscription)
```

`arenya.yaml` sets `auth: subscription`, so any `ANTHROPIC_API_KEY` in your shell is ignored.

## Before the first run

1. **Outline:** put the six-book plot in `plot/outline.md`.
2. **Opening chapters:** put the human-written chapters in `books/book1/chapters/c01.md`, `c02.md`, …,
   with frontmatter `source: human` (see `books/README.md`).
3. **Characters:** for each starting PC, create `agents/<id>/` from `agents/_templates/player/`
   (IDENTITY, SOUL, MEMORY, sheet.yaml) and add them to `roster.yaml` as `role: player`.
4. **State:** set the chapter the game starts at. If the human wrote chapters 1–3, play starts
   at chapter 4:
   ```bash
   uv run arenya set-chapter 1 4
   ```
5. **Worldbuilding (optional but recommended):** have the big live conversation with Claude Code
   playing the DM. Its notes go to `world/interviews/`, and the results go into `world/`, `library/`
   and `plot/`. The DM's in-game onboarding then reads them and asks only follow-ups.

## Playing

```bash
uv run arenya start          # queue the DM's onboarding (once)
uv run arenya run            # the dispatcher; leave it running in a terminal
```

In a second terminal:

```bash
uv run arenya status                 # phase, scene, who waits on whom, queue, charges
uv run arenya inbox                  # questions awaiting you
uv run arenya reply 42 "The binding remembers, but only as grief."
uv run arenya reply 42 --file answer.md      # long answers
uv run arenya say human "New rule: ..." --type decree --to dm   # binding world fact
uv run arenya say ooc "Let's wrap this fight up" --type note    # nudge the table
uv run arenya tail table -n 30       # read the game
uv run arenya pause "lunch" / uv run arenya resume
uv run arenya approve-script encounter.py encounter --roles dm
```

When the game needs you, the dispatcher prints `>>> HUMAN NEEDED` and rings the terminal bell
(set `notify_command` in `arenya.yaml` for desktop notifications). Everything else keeps running
while it waits for you.

## Watching cost and usage

- `logs/usage.jsonl` has one line per turn: gear, model, seconds, `cost_usd` (the API-price
  equivalent), and tokens.
- Quick summary:
  ```bash
  uv run python -c "import json,collections; c=collections.Counter(); \
  [c.update({(r['agent'],r['model']): r['cost_usd'] or 0}) for r in map(json.loads, open('logs/usage.jsonl'))]; \
  [print(f'{k[0]:12} {k[1]:20} \${v:.2f}') for k,v in c.most_common()]"
  ```
- Tune `arenya.yaml`: gears, `base_gear`/`peak_gear`, charges, `concurrency`.
  A subscription has usage windows. If you hit limits, lower `concurrency` or drop the author's
  `draft` gear to 2.

## When things go wrong

| symptom | fix |
|---|---|
| Game paused: "failed N times" | Check `logs/errors.jsonl`, fix the cause, then `arenya resume`. |
| Game paused: "DM keeps waking on an idle table" | Read the table. Usually the DM is stuck; post guidance with `arenya say backstage ... --to dm --awaits dm`. |
| An agent keeps getting denied a file | Check `arenya/acl.py`. If it legitimately needs access, edit the rules there. |
| A wrong fact got into canon | `arenya say human "<correction>" --type decree --to lorekeeper dm`. |
| Want to rewind | Channels are append-only. Commit to git often (`git commit -am "after b1.c04"`). |
| Dispatcher killed mid-turn | Just restart `arenya run`. Running jobs are re-queued. |

## Git

`state/state.json` is tracked: it's the game's save file. `logs/` and `.venv/` are not.
Commit after each chapter.
