# Zangband Save File — Character Property Mapping

## Encoding

Save files use a rolling-XOR encoding (see `zangband_save.py`). All offsets and values below refer to the **decoded** byte stream.

Multi-byte integers are stored **little-endian** (low byte first), despite being described as "big-endian" in some notes.

## Anchor

All offsets below are relative to the closing `)` of the `(saved)` string in the `died_from` field. For a living character this string is always `(saved)`. The character's name precedes it in the file, beginning around file offset `0xC800`.

Byte layout between the anchor and the first property:

| Offset | Content |
|--------|---------|
| `0x00` | `)` — anchor (last char of `"(saved)"`) |
| `0x01` | `\0` — null terminator of the `died_from` string |
| `0x02` | `\0` — old history string 1 (empty) |
| `0x03` | `\0` — old history string 2 (empty) |
| `0x04` | `\0` — old history string 3 (empty) |
| `0x05` | `\0` — old history string 4 (empty) |

## Character Properties

Sample values are from the decoded save of **Chin-su**, a level 15 High-Elf Monk.

### Identity / Race

| Offset | Size | Type | Field | Chin-su | Description |
|--------|------|------|-------|---------|-------------|
| `0x06` | 1 | u8 | `prace` | 9 | Race index (0 = Human, 1 = Half-Elf, 2 = Elf, 3 = Hobbit, 4 = Gnome, 5 = Dwarf, 6 = Half-Orc, 7 = Half-Troll, 8 = Amberite, 9 = High-Elf, …) |
| `0x07` | 1 | u8 | `pclass` | 8 | Class index (0 = Warrior, 1 = Mage, 2 = Priest, 3 = Rogue, 4 = Ranger, 5 = Paladin, 6 = Warrior-Mage, 7 = Chaos-Warrior, 8 = Monk, 9 = Mindcrafter, 10 = High-Mage, …) |
| `0x08` | 1 | u8 | `psex` | 1 | Sex (0 = Female, 1 = Male) |
| `0x09` | 1 | u8 | `spell.r[0].realm` | 3 | Primary magic realm (0 = none, 1 = Life, 2 = Sorcery, 3 = Nature, 4 = Chaos, 5 = Death, 6 = Trump, 7 = Arcane, …) |
| `0x0A` | 1 | u8 | `spell.r[1].realm` | 0 | Secondary magic realm (same values) |
| `0x0B` | 1 | — | *(unused)* | 0 | Padding / legacy field |
| `0x0C` | 1 | u8 | `hitdie` | 16 | Hit die size (e.g. 10 for d10) — base HP per level before CON bonus |
| `0x0D` | 2 | u16 | `expfact` | 240 | Experience factor (100 = normal; higher = slower level-up) |

### Physical Appearance

| Offset | Size | Type | Field | Chin-su | Description |
|--------|------|------|-------|---------|-------------|
| `0x0F` | 2 | s16 | `age` | 120 | Character age (years) |
| `0x11` | 2 | s16 | `ht` | 99 | Height (inches) |
| `0x13` | 2 | s16 | `wt` | 207 | Weight (pounds) |

### Ability Scores

Stats are stored scaled by ×10. Values 3–17 become 30–170; for 18 and above, the value is 180 + the "18/xx" sub-score (e.g. 18/50 → 230). Two sets are saved: maximum (ever-achieved) and current (possibly drained).

| Offset | Size | Type | Field | Chin-su | Description |
|--------|------|------|-------|---------|-------------|
| `0x15` | 2 | s16 | `stat[0].max` | 186 | Strength — maximum (18/06) |
| `0x17` | 2 | s16 | `stat[1].max` | 160 | Intelligence — maximum (16) |
| `0x19` | 2 | s16 | `stat[2].max` | 178 | Wisdom — maximum (17) |
| `0x1B` | 2 | s16 | `stat[3].max` | 199 | Dexterity — maximum (18/19) |
| `0x1D` | 2 | s16 | `stat[4].max` | 209 | Constitution — maximum (18/29) |
| `0x1F` | 2 | s16 | `stat[5].max` | 211 | Charisma — maximum (18/31) |
| `0x21` | 2 | s16 | `stat[0].cur` | 186 | Strength — current |
| `0x23` | 2 | s16 | `stat[1].cur` | 160 | Intelligence — current |
| `0x25` | 2 | s16 | `stat[2].cur` | 178 | Wisdom — current |
| `0x27` | 2 | s16 | `stat[3].cur` | 199 | Dexterity — current |
| `0x29` | 2 | s16 | `stat[4].cur` | 209 | Constitution — current |
| `0x2B` | 2 | s16 | `stat[5].cur` | 211 | Charisma — current |
| `0x2D` | 24 | — | *(unused)* | all 0 | Transient (display-only) stat copies — always written as zeros |

### Resources

