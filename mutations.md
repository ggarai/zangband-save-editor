# Zangband Mutation Bitmasks

Mutations are stored as three 32-bit little-endian values (u32b) in the save file:

| Field | Offset from anchor | Description |
|-------|-------------------|-------------|
| muta1 | 0x12E | Activatable mutations (used deliberately) |
| muta2 | 0x132 | Random-trigger mutations (fire involuntarily) |
| muta3 | 0x136 | Passive mutations (permanent stat/body modifiers) |

Each bit represents one mutation. OR in a bit to add a mutation; AND with the complement to remove it.

---

## muta1 — Activatable Mutations

| Bit | Value | Mutation |
|-----|-------|----------|
| 0 | 0x00000001 | Spit Acid |
| 1 | 0x00000002 | Breathe Fire |
| 2 | 0x00000004 | Hypnotic Gaze |
| 3 | 0x00000008 | Telekinesis |
| 4 | 0x00000010 | Teleport (voluntary) |
| 5 | 0x00000020 | Mind Blast |
| 6 | 0x00000040 | Radiation |
| 7 | 0x00000080 | Vampiric Drain |
| 8 | 0x00000100 | Smell Metal |
| 9 | 0x00000200 | Smell Monsters |
| 10 | 0x00000400 | Blink |
| 11 | 0x00000800 | Eat Rock |
| 12 | 0x00001000 | Swap Position |
| 13 | 0x00002000 | Shriek |
| 14 | 0x00004000 | Illuminate |
| 15 | 0x00008000 | Detect Curses |
| 16 | 0x00010000 | Berserk |
| 17 | 0x00020000 | Polymorph |
| 18 | 0x00040000 | Midas Touch |
| 19 | 0x00080000 | Grow Mold |
| 20 | 0x00100000 | Resist Elements |
| 21 | 0x00200000 | Earthquake |
| 22 | 0x00400000 | Eat Magic |
| 23 | 0x00800000 | Weigh Magic |
| 24 | 0x01000000 | Sterilize |
| 25 | 0x02000000 | Panic Hit |
| 26 | 0x04000000 | Dazzle |
| 27 | 0x08000000 | Laser Eye |
| 28 | 0x10000000 | Word of Recall |
| 29 | 0x20000000 | Banish Evil |
| 30 | 0x40000000 | Cold Touch |
| 31 | 0x80000000 | Launcher |

---

## muta2 — Random-Trigger Mutations

| Bit | Value | Mutation |
|-----|-------|----------|
| 0 | 0x00000001 | Berserk Rage |
| 1 | 0x00000002 | Cowardice |
| 2 | 0x00000004 | Random Teleport |
| 3 | 0x00000008 | Alcohol |
| 4 | 0x00000010 | Hallucinations |
| 5 | 0x00000020 | Flatulence |
| 6 | 0x00000040 | Scorpion Tail |
| 7 | 0x00000080 | Horns |
| 8 | 0x00000100 | Beak |
| 9 | 0x00000200 | Attract Demons |
| 10 | 0x00000400 | Produce Mana |
| 11 | 0x00000800 | Speed Flux |
| 12 | 0x00001000 | Banish All |
| 13 | 0x00002000 | Eat Light |
| 14 | 0x00004000 | Trunk |
| 15 | 0x00008000 | Attract Animals |
| 16 | 0x00010000 | Tentacles |
| 17 | 0x00020000 | Raw Chaos |
| 18 | 0x00040000 | Normality |
| 19 | 0x00080000 | Wraith Form |
| 20 | 0x00100000 | Polymorph Wounds |
| 21 | 0x00200000 | Wasting |
| 22 | 0x00400000 | Attract Dragons |
| 23 | 0x00800000 | Weird Mind |
| 24 | 0x01000000 | Nausea |
| 25 | 0x02000000 | Chaos Gift (grants TR_PATRON — patron rewards on level-up) |
| 26 | 0x04000000 | Walk Through Walls |
| 27 | 0x08000000 | Warning |
| 28 | 0x10000000 | Invulnerability |
| 29 | 0x20000000 | SP to HP |
| 30 | 0x40000000 | HP to SP |
| 31 | 0x80000000 | Disarm |

---

## muta3 — Passive Mutations

| Bit | Value | Mutation |
|-----|-------|----------|
| 0 | 0x00000001 | Hyper Strength |
| 1 | 0x00000002 | Puny |
| 2 | 0x00000004 | Hyper Intelligence |
| 3 | 0x00000008 | Moronic |
| 4 | 0x00000010 | Resilient |
| 5 | 0x00000020 | Extra Fat |
| 6 | 0x00000040 | Albino |
| 7 | 0x00000080 | Flesh Rot |
| 8 | 0x00000100 | Silly Voice |
| 9 | 0x00000200 | Blank Face |
| 10 | 0x00000400 | Illusory Normal Appearance |
| 11 | 0x00000800 | Extra Eyes |
| 12 | 0x00001000 | Magic Resistance |
| 13 | 0x00002000 | Extra Noise |
| 14 | 0x00004000 | Infravision |
| 15 | 0x00008000 | Extra Legs |
| 16 | 0x00010000 | Short Legs |
| 17 | 0x00020000 | Electric Touch |
| 18 | 0x00040000 | Fiery Body |
| 19 | 0x00080000 | Wart Skin |
| 20 | 0x00100000 | Scales |
| 21 | 0x00200000 | Iron Skin |
| 22 | 0x00400000 | Wings |
| 23 | 0x00800000 | Fearless |
| 24 | 0x01000000 | Regeneration |
| 25 | 0x02000000 | ESP |
| 26 | 0x04000000 | Limber |
| 27 | 0x08000000 | Arthritis |
| 28 | 0x10000000 | Bad Luck |
| 29 | 0x20000000 | Elemental Vulnerability |
| 30 | 0x40000000 | Constant Motion |
| 31 | 0x80000000 | Good Luck |
