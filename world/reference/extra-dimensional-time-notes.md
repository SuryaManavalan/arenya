---
source: human
imported: 2026-10-28
note: Inspiration for how the planes and spirit battles relate in time. The human's words: "let's not tie it so strongly to this but kind of a similar vibe". Treat as flavor and intuition, not hard physics.
---

EXTRA-DIMENSIONAL MOVEMENT AND TIME — NOTES
============================================

1. THE BASIC MODEL (2D: one normal axis + one extra axis)
---------------------------------------------------------
- Normal space is the line y = 0 (the x axis). Normal time t is linear:
  from x = 3 you can step to 4 or 2.
- Space turns out to have an extra dimension y. Movement off the x axis
  does not consume normal time.
- Example: an actor at x = 3 leaves the axis, follows a curve through y,
  and rejoins the axis at x = 9. In normal time, x(t) jumps from 3 to 9
  instantly: teleportation.

Formalization
- Traveler's path: gamma(s) = (x(s), y(s)), where s is the traveler's own
  clock (arc length).
- Normal time accumulates through a weight on position:

      dt = w(y) * ds,   with w(0) = 1 and w -> 0 off the axis

- What normal space observes: x as a function of t, built from the pair
  (t(s), x(s)).
- Your exact rule: w(y) = 1 if y = 0, else 0. During the excursion ds
  keeps ticking but dt = 0, so t freezes while x slides 3 -> 9. On the
  x(t) graph this is a vertical jump.

Consequences
- Apparent speed in normal space = (dx/ds) / w(y). As w -> 0 off-axis,
  observed speed blows up. Teleportation is the limit of "infinitely
  fast": a smooth small w gives superluminal travel, w = 0 gives a jump.
- The traveler still ages. Their own clock s runs through the whole arc.
  This is the reverse of relativistic time dilation: the world pauses
  while you move. A longer detour costs you time, never the world.
- Everything becomes a shortcut. 1D distance no longer measures time to
  reach a point; the "normal-time distance" collapses to the on-axis
  part of the cheapest path (zero for any jump).
- Causality is safe for now because t is absolute (one global clock).
  With relativity added, instantaneous jumps could be chained into loops
  into your own past.
- Real-physics cousin: braneworld models, where our universe is a
  surface in a higher-dimensional bulk and signals cutting through the
  bulk can appear to arrive faster than light along the brane.

(Interactive visual shown in chat: slider for off-axis time cost; the
x(t) curve goes from a slow stretch to a vertical jump as cost -> 0.)


2. MULTIPLE ACTORS IN THE EXTRA DIMENSION ("THE BULK")
------------------------------------------------------
Added rule: for all observers and actors in normal space, extra-spatial
movement by ANY actor takes 0 normal time.

Question: how do two bulk travelers compute motion relative to each
other, and in what order is bulk motion computed? Does it depend on
their curves?

Answer: introduce a second clock.

Two clocks, ordered lexicographically
- The bulk has its own time tau that only runs while t is frozen.
- A moment is a pair (t, tau), ordered:

      (t1, tau1) < (t2, tau2)  iff  t1 < t2,  or  t1 = t2 and tau1 < tau2

- Every normal instant has a whole hidden timeline stacked on it.
- In computer science this is "superdense time," used to simulate
  systems with instantaneous events (hybrid systems).

The step loop
  1. Normal step: advance t by dt; every on-axis actor moves in parallel.
  2. If any actor left the axis: freeze t, set tau = 0.
  3. Bulk step: advance tau by d_tau; every off-axis actor moves in
     parallel along its curve gamma_i(tau). Check interactions.
  4. Actors that reach y = 0 park and wait.
  5. When nobody is off-axis, resume step 1. Normal observers see all
     returns happen at the same t.

Does order depend on the curves?
- Not with a shared tau. Bulk travelers are parallel in tau just as
  normal actors are parallel in t. Relative position is simply:

      Delta(tau) = gamma_A(tau) - gamma_B(tau)

- The curves decide WHERE actors are relative to each other (meet,
  collide, pass), but not the computation order.
- The alternative, each actor using its own arc length as its clock,
  breaks: "A at point p" and "B at point q" have no agreed simultaneity,
  so whether they meet depends on an arbitrary rule. This is essentially
  relativity's simultaneity problem. Processing excursions one at a time
  (sequentially) is order-dependent for the same reason.

Consequences
- Only same-instant departures share the bulk. While anyone is off-axis,
  t is frozen, so no one can step off at a later t. Two bulk travelers
  can only meet if they left at the same normal instant (unless you
  allow entering mid-freeze, which is a design choice).
- Early returners are frozen too. If A returns at tau2 and B at tau4,
  A sits parked until B lands.
- A traveler who never returns freezes the universe. t can't advance.
  Needs a rule: excursions must terminate, or a cap on tau.
- It nests. If the bulk has its own extra dimension that costs no tau,
  you get (t, tau, sigma, ...), each level frozen while the deeper one
  runs.

(Diagram shown in chat: normal-time steps along a horizontal axis, with
a vertical column of tau steps stacked at one frozen instant t2.)


3. OPEN THREADS
---------------
- Scale the model up to 3+1 dimensions.
- Try a specific w(y) and derive the travel-time formula.
- Build a stepper simulation with two actors sent on curves, showing
  both clocks.