| Offset | Size | Type | Field | Chin-su | Description |
|--------|------|------|-------|---------|-------------|
| `0x45` | 4 | u32 | `au` | 14064 | Gold pieces |
| `0x49` | 4 | u32 | `max_exp` | 4288 | Maximum experience ever accumulated |
| `0x4D` | 4 | u32 | `exp` | 4288 | Current experience |
| `0x51` | 2 | u16 | `exp_frac` | 26162 | Experience fraction (sub-point accumulator, 0–9999) |
| `0x53` | 2 | s16 | `lev` | 15 | Character level (1–50) |
| `0x55` | 2 | s16 | `place_num` | 18 | Current town/place index |

### Unused / Arena Fields

| Offset | Size | Content |
|--------|------|---------|
| `0x57` | 6 | Arena reward fields (3 × s16) — always 0 |
| `0x5D` | 2 | Arena byte fields (2 × u8) — always 0 |
| `0x5F` | 4 | Old player position py/px (2 × s16) — always 0 |
| `0x63` | 2 | Save building rewards (s16) — always 0 |

### Hit Points

| Offset | Size | Type | Field | Chin-su | Description |
|--------|------|------|-------|---------|-------------|
| `0x65` | 2 | s16 | `mhp` | 170 | Maximum HP |
| `0x67` | 2 | s16 | `chp` | 170 | Current HP |
| `0x69` | 2 | u16 | `chp_frac` | 0 | HP fraction (sub-point accumulator) |

### Spell Points (Mana)

| Offset | Size | Type | Field | Chin-su | Description |
|--------|------|------|-------|---------|-------------|
| `0x6B` | 2 | s16 | `msp` | 20 | Maximum SP (mana) |
| `0x6D` | 2 | s16 | `csp` | 20 | Current SP |
| `0x6F` | 2 | u16 | `csp_frac` | 0 | SP fraction |

### Level Tracking

| Offset | Size | Type | Field | Chin-su | Description |
|--------|------|------|-------|---------|-------------|
| `0x71` | 2 | s16 | `max_lev` | 15 | Highest character level ever reached |
| `0x73` | 2 | — | *(unused)* | 0 | Old max dungeon depth — always 0 |

### Miscellaneous

| Offset | Size | Type | Field | Chin-su | Description |
|--------|------|------|-------|---------|-------------|
| `0x75` | 8 | — | *(unused)* | all 0 | Four legacy s16 fields — always 0 |
| `0x7D` | 2 | s16 | `sc` | 57 | Social class (0–100+, affects starting equipment and interactions) |
| `0x7F` | 2 | — | *(unused)* | 0 | Legacy field — always 0 |

### Status Timers and Conditions

All timer fields count down each game turn; 0 means the effect is not active.

| Offset | Size | Type | Field | Chin-su | Description |
|--------|------|------|-------|---------|-------------|
| `0x81` | 2 | — | *(unused)* | 0 | Old "rest" counter — always 0 |
| `0x83` | 2 | s16 | `tim.blind` | 0 | Blindness timer |
| `0x85` | 2 | s16 | `tim.paralyzed` | 0 | Paralysis timer |
| `0x87` | 2 | s16 | `tim.confused` | 0 | Confusion timer |
| `0x89` | 2 | s16 | `food` | 5311 | Food level (0 = starving, higher = fuller; ~10000 = full) |
| `0x8B` | 2 | — | *(unused)* | 0 | Old food digestion rate — always 0 |
| `0x8D` | 2 | — | *(unused)* | 0 | Old protection value — always 0 |
| `0x8F` | 2 | s16 | `energy` | 100 | Current action energy (100 = ready to act) |
| `0x91` | 2 | s16 | `tim.fast` | 0 | Haste timer |
| `0x93` | 2 | s16 | `tim.slow` | 0 | Slow timer |
| `0x95` | 2 | s16 | `tim.afraid` | 0 | Fear timer |
| `0x97` | 2 | s16 | `tim.cut` | 0 | Bleeding (cut) severity timer |
| `0x99` | 2 | s16 | `tim.stun` | 0 | Stun severity timer |
| `0x9B` | 2 | s16 | `tim.poisoned` | 0 | Poison timer |
| `0x9D` | 2 | s16 | `tim.image` | 0 | Hallucination timer |
| `0x9F` | 2 | s16 | `tim.protevil` | 0 | Protection from evil timer |
| `0xA1` | 2 | s16 | `tim.invuln` | 0 | Invulnerability timer |
| `0xA3` | 2 | s16 | `tim.hero` | 0 | Heroism timer |
| `0xA5` | 2 | s16 | `tim.shero` | 0 | Super heroism (berserk) timer |
| `0xA7` | 2 | s16 | `tim.shield` | 0 | Mystic shield timer |
| `0xA9` | 2 | s16 | `tim.blessed` | 0 | Blessing timer |
| `0xAB` | 2 | s16 | `tim.invis` | 0 | See invisible timer |
| `0xAD` | 2 | s16 | `tim.word_recall` | 0 | Word of Recall countdown timer |
| `0xAF` | 2 | s16 | `see_infra` | 4 | Permanent infravision range (in feet/tiles) |
| `0xB1` | 2 | s16 | `tim.infra` | 0 | Temporary infravision timer |
| `0xB3` | 2 | s16 | `tim.oppose_fire` | 0 | Temporary fire resistance timer |
| `0xB5` | 2 | s16 | `tim.oppose_cold` | 0 | Temporary cold resistance timer |
| `0xB7` | 2 | s16 | `tim.oppose_acid` | 0 | Temporary acid resistance timer |
| `0xB9` | 2 | s16 | `tim.oppose_elec` | 0 | Temporary lightning resistance timer |
| `0xBB` | 2 | s16 | `tim.oppose_pois` | 0 | Temporary poison resistance timer |
| `0xBD` | 2 | s16 | `tim.esp` | 0 | ESP (telepathy) timer |
| `0xBF` | 2 | s16 | `tim.wraith_form` | 0 | Wraith form timer |
| `0xC1` | 2 | s16 | `tim.resist_magic` | 0 | Magic resistance timer |

