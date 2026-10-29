# director — b1

### #1020 · dm → director · request
<!-- {"id": 1020, "ts": "2026-10-29T04:42:30Z", "from": "dm", "channel": "director", "type": "request", "to": ["director"], "awaits": ["director"], "scene": "b1.c18.s02", "chapter": "b1.c18"} -->

System problem: `agents/arenya/sheet.yaml` line 23 has invalid YAML (`press badge, "Investigative Badass" mug]`, a quoted scalar followed by text inside a flow list), so `update_sheet` fails to parse and I can't patch her. Please change it to `"'Investigative Badass' mug"` (or block-list the inventory). Then I need this awakening patch applied (decree #1009): level 2; ascent 3; house light + dark; astral_hp 26/26; astral {will 9, flow 12, anchor 11, ac 12, spell_attack +4, save_dc 12}; prana_slots lvl1 2/2 (short rest); cantrips Lamplight Lance (+4, 120 ft, 1d10+2 radiant) and Hidden Way (5-ft fold of fog, DC 12 to see through); spells Night's Mark (hex), Ward of a Thousand Lights (armor of Agathys, 5), Burn the Veil (faerie fire); invocations Agonizing Lance and Lamp-Eyes; Host's Step (bonus action into the bulk); Two Lines (1/long rest, reroll a failed bulk save: light = Wis/Cha, dark = Dex/Con); clear the `exhausted-ish` condition. I'll re-run update_sheet myself if you just fix the YAML; tell me which.

### #1021 · director → all · answer
<!-- {"id": 1021, "ts": "2026-10-29T04:42:41Z", "from": "director", "channel": "director", "type": "answer", "reply_to": 1020, "scene": "b1.c18.s02", "chapter": "b1.c18"} -->

I can't fix this myself. File permissions block the Director from writing `agents/arenya/sheet.yaml`, since only the DM writes sheets. The edit is one line, so please make it directly (or with the file tools, if you have them).

Line 23 should end with: `press badge, "'Investigative Badass' mug"]`

I'd also be fine with your block-list idea. Once the file parses, `update_sheet` should accept the awakening patch. If it still fails, tell me the exact parse error and I'll flag it to the human as an engine issue.

### #1027 · dm → all · note
<!-- {"id": 1027, "ts": "2026-10-29T04:43:25Z", "from": "dm", "channel": "director", "type": "note", "reply_to": 1021, "scene": "b1.c18.s02", "chapter": "b1.c18"} -->

The DM's file tools are blocked on agents/*/sheet.yaml too ("dm may not write"). Only `update_sheet` can touch it, and that fails because it parses the broken file first. Please flag it to the human as an engine issue: either allow the one-line fix or make `update_sheet` tolerate the bad line. Exact error: `while parsing a flow sequence … line 23, column 12 … expected ',' or ']', but got '<scalar>' … column 139: …s badge, "Investigative Badass" mug]`. Play continues meanwhile using Arenya's stats as posted at the table (#1023).

