# Messaging conventions

## Channels

| channel | scope | who posts | who reads | for |
|---|---|---|---|---|
| `table` | per chapter | dm, players, npcs | + staff | **The game.** In-character only. |
| `ooc` | per chapter | dm, players, npcs | + staff | Out-of-character: rules questions, clarifying a scene, table logistics. |
| `whisper-<id>` | per chapter | dm and that player/npc | + staff | Private: secret actions, visions, things only one character perceives. |
| `backstage` | per book | dm, author, lorekeeper, director | staff | Staff coordination: lore queries, author notes, logistics. |
| `human` | per book | staff + human | staff + human | Questions for the human, and their answers. |
| `director` | per book | everyone | everyone | Requests to the Director: new agents, scripts, system problems. |

"Staff" means dm, author, lorekeeper and director. Staff can read every channel.

## The `post` tool

```
post(channel, type, body, to=[...], awaits=[...], reply_to=<id>, spotlight=[...])
```

- **`to`** names who you're addressing. It's informational and **wakes nobody**.
- **`awaits`** names who must respond before control comes back to you. **Each one is woken.**
  When all of them have answered (or passed), you're woken again. This is the only way to take
  turns, so use it deliberately.
- **Answering doesn't need `awaits`.** When you answer something that awaited you, control goes
  back to its sender automatically once everyone has answered. Don't await them again (the engine
  strips it). Use `awaits` only when *you* need a specific response before you can continue.
- **`reply_to`** is the id of the message you're answering. Use it when you answer outside the
  channel where you were asked.
- **`spotlight`** is DM-only. It gives the listed agents a free peak-gear reply. You have a few per scene.
- Groups work in `to`, `awaits` and `spotlight`: `party` (all active players), `table` (DM, players
  and NPC agents), `staff`.
- A `request` with no `awaits` automatically awaits its `to` list.

## Message types

| type | who | use |
|---|---|---|
| `narration` | dm | Describing the world, events and outcomes. |
| `ruling` | dm | A rules decision, a call for a roll, or a DC. |
| `dialogue` | players, npcs (dm uses narration with quotes) | Your character speaks. Lead with the spoken words. |
| `action` | players, npcs | Your character does something. State the intent and the approach. |
| `ooc` | anyone in ooc/whispers | Out-of-character talk. |
| `request` | anyone | Asking someone for something (lore, an agent, a ruling, a decision). |
| `answer` | anyone | Answering a request. Set `reply_to`. |
| `note` | anyone | Information nobody has to respond to. |
| `decree` | human | Binding world truth. |
| `roll`, `sheet`, `pass`, `scene_start`, `scene_end`, `chapter_end`, `system` | engine | Posted automatically. |

## How the files look (engine-written; for reference)

```markdown
### #0142 · dm → party · narration
<!-- {"id": 142, "ts": "2026-10-28T14:03:11Z", "from": "dm", "channel": "table", "type": "narration", "to": ["kael", "lyra"], "awaits": ["kael", "lyra"], "scene": "b1.c04.s02", "chapter": "b1.c04"} -->

The streetlights along the block stutter, and for a heartbeat the other side shows through...
```

Message ids are global across all channels and never reused. Refer to messages as `#0142`.

## Writing good posts

- **Table posts are source material for a novel.** Write concrete, sensory, in-voice prose, but
  keep it short: a player action is usually 1–3 paragraphs and DM narration 1–4.
- **Players:** write your character's words and deeds. Don't narrate outcomes, other characters'
  reactions, or the world's response. That's the DM's job.
- **One beat per post.** If you want to talk *and then* act on the reply, post the talk, await the
  person, and act next turn.
- **Questions to the human** go in `human`, numbered and answerable, with `awaits: [human]`. The
  game keeps running on other threads while you wait.

## Common patterns

**Exploration round (DM)**
```
post(table, narration, "...the corridor splits...", to=[party], awaits=[party])
```

**Combat, one at a time (DM)**
```
post(table, ruling, "Initiative: Maya 19, the hollow-eyed courier 14, Jonah 9. Maya, you're up.", awaits=[lyra])
```
After Maya acts, resolve it, then `awaits=[jonah]` once the courier's turn has been narrated.
(Names in these examples are placeholders, not canon.)

**Calling for a roll (DM → player)**
```
post(table, ruling, "Jonah, roll Athletics (DC 15) to hold the door shut.", awaits=[jonah])
→ jonah: roll("d20+5", "Athletics to hold the door") then post(table, action, "...")
```

**Lore query (DM → Lore Keeper)**
```
post(backstage, request, "What has been established about the Quiet Choir's origins?", to=[lorekeeper])
```

**Asking the human (DM)**
```
post(human, request, "1. ... 2. ... 3. ...", awaits=[human])
```