### Chaos Patron and Mutations

| Offset | Size | Type | Field | Chin-su | Description |
|--------|------|------|-------|---------|-------------|
| `0xC3` | 2 | s16 | `chaos_patron` | 0 | Chaos patron index (for Chaos-Warriors and similar) |
| `0xC5` | 4 | u32 | `muta1` | 0x00000000 | Mutation bitfield 1 |
| `0xC9` | 4 | u32 | `muta2` | 0x00000000 | Mutation bitfield 2 |
| `0xCD` | 4 | u32 | `muta3` | 0x00000000 | Mutation bitfield 3 |

### Virtues

`MAX_PLAYER_VIRTUES = 8`. Virtue scores range roughly −125 to +125.

| Offset | Size | Type | Field | Chin-su | Description |
|--------|------|------|-------|---------|-------------|
| `0xD1` | 2 | s16 | `virtues[0]` | 41 | Virtue score 0 |
| `0xD3` | 2 | s16 | `virtues[1]` | 25 | Virtue score 1 |
| `0xD5` | 2 | s16 | `virtues[2]` | 35 | Virtue score 2 |
| `0xD7` | 2 | s16 | `virtues[3]` | 28 | Virtue score 3 |
| `0xD9` | 2 | s16 | `virtues[4]` | 15 | Virtue score 4 |
| `0xDB` | 2 | s16 | `virtues[5]` | −125 | Virtue score 5 |
| `0xDD` | 2 | s16 | `virtues[6]` | −12 | Virtue score 6 |
| `0xDF` | 2 | s16 | `virtues[7]` | 5 | Virtue score 7 |
| `0xE1` | 2 | s16 | `vir_types[0]` | 6 | Virtue type identifier 0 (which virtue this slot tracks) |
| `0xE3` | 2 | s16 | `vir_types[1]` | 11 | Virtue type identifier 1 |
| `0xE5` | 2 | s16 | `vir_types[2]` | 15 | Virtue type identifier 2 |
| `0xE7` | 2 | s16 | `vir_types[3]` | 14 | Virtue type identifier 3 |
| `0xE9` | 2 | s16 | `vir_types[4]` | 12 | Virtue type identifier 4 |
| `0xEB` | 2 | s16 | `vir_types[5]` | 10 | Virtue type identifier 5 |
| `0xED` | 2 | s16 | `vir_types[6]` | 1 | Virtue type identifier 6 |
| `0xEF` | 2 | s16 | `vir_types[7]` | 4 | Virtue type identifier 7 |

### State Flags

| Offset | Size | Type | Field | Chin-su | Description |
|--------|------|------|-------|---------|-------------|
| `0xF1` | 1 | u8 | `state.confusing` | 0 | Non-zero if player's touch is currently confusing monsters |
| `0xF2` | 3 | — | *(unused)* | all 0 | Three legacy bytes — always 0 |
| `0xF5` | 1 | u8 | `state.searching` | 0 | Non-zero if player is in searching mode |
| `0xF6` | 3 | — | *(unused)* | all 0 | Three legacy bytes — always 0 |

### Padding / Future Use

| Offset | Size | Content |
|--------|------|---------|
| `0xF9` | 48 | Future-use u32 fields (12 × u32) — always 0 |
| `0x129` | 12 | Ignored flags (3 × u32) — always 0 |

### Miscellaneous State

| Offset | Size | Type | Field | Chin-su | Description |
|--------|------|------|-------|---------|-------------|
| `0x135` | 4 | u32 | `seed_flavor` | 0x09879222 | RNG seed for item flavour randomisation |
| `0x139` | 2 | u16 | `state.panic_save` | 0 | Non-zero if the game was panic-saved (crash recovery) |
| `0x13B` | 2 | u16 | `state.total_winner` | 0 | Non-zero if the player has won the game |
| `0x13D` | 2 | u16 | `state.noscore` | 0 | Non-zero if the character is ineligible for the high-score list |
| `0x13F` | 1 | u8 | `state.is_dead` | 0 | Non-zero if the character is dead |
| `0x140` | 1 | u8 | `state.feeling` | 10 | Last dungeon-feeling value (1–10) |
| `0x141` | 4 | s32 | `old_turn` | 617890 | Game turn of the last dungeon-feeling update |
