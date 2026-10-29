# Mechanics

D&D 5e underneath, **heavily reskinned** for a modern-day world with a subtle spiritual realm
laid over it. Players read this file, so keep secrets in `plot/` and `library/restricted/`.

Every rule is tagged with its source: `[human]` defined by the human (binding) · `[dm-proposed]`
invented by the DM, not yet confirmed · `[approved]` invented by the DM and confirmed by the human.
Every rule also carries the book it applies from, e.g. `(from B1)`: the world gets more mystical as
the series goes on, so later books unlock rules that don't exist yet in earlier ones.

## Authority
Who may define each area. `human-defines`: the DM must ask. `dm-propose`: the DM may invent but
must tell the human. `dm-free`: the DM invents freely.

| area | authority |
|---|---|
| Spirit magic (sources, costs, limits, look & feel) | human-defines |
| The spiritual realm & cosmology | human-defines |
| Esoteric factions | human-defines |
| Escalation across the books (what unlocks when) | human-defines |
| Mundane modern-day details (places, institutions, gear) | dm-free |
| Combat & rules plumbing (DCs, damage, conditions) | dm-propose |
| Everything else | dm-propose |

## The planes `[human]` (from B1)
Reality is a ladder of increasingly subtle planes. The physical world is the bottom rung. Each book
opens the next layer: **Astral → Cosmic → Temporal → Ethereal → Celestial → Causal**.
"With new levels come new devils." Only the Astral is in play in Book 1.

## The physical and the astral `[human]` (from B1)
- **The astral (spirit) plane** is the plane closest to the physical. It is **not a mirror** of the
  physical world. It's an emergent world, made of the archetypal characteristics, properties and
  mechanics of physical reality, anthropomorphized. It has shadows and projections of the physical:
  tree spirits near trees, tinkering intelligences near AI labs. But it's stranger, more complex and
  more abstract than a mirror.
- **Bodies:** a fully incarnated being has a physical body and increasingly subtle bodies on top of
  it (astral, ether, … causal). Spirits are entities without a physical body.
- **Perception:** to an ordinary person, seeing a spirit (even one that came through a rift) is so
  violent to their sense of reality that it reads as **psychosis**, especially a large spirit.
  Spirits never look like ordinary animals.

## Spirit battles `[human]` (from B1)
- Spirit battles are fought **in the higher-dimensional astral plane**, not in 3D space. Combatants
  commit their whole energy and astral bodies to the fight, so their **physical bodies freeze**:
  they're motionless, staring at their opponent.
- Losing can kill. The witnessed deaths so far are a freeze of ~30–60 seconds followed by collapse
  (diagnosed as aneurysm).
- 5e combat mechanics live **here**, in the astral battle, with D&D's fighting rules reskinned.
- Time intuition (flavor, not physics; see `world/reference/extra-dimensional-time-notes.md`): moving
  through the extra dimensions costs little or no physical time. A long battle can fit inside a
  physical pause. `[dm-proposed]` The deeper the plane, the more of its time fits inside one
  instant of the plane below.

## The bulk `[human]` (from B1)
**The bulk** is the in-world name for the extra dimensions stacked on top of physical reality.
Spirit battles happen there. The higher planes are deeper layers of the bulk, each with its own
clock running inside the instants of the one below.

## Astral combat `[dm-proposed]`, built on `[human]` principles (from B1)
**Prana and embodiment** `[human]`: a living being's life force (prana) can be pointed into its
astral and higher bodies and away from the physical. **Chakra level** shows how far up a being can
embody itself. `[dm-proposed]` As a stat, this is **Ascent 1–7** (root to crown). Ascent 3 or higher is
needed to fight in the astral. Book 1 heroes sit around 3–4. Ascent rises at story milestones, not
with XP.

**Going into the bulk:**
- A host enters the bulk as a bonus action. A non-host can enter only if a spirit or host carries
  them in (which takes an action, and they must be touching or bonded).
- **Joining mid-battle:** hosts and carried allies can enter a battle already in progress. They
  arrive at the top of the next astral round. Rescues are meant to be set pieces.
- **Clocks:** about **one astral round per physical second** (DM may vary this by depth). A 5-round
  duel is a 5-second freeze. The 30–60 second freezes seen so far were long, lopsided executions.

**The body left behind** gains the **Entranced** condition:
- Incapacitated, can't move or speak, unaware of the physical world. Eyes locked on the opponent's
  physical body (if it has one).
- Any attack on it **hits automatically and counts as a critical hit**. Damage to an Entranced body
  also forces a DC 10 Con save (or half the damage, if higher). Failing it severs you from the battle
  and drops you to 0 astral HP. ("If you get stabbed, you're probably cooked.")
- An ally can spend an action to shake you. You may then return at the start of your next astral
  turn instead of finishing the fight.

