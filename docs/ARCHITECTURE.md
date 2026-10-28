# Arenya — Architecture

Arenya is a multi-agent Dungeons & Dragons game whose play becomes a six-book novel series. This
document covers how the machine works. The conventions agents follow live in `rules/` (they're
loaded into the agents' system prompts); running it is covered in `docs/OPERATIONS.md`.

```
          ┌────────────────────────── dispatcher (python, no LLM) ──────────────────────────┐
          │  persisted job queue  ─►  pick gear  ─►  build prompt  ─►  Agent SDK query()    │
          │        ▲                                                         │              │
          │        │ expectations / scene events                             ▼              │
          │     engine.py  ◄──────── MCP tools (post, roll, scene_end …) ◄── agent turn     │
          │        │                                                         │              │
          │        ▼                                     PreToolUse ACL hook ┘ (file tools) │
          │  channels/*.md   state/state.json   logs/*.jsonl                                 │
          └──────────────────────────────────────────────────────────────────────────────────┘
                 ▲
     human ──────┘  `uv run arenya reply / say / status …`
```

## Why a dispatcher, not file watchers

Watchers that wake agents on file changes create races (two agents answering the same thing),
loops (agents answering each other forever) and unpredictable cost. D&D is already turn-based, so
the dispatcher makes turn order explicit and deterministic:

- **Nobody is woken unless something requires them.** The triggers are an `awaits`, a completed
  expectation, a scene/chapter event, or the idle rule.
- **One agent runs at most one turn at a time.** Up to `concurrency` different agents run in parallel.
- **The queue is persisted** (`state/state.json`), so a crash or Ctrl-C loses nothing. In-flight
  jobs are re-queued on the next start.

## Runtime: Claude Agent SDK (Python)

Each agent turn is one `claude_agent_sdk.query()` call: a headless Claude Code run with:

| option | value | why |
|---|---|---|
| `system_prompt` | `rules/common.md` + `rules/messaging.md` + `rules/<role>.md` + the agent's `IDENTITY.md` + `SOUL.md` | Persona and conventions. Stable across turns, so it caches well. |
| `model`, `effort` | from the gear (see below) | Model budgeting. |
| `tools` | `Read, Write, Edit, Glob, Grep` | No Bash or web access for any agent. |
| `mcp_servers` | in-process `arenya` server, built per turn | Game actions. Sender identity is bound by closure, so it can't be spoofed. |
| `hooks.PreToolUse` | `acl.make_hook(agent, role)` on the file tools | Hard file permissions per role. |
| `setting_sources` | `[]` | Ignore your personal `~/.claude` settings and CLAUDE.md files. |
| `resume` | the agent's session for the current scene | Continuity within a scene. Fresh context per scene. |
| `max_turns` | per role in `arenya.yaml` | Runaway guard. |

**Auth:** with `auth: subscription`, the dispatcher removes `ANTHROPIC_API_KEY` from its
environment, so the bundled Claude CLI uses your claude.ai login (`claude auth status`). Set
`auth: api_key` to bill an API key instead. `cost_usd` in `logs/usage.jsonl` is what the turn
*would* cost at API prices, which is useful for comparing gears even on a subscription.

## Code map

| file | responsibility |
|---|---|
| `arenya/config.py` | Paths, `arenya.yaml`, `roster.yaml` (re-read on every access, since the Director edits it live), gear lookup. |
| `arenya/state.py` | `state/state.json` with an `flock` (`state.locked()`), so the dispatcher and CLI can both write. |
| `arenya/channels.py` | Channel definitions, membership, file paths, the Markdown message format, and the parser. |
| `arenya/engine.py` | **All state mutation:** posting, expectations, the queue, scenes/chapters, gears and charges, sheets, logs. |
| `arenya/tools.py` | The MCP tools agents call. Thin wrappers over `engine`. |
| `arenya/acl.py` | Per-role file read/write rules plus the PreToolUse hook. |
| `arenya/prompts.py` | System prompts, session keys, wake packets (the per-turn prompt). |
| `arenya/dispatcher.py` | The main loop: launches jobs, runs SDK queries, retries, idle handling. |
| `arenya/dice.py` | Dice expression parser and roller (seeded, logged). |
| `arenya/cli.py` | The human's commands. |

## Messages and channels

### On-disk format
Channel files are Markdown, append-only, and written only by `engine.post_message`:

```markdown
### #0142 · dm → kael,lyra · narration
<!-- {"id": 142, "ts": "…", "from": "dm", "channel": "table", "type": "narration", "to": ["kael","lyra"], "awaits": ["kael","lyra"], "scene": "b1.c04.s02", "chapter": "b1.c04"} -->

Body…
```

- The heading is for humans. The one-line JSON comment is the machine record, and `channels.parse`
  reads only that. Empty fields are omitted. `-->` inside a value is escaped as `-->`.
- Bodies may not contain lines starting with `### #`, so parsing stays unambiguous.
- **Ids are global** (`state.next_id`) across all channels and books, so `#0142` is a unique reference.

| metadata key | meaning |
|---|---|
| `id`, `ts`, `from`, `channel`, `type` | Always present. |
| `to` | Addressees (informational). Groups are expanded at post time. |
| `awaits` | Who must respond (creates an expectation). |
| `reply_to` | The message being answered. |
| `spotlight` | DM-granted free peak-gear replies. |
| `scene`, `chapter` | Where in the story this message happened (`b1.c04.s02`, `b1.c04`). |
| `roller`, `total`, `seed` | On `roll` messages. Rolls can be re-derived from their seed. |
| `scene_title` | On `scene_start`. |

### Layout and rotation
```
channels/b<book>/c<chapter>/{table,ooc,whisper-<id>}.md   # chapter-scoped
channels/b<book>/{backstage,human,director}.md            # book-scoped
```
Files rotate automatically when the chapter or book counter advances, which keeps them small.
Channel membership and posting rights are in `channels.STATIC_CHANNELS` (documented for agents in
`rules/messaging.md`).

## Turn-taking: expectations

This is the core scheduling rule (`engine.py`):

1. A post with `awaits=[a,b]` creates an **expectation** `{id, from, channel, waiting_on:[a,b]}`
   and queues a `turn` job for `a` and `b`.
2. An awaited agent **satisfies** it by posting in the same channel after it, by posting anywhere
   with `reply_to` set to its id, or by calling `pass_turn`.
3. When `waiting_on` empties, the **owner** is queued for a turn.
4. If a post satisfies an expectation, its `awaits` can't include that expectation's owner (it's
   stripped), because that would wake the owner before the others have answered.
5. `awaits: [human]` (only allowed in the `human` channel) queues nothing. It records the message
   in `state.human_waiting` and notifies you. Your `arenya reply` resolves it, and the owner is woken.
6. A `request` with no `awaits` automatically awaits its `to` list.

Guards:

- **Nudge:** if a turn ends and the agent still owes a response, it gets one `nudge` turn. After
  that, the dispatcher posts an automatic pass.
- **Skip:** a queued `turn` with no new messages and nothing owed is dropped without calling the model.
- **Idle rule:** if nothing is queued or running, nobody is owed a turn, and nothing awaits the
  human, the DM is woken ("the table is quiet"). After `idle_wakes_before_pause` such wakes with no
  post, the game pauses and calls you.
- **Self-heal:** if an expectation waits on an agent with no queued job (for example because it was
  benched), that agent is queued, or auto-passed if it's inactive.

Combat needs no special engine. The DM awaits one combatant at a time, in initiative order.

## Jobs

| job | who | trigger | session | gear |
|---|---|---|---|---|
| `onboard` | dm | `arenya start` | fresh | pinned (4) |
| `turn` | anyone | awaits / completed expectation / idle | scene session (resumed) | base, or peak via spotlight/upshift |
| `nudge` | anyone | ended a turn still owing a response | scene session | base |
| `replay` | anyone | called `upshift` | scene session | peak |
| `reflect` | dm + scene cast | `scene_end` | the scene's session (cheap, cached) | pinned (1) |
| `extract` | lorekeeper | `scene_end` | fresh | base |
| `draft` | author | `scene_end` | fresh | pinned (3) |
| `revise` | author | `chapter_end` | fresh | pinned (4) |

Priority (lower runs first): dm 0, players/npcs 1, director 2, lorekeeper 3, author 4, and +5 for
non-turn jobs. Nudge and replay jobs run at -1. Play stays responsive, and the Author and Lore
Keeper catch up in the gaps.

**Sessions:** an agent keeps one SDK session per scene (`state.sessions[agent] = {key, session_id}`).
A new scene means a fresh session that starts from `MEMORY.md`, so context never grows without
bound across a six-book campaign. Continuity between scenes is carried by `MEMORY.md`, the wake
packet, `read_channel`, and the files.

**Wake packet** (`prompts.wake_packet`): the scene line; gear, reason and charges; `MEMORY.md` (in
new sessions only); what's awaiting the agent; what it's waiting on; new messages since its cursor
(filtered by channel membership, capped at `packet_message_limit`); and the job instructions. Staff
agents' turn packets include only staff channels and messages addressed to them. They read the
table from files when a job requires it.

## Gearbox: model budgets ("automatic transmission")

Every job runs in a **gear** = (model, effort), from `arenya.yaml`:

| gear | default | for |
|---|---|---|
| 1 | Haiku 5.5, low | memory upkeep |
| 2 | Sonnet 5.5, medium | everyday play, lore extraction |
| 3 | Opus 5.5, high | DM default, scene drafts, pivotal player moments |
| 4 | Opus 5.5, xhigh | DM onboarding and climaxes, chapter revisions |

`engine.pick_gear` decides, in this order:

1. **The job's pinned gear** (`job_gears`), e.g. reflect=1, revise=4.
2. **Spotlight:** the DM posted with `spotlight=[agent]`. The agent's next turn is at peak gear,
   free. Limited to `spotlights_per_scene`.
3. **Upshift:** the agent called `upshift` at the start of its turn. One charge is spent, the turn
   stops, and it's replayed at peak gear (same session).
4. Otherwise, the role's **base gear**.

**Charges:** each role gets `charges` per chapter. On a new chapter, the unspent balance plus the
new allotment is capped at `charge_cap`. The DM can `grant_charge` (`grants_per_chapter` total),
like awarding Inspiration. Players start with about 1 charge per chapter, so peak-model turns are
rare and chosen deliberately. The DM is already at Opus and spends charges to reach xhigh.

**Rate limits:** a rejected rate-limit event, or a 429 result, re-queues the job with backoff
(`rate_limit_backoff_s`). From the second attempt on, the job is **downshifted** one gear. After the
backoff list is exhausted, the game pauses and notifies you.

## Access control

`acl.py` enforces this on every `Read/Write/Edit/MultiEdit/Glob/Grep/NotebookEdit` call:

| role | read | write |
|---|---|---|
| dm | everything (except `state/`) | `plot/`, `world/`, `agents/dm/` |
| author | everything (except `state/`) | `books/`, `agents/author/` |
| lorekeeper | everything (except `state/`) | `library/`, `agents/lorekeeper/` |
| director | everything | `agents/`, `scripts/pending/` |
| player / npc | `rules/{common,messaging,player}.md`, `world/`, `library/public/`, own folder, every `IDENTITY.md`, `scripts/registry.yaml` | own `MEMORY.md`, `notes.md` |

These are never writable by any agent: `channels/`, `state/`, `logs/`, `rules/`, `arenya/`,
`docs/`, config files, approved scripts, and `agents/*/sheet.yaml` (sheets change only through the
DM's `update_sheet`, which posts the change at the table). Paths are resolved with `realpath`, so
`..` and symlink escapes fail. Searching a directory requires read access to everything beneath it.
Players read channels only through `read_channel`, which checks membership.

## MCP tools

| tool | roles | effect |
|---|---|---|
| `post` | all | `engine.post_message` |
| `pass_turn` | all | Visible pass that resolves everything the agent owes. |
| `roll` | all (`secret` = DM only) | Rolls dice. Posts a `roll` system message (or only logs it, if secret). |
| `read_channel` | all | Reads a channel the agent belongs to (any chapter). |
| `game_status` | all | Phase, scene, expectations, charges, roster. |
| `upshift` | all | Spends a charge and replays the turn at peak gear. |
| `run_script` | all (per-script roles) | Runs an approved script (60s timeout, stdout returned). |
| `scene_start`, `scene_end`, `chapter_end` | dm | Story structure plus downstream jobs. |
| `update_sheet` | dm | Deep-merges a patch into `sheet.yaml` and posts the diff. |
| `grant_charge` | dm | Awards upshift charges. |
| `register_agent` | director | Validates the folder and writes `roster.yaml`. |
| `propose_script` | director | Asks the human to approve `scripts/pending/<file>`. |

## Scene → book pipeline

```
scene_end(summary)
  ├─ author/draft       → books/book<N>/drafts/c<CC>/s<SS>.md     (per scene, gear 3)
  ├─ lorekeeper/extract → library/** + timeline + canon-log      (per scene)
  └─ reflect × (dm + cast) → agents/<id>/MEMORY.md                (gear 1)
chapter_end(summary)
  └─ author/revise      → books/book<N>/chapters/c<CC>.md         (gear 4)
```

## Logs (`logs/`, git-ignored)

- `usage.jsonl`: one line per turn: agent, job, gear, model, effort, why, seconds, SDK turns,
  `cost_usd`, token usage, ids posted, errors.
- `rolls.jsonl`: every roll, including secret ones, with its seed.
- `gears.jsonl`: upshift spends.
- `scripts.jsonl`: script runs.
- `errors.jsonl`: crashed turns, with tracebacks.

## State (`state/state.json`)

`phase`, `next_id`, `book`, `chapter`, `scene_counter`, `scene`, `scenes` (closed scenes with
message ranges and summaries), `expectations`, `cursors`, `sessions`, `charges`, `grants_used`,
`upshift`, `spotlight`, `queue`, `running`, `human_waiting`, `idle_wakes`, `paused`. Only `engine`
and the dispatcher write it, always under `state.locked()`. Back it up with the rest of the repo.

## Extending

- **New channel:** add it to `channels.STATIC_CHANNELS` and document it in `rules/messaging.md`.
- **New role:** add it to `config.ROLES`, `arenya.yaml` roles, `acl.READ/WRITE`, `engine.PRIORITY`,
  and create `rules/<role>.md`.
- **New tool:** add it in `tools.build_server` and put the logic in `engine`.
- **New job type:** queue it from `engine`, and add instructions in `prompts.wake_packet` and its
  gear in `job_gears`.
