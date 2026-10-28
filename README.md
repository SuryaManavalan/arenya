# arenya

A multi-agent Dungeons & Dragons game, played by Claude agents, that writes a six-book novel
series from its own play.

- A **DM** agent runs a heavily reskinned 5e game. It's set in the modern day, with a subtle
  spiritual realm over reality that grows more mystical book by book. The human's six-book outline
  is the DM's loose railroad.
- **Player agents** (one per character) play their characters. Drama, roleplay and battles come
  straight from the table.
- The **Author** turns each scene into a draft and each chapter into finished prose.
- The **Lore Keeper** keeps the canon library. The **Director** creates new agents and tools.
- **You** are the world's creator. The DM interviews you about the world and asks you whenever
  play reaches new territory.

(*Arenya* is also the name of one of the main characters. In agent-facing text, the name only
ever means that character.)

| read this | for |
|---|---|
| `docs/OPERATIONS.md` | setup, running, the CLI, troubleshooting |
| `docs/ARCHITECTURE.md` | how the engine works: dispatcher, expectations, gears, ACL, formats |
| `rules/` | the conventions every agent follows (these are their system prompts) |
| `world/mechanics.md` | the game's rules skin |

```
arenya/        engine (Python, Claude Agent SDK)     rules/     agent conventions
agents/        one folder per agent + templates      world/     mechanics + interviews
channels/      all messages (engine-written)         plot/      outline + DM notes (secret)
library/       canon (public / restricted)           books/     the novels
scripts/       approved helper scripts               state/     save file    logs/  usage, rolls
```