**The astral body** has its own sheet values. Use 5e combat with these reskins:
- **Astral HP** = 10 + (Ascent × your spirit-casting modifier) + level × (your house's hit die).
  Physical HP and astral HP are separate.
- Abilities in the astral: Strength → **Will** (force of spirit), Dexterity → **Flow**, Constitution
  → **Anchor** (holding on to yourself). Int, Wis and Cha stay as they are.
- Weapons don't exist there unless they have an astral echo. You fight with your **house**: its
  spirit powers are your attacks and spells (see Houses).

**At 0 astral HP**, the outcome isn't automatically death. Make **astral death saves**, as in 5e:
- **Stabilized, or saved by an ally:** you snap back to your body with an **Astral Wound**. Roll or
  choose one: lost memories, a severed spirit bond (temporary), a chakra drop (−1 Ascent until healed),
  nightmares and leaking perception (you see spirits uncontrollably), or a body that stays comatose
  until someone retrieves you from the bulk.
- **Three failures, or an enemy's finishing strike on a downed astral body:** the astral body is
  destroyed. The physical body dies within moments (a "cerebral event"). This is what the
  assassins do.

**Protected characters** `[human]`: Arenya, Malachi and Abernathy can't permanently die. If one
falls, they're **Lost** (not dead), and the other characters must do everything they can to bring them
back. Losing them is a story, not an ending. Every other character can die.

## Spirits, houses and hosts `[human]` (from B1)
- **Spirits** are metaphysical entities that emerge from the archetypal properties of physical
  reality, anthropomorphized. They live in the astral plane.
- **Six houses:** light, dark, heavy, sharp, flexible, sticky (sticky is akin to **magnetism**).
- **Hosting** is both **bloodline and reincarnation.** Esoterically advanced families used high
  **tantra technology** to bind their spirit lines to their bloodlines. Details are deliberately open.
- A family's **main spirit** can be an incomprehensibly complex being, akin to a dragon, an angel or
  a Hindu deity. Lesser spirits can serve it (squires, retainers).
- Spirits of a **place** can adopt someone who wasn't born of their lineage, and even make them
  their champion.

### Arenya's two lines `[human]` + `[dm-proposed]` details
- `[human]` Arenya is a child of **light and dark**. Her lineage's spirits were formed elsewhere,
  while the spirits of the place she was born adopted her and made her their champion, even over
  their "true champion".
- `[dm-proposed]` **Light is the Sowri blood-line.** It's a South Indian lineage bound by tantra
  technology. Its main spirit is a vast deity-like being of lamplight and dawn (working name
  *Sahasrajyoti*, "Thousand Lights"). Susmithaa hosts it; Abernathy serves it as squire. Hence
  "go with all the light you can carry."
- `[dm-proposed]` **Dark is the land of San Francisco.** It's an old spirit lineage of this coast,
  shaped by the first peoples here and carrying deep currents of Mesoamerican cosmology: the jaguar
  sun that travels the underworld at night, the many-layered Xibalba below, the sacred mountain.
  Here "dark" doesn't mean evil. It means fog, night, the underworld, dreams, and what's hidden and
  fertile.
- `[dm-proposed]` **The mountain in Arenya's dreams** (alive, ancient, asleep, breathing) is the
  land's great dark spirit. It's echoed in **Mount Tamalpais, "the Sleeping Lady."** It chose her.
- *(Writing note: the land lineage is a fictional spirit tradition inspired by these cosmologies.
  It is not a depiction of any living people's actual sacred practice. Any indigenous characters
  are full people, not mystical props.)*

## Meta mages `[human]` (from B1)
- Mass-produced spirit users: Typhus's army. They're not true spiritual people, and they're dependent
  on their tools: a made-up **chemical** plus a **neural-link chip** that induces hypnosis, along
  with other "new-age spiritual technologies". The tech is sci-fi and mystical, not realistic.
- Their connection to the spirit plane is **weaker**, and one-on-one they lose to a true host. In
  numbers they can bring true hosts down.
- The rifts are what let them (and leaking spirits) act in the physical world.
- `[dm-proposed]` The tech: the **Crown**, a neural-lace implant at the crown of the skull that induces
  a hypnotic, flattened state, and **Vesper**, an injected/inhaled compound that opens a borrowed
  channel to the bulk. Without Vesper, the Crown is a dead weight. Without the Crown, Vesper is a
  bad trip. Long-term users become **forgettable**: flat affect, no idle fidgets, faces people slide
  off of.

## Core rules (5e baseline)
- Ability checks, saves, advantage/disadvantage, combat flow and conditions follow 5e unless overridden here.
- Modern-day gear (phones, cars, firearms, money, the internet, police, consequences) follows real-world logic. The DM sets DCs and damage for it.

## Spirit magic `[approved]` (human, #0027: "go with your drafts on all eight") (from B1)
- **Source.** A host's power belongs to their spirit. The host lends it a body and a will and points
  it, and the spirit lends its house's nature. Meta mages borrow a channel through Vesper. What
  they're actually using is rendered spirit.
- **Prana is the currency.** 5e spell slots and similar resources (ki, sorcery points, pact slots)
  are reskinned as **prana**: life force pointed upward. It recovers with a long rest, or with an
  hour of breath and stillness for a short-rest class.
- **Overdraw.** A host can keep going after their prana runs out. Each extra slot-level costs either a
  level of **exhaustion** (drawn from the physical body) or **1d8 astral HP per slot level** (drawn
  from the astral body). A deity-class spirit (Sahasrajyoti) can also be asked to *push*. When it
  pushes, the effect is stronger, and the spirit gets a little more of the wheel (DM-run consequence).
- **Where it works (Book 1).** Spirit powers work **fully in the bulk**. In the physical world they
  work only **subtly** outside a rift: intuition, perception, luck, a lamp that brightens, fog that
  thickens on cue, roughly cantrip-grade "coincidence". **Near a rift**, full effects bleed into the
  physical. As the rifts spread through Book 1, so does physical magic.
- **What it can't do (Book 1).** It can't bring back a destroyed astral body (that's death). It
  can't create lasting matter. It can't touch time (that belongs to later books and to whatever
  Abernathy was).

### The six houses: powers `[approved]` (#0027)
| house | archetype | in a fight (the bulk) | outside a fight |
|---|---|---|---|
| **Light** | revelation, radiance, warding | radiant force, wards, burning away illusion, healing | seeing what's true, being *seen* |
| **Dark** | night, fog, dream, the underworld | concealment, fear, passage through hidden ways, dream-walk | hiding, knowing the land, dreams that mean things |
| **Heavy** | gravity, mass, structure | crushing, pinning, immovability, shockwaves | endurance, structural sense (Yuri was an architect) |
| **Sharp** | edges, precision, severance | cutting, piercing, severing bonds and links | clarity, speed of thought, finding the flaw |
| **Flexible** | elasticity, adaptation | redirection, evasion, reshaping your astral form | adapting, slipping out of things |
| **Sticky** | binding, magnetism, attraction | holds, tethers, pulls, nets | bonds between people and things; **containment** (the collection lattices are sticky-house tech) |

## Classes → what they are in this world `[dm-proposed]` (from B1)
Every character uses a 5e class as a **chassis**, and the fiction says what it is:
- **Spirit Host** = warlock chassis. The patron is your spirit, pact magic runs on prana, and
  invocations are what your spirit teaches you. (Arenya.)
- **Night Sentinel** = monk chassis. Ki is prana, and the host's spirit fights beside them. (Kino.)
- **Meta Mage** = sorcerer chassis. The power comes from the Crown + Vesper, and metamagic is
  firmware. (Caleb.)
- **Squire-Spirit** = bard chassis. A lesser spirit that serves a host. (Abernathy.)
- **Seer** = wizard chassis (Divination). Perception that opens into the bulk. (Ava.)
- **Field Officer** = rogue chassis. A mundane human. (Malachi.)
- **Levels** come from XP and story. **Ascent** comes only from story milestones.

## Escalation by book `[dm-proposed]` from the outline; the human may correct it
| book | what the world feels like | what becomes possible |
|---|---|---|
| 1 Astral | Our world, nearly normal. The strange reads as illness, overdose, psychosis. By the end, the public has seen it and been told it's evil. | The bulk and spirit battles. Hosting. Meta mages. Physical magic near rifts. Spirits leaking through. |
| 2 Cosmic | Four years on: a divided world that knows. Spirits are feared and regulated. Then the sky opens. | Matured powers in public. Space. Cosmic-scale spirits of stars and voids. Government programs (Malachi's). |
| 3 Temporal | Exile into deep time. Myth-scale history. | Time travel (Abernathy). The Time Masters. Changing the past and paying for it. |
| 4 Ethereal | A changed present, alien allies, a cult. Whispers of angels. | Ether bodies. Subtler possession. The void as a weapon. |
| 5 Celestial | Angels are real. Temple-delving on far planets. | Embodiment by angels. Sacrifice and buffering (Abernathy's death). |
| 6 Causal | Disembodied witness across thousands of years. The end of everything. | The causal body. Singularity. Speaking with the creator. Rebirth. |

## House rules `[dm-proposed]`
- **Fast rulings at the table.** Corrections go in `ooc` afterwards and never undo what happened.
- **Psychosis shock:** an unprepared mind seeing a spirit makes a Wis save (DC 10 + spirit's size
  tier). On a failure: frightened, or a short dissociative episode. It reads as a mental-health crisis.
- **Ascent gates the bulk:** Ascent 3 or higher to fight there. Lower-Ascent characters can be carried
  in to *witness* but can't act much beyond speaking (dreams count as witnessing).
