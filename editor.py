#!/usr/bin/env python3
"""
Zangband Save Game Editor
Run with: python3 editor.py
"""

import json
import os
import struct
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path

try:
    from flask import Flask, request, jsonify, render_template_string
except ImportError:
    import platform
    pip_args = [sys.executable, "-m", "pip", "install", "flask", "-q"]
    if platform.system() != "Windows":
        pip_args.append("--break-system-packages")
    subprocess.check_call(pip_args)
    from flask import Flask, request, jsonify, render_template_string

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

HERE = Path(__file__).parent
CODEC = HERE / "zangband_save.py"

# ---------------------------------------------------------------------------
# Data tables (from tables.c)
# ---------------------------------------------------------------------------

RACES = [
    "Human", "Half-Elf", "Elf", "Hobbit", "Gnome", "Dwarf",
    "Half-Orc", "Half-Troll", "Amberite", "High-Elf", "Barbarian",
    "Half-Ogre", "Half-Giant", "Half-Titan", "Cyclops", "Yeek",
    "Klackon", "Kobold", "Nibelung", "Dark-Elf", "Draconian",
    "Mindflayer", "Imp", "Golem", "Skeleton", "Zombie",
    "Vampire", "Spectre", "Sprite", "Beastman", "Ghoul",
]

CLASSES = [
    "Warrior", "Mage", "Priest", "Rogue", "Ranger", "Paladin",
    "Warrior-Mage", "Chaos-Warrior", "Monk", "Mindcrafter", "High-Mage",
]

SEXES = ["Female", "Male"]

# Index 0 = "no magic", 1–7 = named realms, 8 = unknown
REALMS = ["no magic", "Life", "Sorcery", "Nature", "Chaos", "Death", "Trump", "Arcane"]

STAT_NAMES = ["Strength", "Intelligence", "Wisdom", "Dexterity", "Constitution", "Charisma"]

# ---------------------------------------------------------------------------
# Stat encoding helpers
# ---------------------------------------------------------------------------

def raw_to_display(raw: int) -> str:
    """Convert stored stat value to Angband display notation."""
    if raw < 180:
        return str(raw // 10)
    return f"18/{raw - 180:02d}"

def display_to_raw(s: str) -> int:
    """Convert display notation back to stored value. Accepts '16' or '18/50'."""
    s = s.strip()
    if "/" in s:
        parts = s.split("/")
        return 180 + int(parts[1])
    n = int(s)
    return n * 10  # works for 1–17; '18' → 180 which also happens to equal 180+0

# ---------------------------------------------------------------------------
# Save file parsing
# ---------------------------------------------------------------------------

def find_anchor(data: bytes) -> int:
    """Return offset of the closing ')' in '(saved)'."""
    pos = data.find(b"(saved)")
    if pos == -1:
        raise ValueError("'(saved)' not found — is this a decoded living-character save?")
    return pos + 6  # offset of ')'

def read_fields(data: bytes) -> dict:
    """Extract all character fields from decoded save data."""
    a = find_anchor(data)

    def rb(off): return data[a + off]
    def rs16(off): return struct.unpack_from("<h", data, a + off)[0]
    def ru16(off): return struct.unpack_from("<H", data, a + off)[0]
    def ru32(off): return struct.unpack_from("<I", data, a + off)[0]
    def rs32(off): return struct.unpack_from("<i", data, a + off)[0]

    # Player name: null-terminated string just before "(saved)"
    saved_pos = a - 6  # start of "(saved)"
    name_end = saved_pos - 1  # the \0 before "(saved)"
    name_start = name_end
    while name_start > 0 and data[name_start - 1] != 0:
        name_start -= 1
    player_name = data[name_start:name_end].decode("latin-1", errors="replace")

    fields = {
        "player_name": player_name,
        # Identity
        "prace":   rb(0x06),
        "pclass":  rb(0x07),
        "psex":    rb(0x08),
        "realm1":  rb(0x09),
        "realm2":  rb(0x0A),
        "hitdie":  rb(0x0C),
        "expfact": ru16(0x0D),
        # Appearance
        "age": rs16(0x0F),
        "ht":  rs16(0x11),
        "wt":  rs16(0x13),
        # Stats (max then cur)
        "stat_max": [rs16(0x15 + i * 2) for i in range(6)],
        "stat_cur": [rs16(0x21 + i * 2) for i in range(6)],
        # Resources
        "au":       ru32(0x45),
        "max_exp":  ru32(0x49),
        "exp":      ru32(0x4D),
        "exp_frac": ru16(0x51),
        "lev":      rs16(0x53),
        "place_num": rs16(0x55),
        # HP
        "mhp":      rs16(0x65),
        "chp":      rs16(0x67),
        "chp_frac": ru16(0x69),
        # SP
        "msp":      rs16(0x6B),
        "csp":      rs16(0x6D),
        "csp_frac": ru16(0x6F),
        # Levels
        "max_lev": rs16(0x71),
        # Misc
        "sc": rs16(0x7D),
        # Status
        "blind":        rs16(0x83),
        "paralyzed":    rs16(0x85),
        "confused":     rs16(0x87),
        "food":         rs16(0x89),
        "energy":       rs16(0x8F),
        "fast":         rs16(0x91),
        "slow":         rs16(0x93),
        "afraid":       rs16(0x95),
        "cut":          rs16(0x97),
        "stun":         rs16(0x99),
        "poisoned":     rs16(0x9B),
        "image":        rs16(0x9D),
        "protevil":     rs16(0x9F),
        "invuln":       rs16(0xA1),
        "hero":         rs16(0xA3),
        "shero":        rs16(0xA5),
        "shield":       rs16(0xA7),
        "blessed":      rs16(0xA9),
        "invis":        rs16(0xAB),
        "word_recall":  rs16(0xAD),
        "see_infra":    rs16(0xAF),
        "infra":        rs16(0xB1),
        "oppose_fire":  rs16(0xB3),
        "oppose_cold":  rs16(0xB5),
        "oppose_acid":  rs16(0xB7),
        "oppose_elec":  rs16(0xB9),
        "oppose_pois":  rs16(0xBB),
        "esp":          rs16(0xBD),
        "wraith_form":  rs16(0xBF),
        "resist_magic": rs16(0xC1),
        # Chaos / mutations
        "chaos_patron": rs16(0xC3),
        "muta1": ru32(0xC5),
        "muta2": ru32(0xC9),
        "muta3": ru32(0xCD),
        # Virtues
        "virtues":   [rs16(0xD1 + i * 2) for i in range(8)],
        "vir_types": [rs16(0xE1 + i * 2) for i in range(8)],
        # State
        "confusing": rb(0xF1),
        "searching":  rb(0xF5),
        # Misc state
        "seed_flavor":   ru32(0x135),
        "panic_save":    ru16(0x139),
        "total_winner":  ru16(0x13B),
        "noscore":       ru16(0x13D),
        "is_dead":       rb(0x13F),
        "feeling":       rb(0x140),
        "old_turn":      rs32(0x141),
    }
    return fields


def write_fields(data: bytes, fields: dict) -> bytes:
    """Write character fields back into decoded save data, return modified bytes."""
    a = find_anchor(data)
    buf = bytearray(data)

    def wb(off, v):  buf[a + off] = v & 0xFF
    def ws16(off, v):  struct.pack_into("<h", buf, a + off, int(v))
    def wu16(off, v):  struct.pack_into("<H", buf, a + off, int(v))
    def wu32(off, v):  struct.pack_into("<I", buf, a + off, int(v))
    def ws32(off, v):  struct.pack_into("<i", buf, a + off, int(v))

    wb(0x06, fields["prace"])
    wb(0x07, fields["pclass"])
    wb(0x08, fields["psex"])
    wb(0x09, fields["realm1"])
    wb(0x0A, fields["realm2"])
    wb(0x0C, fields["hitdie"])
    wu16(0x0D, fields["expfact"])

    ws16(0x0F, fields["age"])
    ws16(0x11, fields["ht"])
    ws16(0x13, fields["wt"])

    for i, v in enumerate(fields["stat_max"]): ws16(0x15 + i * 2, v)
    for i, v in enumerate(fields["stat_cur"]): ws16(0x21 + i * 2, v)

    wu32(0x45, fields["au"])
    wu32(0x49, fields["max_exp"])
    wu32(0x4D, fields["exp"])
    wu16(0x51, fields["exp_frac"])
    ws16(0x53, fields["lev"])
    ws16(0x55, fields["place_num"])

    ws16(0x65, fields["mhp"])
    ws16(0x67, fields["chp"])
    wu16(0x69, fields["chp_frac"])
    ws16(0x6B, fields["msp"])
    ws16(0x6D, fields["csp"])
    wu16(0x6F, fields["csp_frac"])

    ws16(0x71, fields["max_lev"])
    ws16(0x7D, fields["sc"])

    ws16(0x83, fields["blind"])
    ws16(0x85, fields["paralyzed"])
    ws16(0x87, fields["confused"])
    ws16(0x89, fields["food"])
    ws16(0x8F, fields["energy"])
    ws16(0x91, fields["fast"])
    ws16(0x93, fields["slow"])
    ws16(0x95, fields["afraid"])
    ws16(0x97, fields["cut"])
    ws16(0x99, fields["stun"])
    ws16(0x9B, fields["poisoned"])
    ws16(0x9D, fields["image"])
    ws16(0x9F, fields["protevil"])
    ws16(0xA1, fields["invuln"])
    ws16(0xA3, fields["hero"])
    ws16(0xA5, fields["shero"])
    ws16(0xA7, fields["shield"])
    ws16(0xA9, fields["blessed"])
    ws16(0xAB, fields["invis"])
    ws16(0xAD, fields["word_recall"])
    ws16(0xAF, fields["see_infra"])
    ws16(0xB1, fields["infra"])
    ws16(0xB3, fields["oppose_fire"])
    ws16(0xB5, fields["oppose_cold"])
    ws16(0xB7, fields["oppose_acid"])
    ws16(0xB9, fields["oppose_elec"])
    ws16(0xBB, fields["oppose_pois"])
    ws16(0xBD, fields["esp"])
    ws16(0xBF, fields["wraith_form"])
    ws16(0xC1, fields["resist_magic"])

    ws16(0xC3, fields["chaos_patron"])
    wu32(0xC5, fields["muta1"])
    wu32(0xC9, fields["muta2"])
    wu32(0xCD, fields["muta3"])

    for i, v in enumerate(fields["virtues"]):   ws16(0xD1 + i * 2, v)
    for i, v in enumerate(fields["vir_types"]): ws16(0xE1 + i * 2, v)

    wb(0xF1, fields["confusing"])
    wb(0xF5, fields["searching"])

    wu32(0x135, fields["seed_flavor"])
    wu16(0x139, fields["panic_save"])
    wu16(0x13B, fields["total_winner"])
    wu16(0x13D, fields["noscore"])
    wb(0x13F, fields["is_dead"])
    wb(0x140, fields["feeling"])
    ws32(0x141, fields["old_turn"])

    return bytes(buf)

# ---------------------------------------------------------------------------
# Equipment I/O  (save file version 52 format)
# ---------------------------------------------------------------------------

EQUIP_SLOT_NAMES = [
    "WIELD", "BOW", "LEFT", "RIGHT", "NECK", "LITE",
    "BODY", "OUTER", "ARM", "HEAD", "HANDS", "FEET",
]

# Brief tval → item category label (incomplete but covers all equipment slots)
TVAL_LABELS = {
    19: "Sling/Bow", 20: "Bow", 21: "Crossbow",
    23: "Sword", 24: "Polearm", 25: "Hafted", 26: "Staff",
    30: "Boots", 31: "Gloves", 33: "Helm", 34: "Shield",
    35: "Cloak", 36: "Soft Armor", 37: "Hard Armor", 38: "Dragon Armor",
    39: "Lite", 40: "Amulet", 45: "Ring",
}


def _rd_string(data: bytes, pos: int):
    """Read null-terminated string; return (string, new_pos)."""
    end = data.index(0, pos)
    return data[pos:end].decode("latin-1", "replace"), end + 1


def _find_equip_start(data: bytes) -> int:
    """Return byte offset of the first slot-index u16b in the equipment block."""
    anchor = data.find(b"(saved)")
    if anchor == -1:
        raise ValueError("'(saved)' not found")
    anchor += 6                                      # closing ')'
    after_extra    = anchor + 0x14C
    py_max_level   = struct.unpack_from("<H", data, after_extra)[0]
    after_hp       = after_extra + 2 + py_max_level * 2
    # 6 u32b spell-learned/worked/forgotten + 64 spell-order bytes
    return after_hp + 6 * 4 + 64


def read_equipment(data: bytes) -> list[dict]:
    """
    Parse the equipment block and return a list of item dicts.

    Each dict contains all item fields plus:
      '_slot'  – equipment slot index (0-11)
      '_start' – byte offset of the first byte of the item record (after the slot u16b)
      '_size'  – total byte length of the item record
    """
    pos = _find_equip_start(data)
    items = []

    while True:
        slot_idx = struct.unpack_from("<H", data, pos)[0]
        if slot_idx == 0xFFFF:
            break
        if slot_idx > 11:
            raise ValueError(f"Unexpected slot index {slot_idx} at 0x{pos:x}")
        pos += 2
        item_start = pos

        # ---- fixed fields (47 bytes) ----------------------------------------
        k_idx    = struct.unpack_from("<h", data, pos)[0]; pos += 2
        iy       = struct.unpack_from("<h", data, pos)[0]; pos += 2
        ix       = struct.unpack_from("<h", data, pos)[0]; pos += 2
        tval     = data[pos]; pos += 1
        sval     = data[pos]; pos += 1
        pval     = struct.unpack_from("<h", data, pos)[0]; pos += 2
        discount = data[pos]; pos += 1
        number   = data[pos]; pos += 1
        weight   = struct.unpack_from("<h", data, pos)[0]; pos += 2
        timeout  = struct.unpack_from("<h", data, pos)[0]; pos += 2
        to_h     = struct.unpack_from("<h", data, pos)[0]; pos += 2
        to_d     = struct.unpack_from("<h", data, pos)[0]; pos += 2
        to_a     = struct.unpack_from("<h", data, pos)[0]; pos += 2
        ac       = struct.unpack_from("<h", data, pos)[0]; pos += 2
        dd       = data[pos]; pos += 1
        ds       = data[pos]; pos += 1
        info     = data[pos]; pos += 1
        flags    = [struct.unpack_from("<I", data, pos + i*4)[0] for i in range(4)]; pos += 16
        next_o   = struct.unpack_from("<h", data, pos)[0]; pos += 2
        alloc    = data[pos]; pos += 1
        feeling  = data[pos]; pos += 1

        # ---- variable-length strings -----------------------------------------
        insc, pos = _rd_string(data, pos)
        new_byte  = data[pos]; pos += 1          # v52 extra byte
        xname, pos = _rd_string(data, pos)

        # ---- triggers: index + null-terminated string, terminated by 0xFF ----
        triggers = []
        tidx = data[pos]; pos += 1
        while tidx != 255:
            s, pos = _rd_string(data, pos)
            triggers.append((tidx, s))
            tidx = data[pos]; pos += 1

        # ---- python object (always length 0) ---------------------------------
        py_len = struct.unpack_from("<i", data, pos)[0]; pos += 4 + max(0, py_len)

        # ---- tail fields -----------------------------------------------------
        cost      = struct.unpack_from("<i", data, pos)[0]; pos += 4
        a_idx     = data[pos]; pos += 1
        kn_flags  = [struct.unpack_from("<I", data, pos + i*4)[0] for i in range(4)]; pos += 16

        items.append({
            "_slot":    slot_idx,
            "_start":   item_start,
            "_size":    pos - item_start,
            "k_idx":    k_idx, "tval": tval, "sval": sval,
            "iy": iy, "ix": ix,
            "pval":     pval,  "discount": discount, "number": number,
            "weight":   weight, "timeout": timeout,
            "to_h":     to_h, "to_d": to_d, "to_a": to_a, "ac": ac,
            "dd": dd, "ds": ds, "info": info,
            "flags":    flags, "next_o": next_o, "alloc": alloc, "feeling": feeling,
            "insc":     insc, "new_byte": new_byte, "xname": xname,
            "triggers": triggers, "cost": cost, "a_idx": a_idx,
            "kn_flags": kn_flags,
        })

    return items


def write_equipment(data: bytes, edits: list[dict]) -> bytes:
    """
    Apply in-place edits to equipment items.

    Each edit dict must contain '_start' (the item's byte offset) plus any
    combination of: to_h, to_d, to_a, pval, ac, timeout, number.
    Only fixed-size fields at predictable offsets are touched; the
    variable-length trigger/script bytes are left untouched.
    """
    buf = bytearray(data)

    # Fixed-field offsets within each item record (relative to item_start)
    FIELD_OFFSETS = {
        "pval":    (8,  "<h"),
        "timeout": (14, "<h"),
        "to_h":    (16, "<h"),
        "to_d":    (18, "<h"),
        "to_a":    (20, "<h"),
        "ac":      (22, "<h"),
        "number":  (11, "B"),
    }

    for edit in edits:
        base = edit["_start"]
        for field, (off, fmt) in FIELD_OFFSETS.items():
            if field in edit:
                struct.pack_into(fmt, buf, base + off, int(edit[field]))

    return bytes(buf)


# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------

app = Flask(__name__)

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Zangband Save Editor</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: system-ui, sans-serif; font-size: 14px; background: #1a1a2e; color: #e0e0e0; }
  h1 { padding: 16px 20px; background: #16213e; border-bottom: 2px solid #0f3460; color: #e94560; font-size: 18px; letter-spacing: 1px; }
  h2 { font-size: 12px; text-transform: uppercase; letter-spacing: 1px; color: #e94560; margin: 0 0 10px; }
  .toolbar { display: flex; align-items: center; gap: 8px; padding: 12px 20px; background: #16213e; border-bottom: 1px solid #0f3460; flex-wrap: wrap; }
  .toolbar input[type=text] { flex: 1; min-width: 200px; padding: 6px 10px; background: #0f3460; border: 1px solid #e94560; color: #e0e0e0; border-radius: 4px; }
  button { padding: 6px 14px; border: none; border-radius: 4px; cursor: pointer; font-size: 13px; font-weight: 600; }
  .btn-primary { background: #e94560; color: #fff; }
  .btn-secondary { background: #0f3460; color: #e0e0e0; border: 1px solid #e94560; }
  .btn-primary:hover { background: #c73652; }
  .btn-secondary:hover { background: #1a4a80; }
  .content { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 16px; padding: 16px 20px; }
  .card { background: #16213e; border: 1px solid #0f3460; border-radius: 6px; padding: 14px; }
  .field { display: grid; grid-template-columns: 1fr 1fr; align-items: center; margin-bottom: 8px; gap: 6px; }
  .field label { color: #a0a0c0; font-size: 12px; }
  .field input, .field select { padding: 4px 8px; background: #0f3460; border: 1px solid #2a4a80; color: #e0e0e0; border-radius: 3px; width: 100%; font-size: 13px; }
  .field input:focus, .field select:focus { outline: none; border-color: #e94560; }
  .field.readonly input { color: #808090; }
  .stat-grid { display: grid; grid-template-columns: 2fr 1fr 1fr; gap: 4px; align-items: center; margin-bottom: 4px; }
  .stat-grid .lbl { color: #a0a0c0; font-size: 12px; }
  .stat-grid input { padding: 4px 8px; background: #0f3460; border: 1px solid #2a4a80; color: #e0e0e0; border-radius: 3px; font-size: 13px; width: 100%; }
  .stat-grid input:focus { outline: none; border-color: #e94560; }
  .col-hdr { font-size: 11px; color: #606080; text-align: center; }
  #status { padding: 6px 20px; font-size: 12px; background: #0f1e3d; border-top: 1px solid #0f3460; min-height: 28px; color: #80c080; }
  #status.error { color: #e94560; }
  .inline-buttons { display: flex; gap: 8px; }
  #equip-table { width:100%; border-collapse:collapse; font-size:13px; }
  #equip-table th { text-align:left; padding:4px 8px; border-bottom:1px solid #0f3460; color:#a0a0c0; font-size:11px; text-transform:uppercase; letter-spacing:.5px; }
  #equip-table td { padding:4px 6px; border-bottom:1px solid #0f2040; }
  #equip-table td.slot-name { color:#e94560; font-weight:600; white-space:nowrap; }
  #equip-table td.ego-name  { color:#c0d0f0; }
  #equip-table input.stat   { width:52px; padding:2px 4px; background:#0f3460; border:1px solid #2a4a80; color:#e0e0e0; border-radius:3px; font-size:13px; text-align:right; }
  #equip-table input.stat:focus { outline:none; border-color:#e94560; }
</style>
</head>
<body>
<h1>⚔ Zangband Save Editor</h1>

<div class="toolbar">
  <input type="text" id="filepath" placeholder="Path to save file…">
  <button class="btn-secondary" onclick="browse()">Browse…</button>
  <button class="btn-secondary" onclick="decode()">Decode</button>
  <button class="btn-secondary" onclick="encode()">Encode</button>
  <button class="btn-primary"   onclick="load()">Load</button>
  <button class="btn-primary"   onclick="save()">Save</button>
</div>

<div class="content">

  <!-- Identity -->
  <div class="card">
    <h2>Identity</h2>
    <div class="field readonly"><label>Name</label><input id="player_name" readonly></div>
    <div class="field"><label>Race</label>
      <select id="prace">{{ race_options }}</select></div>
    <div class="field"><label>Class</label>
      <select id="pclass">{{ class_options }}</select></div>
    <div class="field"><label>Sex</label>
      <select id="psex">{{ sex_options }}</select></div>
    <div class="field"><label>Primary Realm</label>
      <select id="realm1">{{ realm_options }}</select></div>
    <div class="field"><label>Secondary Realm</label>
      <select id="realm2">{{ realm_options }}</select></div>
    <div class="field"><label>Hit Die</label><input id="hitdie" type="number"></div>
    <div class="field"><label>Exp Factor</label><input id="expfact" type="number"></div>
  </div>

  <!-- Appearance -->
  <div class="card">
    <h2>Appearance</h2>
    <div class="field"><label>Age</label><input id="age" type="number"></div>
    <div class="field"><label>Height (in)</label><input id="ht" type="number"></div>
    <div class="field"><label>Weight (lb)</label><input id="wt" type="number"></div>
    <div class="field"><label>Social Class</label><input id="sc" type="number"></div>
  </div>

  <!-- Ability Scores -->
  <div class="card">
    <h2>Ability Scores</h2>
    <div class="stat-grid">
      <div></div><div class="col-hdr">Max</div><div class="col-hdr">Current</div>
    </div>
    {% for i, name in stat_names %}
    <div class="stat-grid">
      <div class="lbl">{{ name }}</div>
      <input id="stat_max_{{ i }}" placeholder="e.g. 18/50">
      <input id="stat_cur_{{ i }}" placeholder="e.g. 18/50">
    </div>
    {% endfor %}
    <p style="font-size:11px;color:#606080;margin-top:6px;">Use 18/xx notation for 18+ stats (e.g. 18/06, 18/100)</p>
  </div>

  <!-- Resources -->
  <div class="card">
    <h2>Resources &amp; Level</h2>
    <div class="field"><label>Character Level</label><input id="lev" type="number"></div>
    <div class="field"><label>Max Level Reached</label><input id="max_lev" type="number"></div>
    <div class="field"><label>Gold</label><input id="au" type="number"></div>
    <div class="field"><label>Experience</label><input id="exp" type="number"></div>
    <div class="field"><label>Max Experience</label><input id="max_exp" type="number"></div>
    <div class="field"><label>Exp Fraction</label><input id="exp_frac" type="number"></div>
    <div class="field readonly"><label>Place Index</label><input id="place_num" type="number"></div>
  </div>

  <!-- HP & SP -->
  <div class="card">
    <h2>Hit Points &amp; Mana</h2>
    <div class="field"><label>Max HP</label><input id="mhp" type="number"></div>
    <div class="field"><label>Current HP</label><input id="chp" type="number"></div>
    <div class="field"><label>HP Fraction</label><input id="chp_frac" type="number"></div>
    <div class="field readonly"><label>Max SP (Mana)</label><input id="msp" type="number" readonly></div>
    <div class="field readonly"><label>Current SP</label><input id="csp" type="number" readonly></div>
    <div class="field readonly"><label>SP Fraction</label><input id="csp_frac" type="number" readonly></div>
    <p style="font-size:11px;color:#606080;margin-top:6px;">SP is recalculated by the game on startup and cannot be edited.</p>
  </div>

  <!-- Conditions -->
  <div class="card">
    <h2>Conditions &amp; Timers</h2>
    <div class="field"><label>Food Level</label><input id="food" type="number"></div>
    <div class="field"><label>Energy</label><input id="energy" type="number"></div>
    <div class="field"><label>Infravision (perm)</label><input id="see_infra" type="number"></div>
    <div class="field"><label>Blindness</label><input id="blind" type="number"></div>
    <div class="field"><label>Paralysis</label><input id="paralyzed" type="number"></div>
    <div class="field"><label>Confusion</label><input id="confused" type="number"></div>
    <div class="field"><label>Fear</label><input id="afraid" type="number"></div>
    <div class="field"><label>Bleeding (Cut)</label><input id="cut" type="number"></div>
    <div class="field"><label>Stun</label><input id="stun" type="number"></div>
    <div class="field"><label>Poison</label><input id="poisoned" type="number"></div>
    <div class="field"><label>Hallucination</label><input id="image" type="number"></div>
  </div>

  <!-- Temporary Effects -->
  <div class="card">
    <h2>Temporary Effects</h2>
    <div class="field"><label>Haste</label><input id="fast" type="number"></div>
    <div class="field"><label>Slow</label><input id="slow" type="number"></div>
    <div class="field"><label>Heroism</label><input id="hero" type="number"></div>
    <div class="field"><label>Super Heroism</label><input id="shero" type="number"></div>
    <div class="field"><label>Shield</label><input id="shield" type="number"></div>
    <div class="field"><label>Blessed</label><input id="blessed" type="number"></div>
    <div class="field"><label>See Invisible</label><input id="invis" type="number"></div>
    <div class="field"><label>Infravision</label><input id="infra" type="number"></div>
    <div class="field"><label>Prot. from Evil</label><input id="protevil" type="number"></div>
    <div class="field"><label>Invulnerability</label><input id="invuln" type="number"></div>
    <div class="field"><label>ESP</label><input id="esp" type="number"></div>
    <div class="field"><label>Wraith Form</label><input id="wraith_form" type="number"></div>
    <div class="field"><label>Resist Magic</label><input id="resist_magic" type="number"></div>
    <div class="field"><label>Word of Recall</label><input id="word_recall" type="number"></div>
    <div class="field"><label>Resist Fire</label><input id="oppose_fire" type="number"></div>
    <div class="field"><label>Resist Cold</label><input id="oppose_cold" type="number"></div>
    <div class="field"><label>Resist Acid</label><input id="oppose_acid" type="number"></div>
    <div class="field"><label>Resist Lightning</label><input id="oppose_elec" type="number"></div>
    <div class="field"><label>Resist Poison</label><input id="oppose_pois" type="number"></div>
  </div>

  <!-- Chaos & Mutations -->
  <div class="card">
    <h2>Chaos &amp; Mutations</h2>
    <div class="field"><label>Chaos Patron</label><input id="chaos_patron" type="number"></div>
    <div class="field"><label>Mutations 1 (hex)</label><input id="muta1" placeholder="0x00000000"></div>
    <div class="field"><label>Mutations 2 (hex)</label><input id="muta2" placeholder="0x00000000"></div>
    <div class="field"><label>Mutations 3 (hex)</label><input id="muta3" placeholder="0x00000000"></div>
  </div>

  <!-- Virtues -->
  <div class="card">
    <h2>Virtues</h2>
    {% for i in range(8) %}
    <div class="stat-grid">
      <div class="lbl">Virtue {{ i }}</div>
      <input id="virtues_{{ i }}" type="number" placeholder="score">
      <input id="vir_types_{{ i }}" type="number" placeholder="type">
    </div>
    {% endfor %}
    <p style="font-size:11px;color:#606080;margin-top:6px;">Score / Type index per slot</p>
  </div>

  <!-- Game State -->
  <div class="card">
    <h2>Game State</h2>
    <div class="field"><label>Is Dead</label><input id="is_dead" type="number"></div>
    <div class="field"><label>Total Winner</label><input id="total_winner" type="number"></div>
    <div class="field"><label>No Score</label><input id="noscore" type="number"></div>
    <div class="field"><label>Panic Save</label><input id="panic_save" type="number"></div>
    <div class="field"><label>Dungeon Feeling</label><input id="feeling" type="number"></div>
    <div class="field readonly"><label>Last Feeling Turn</label><input id="old_turn" type="number"></div>
    <div class="field"><label>Confusing Touch</label><input id="confusing" type="number"></div>
    <div class="field"><label>Searching Mode</label><input id="searching" type="number"></div>
    <div class="field readonly"><label>Flavour Seed</label><input id="seed_flavor" placeholder="hex"></div>
  </div>

  <!-- Equipment -->
  <div class="card" style="grid-column:1/-1">
    <h2>Equipment</h2>
    <table id="equip-table">
      <thead>
        <tr>
          <th>Slot</th><th>k_idx</th><th>Category</th><th>Name / Ego</th>
          <th>to_h</th><th>to_d</th><th>to_a</th><th>pval</th><th>ac</th>
        </tr>
      </thead>
      <tbody id="equip-body"></tbody>
    </table>
    <p style="font-size:11px;color:#606080;margin-top:8px;">
      Editing to_h / to_d / to_a / pval / ac rewrites those bytes in-place.
      The game re-derives display names from the kind table on load.
    </p>
  </div>

</div>
<div id="status">Ready.</div>

<script>
const $ = id => document.getElementById(id);

function setStatus(msg, isError=false) {
  const el = $('status');
  el.textContent = msg;
  el.className = isError ? 'error' : '';
}

async function api(endpoint, body) {
  const r = await fetch(endpoint, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(body)
  });
  return r.json();
}

async function browse() {
  const res = await api('/browse', {});
  if (res.path) $('filepath').value = res.path;
  else if (res.error) setStatus(res.error, true);
}

async function decode() {
  const path = $('filepath').value.trim();
  if (!path) { setStatus('No file selected.', true); return; }
  setStatus('Decoding…');
  const res = await api('/decode', {path});
  if (res.ok) setStatus(res.message);
  else setStatus(res.error, true);
}

async function encode() {
  const path = $('filepath').value.trim();
  if (!path) { setStatus('No file selected.', true); return; }
  setStatus('Encoding…');
  const res = await api('/encode', {path});
  if (res.ok) setStatus(res.message);
  else setStatus(res.error, true);
}

function statRawToDisplay(raw) {
  if (raw < 180) return String(Math.floor(raw / 10));
  return '18/' + String(raw - 180).padStart(2, '0');
}

function statDisplayToRaw(s) {
  s = s.trim();
  if (s.includes('/')) {
    const parts = s.split('/');
    return 180 + parseInt(parts[1], 10);
  }
  const n = parseInt(s, 10);
  return n * 10; // works for 1-17; 18→180 which equals 18/00
}

async function load() {
  const path = $('filepath').value.trim();
  if (!path) { setStatus('No file selected.', true); return; }
  setStatus('Loading…');
  const res = await api('/load', {path});
  if (res.error) { setStatus(res.error, true); return; }
  const f = res.fields;

  $('player_name').value = f.player_name;
  $('prace').value  = f.prace;
  $('pclass').value = f.pclass;
  $('psex').value   = f.psex;
  $('realm1').value = f.realm1;
  $('realm2').value = f.realm2;
  $('hitdie').value  = f.hitdie;
  $('expfact').value = f.expfact;

  $('age').value = f.age;
  $('ht').value  = f.ht;
  $('wt').value  = f.wt;
  $('sc').value  = f.sc;

  for (let i = 0; i < 6; i++) {
    $('stat_max_' + i).value = statRawToDisplay(f.stat_max[i]);
    $('stat_cur_' + i).value = statRawToDisplay(f.stat_cur[i]);
  }

  $('lev').value      = f.lev;
  $('max_lev').value  = f.max_lev;
  $('au').value       = f.au;
  $('exp').value      = f.exp;
  $('max_exp').value  = f.max_exp;
  $('exp_frac').value = f.exp_frac;
  $('place_num').value = f.place_num;

  $('mhp').value      = f.mhp;
  $('chp').value      = f.chp;
  $('chp_frac').value = f.chp_frac;
  $('msp').value      = f.msp;
  $('csp').value      = f.csp;
  $('csp_frac').value = f.csp_frac;

  $('food').value      = f.food;
  $('energy').value    = f.energy;
  $('see_infra').value = f.see_infra;
  $('blind').value     = f.blind;
  $('paralyzed').value = f.paralyzed;
  $('confused').value  = f.confused;
  $('afraid').value    = f.afraid;
  $('cut').value       = f.cut;
  $('stun').value      = f.stun;
  $('poisoned').value  = f.poisoned;
  $('image').value     = f.image;

  $('fast').value         = f.fast;
  $('slow').value         = f.slow;
  $('hero').value         = f.hero;
  $('shero').value        = f.shero;
  $('shield').value       = f.shield;
  $('blessed').value      = f.blessed;
  $('invis').value        = f.invis;
  $('infra').value        = f.infra;
  $('protevil').value     = f.protevil;
  $('invuln').value       = f.invuln;
  $('esp').value          = f.esp;
  $('wraith_form').value  = f.wraith_form;
  $('resist_magic').value = f.resist_magic;
  $('word_recall').value  = f.word_recall;
  $('oppose_fire').value  = f.oppose_fire;
  $('oppose_cold').value  = f.oppose_cold;
  $('oppose_acid').value  = f.oppose_acid;
  $('oppose_elec').value  = f.oppose_elec;
  $('oppose_pois').value  = f.oppose_pois;

  $('chaos_patron').value = f.chaos_patron;
  $('muta1').value = '0x' + f.muta1.toString(16).padStart(8, '0');
  $('muta2').value = '0x' + f.muta2.toString(16).padStart(8, '0');
  $('muta3').value = '0x' + f.muta3.toString(16).padStart(8, '0');

  for (let i = 0; i < 8; i++) {
    $('virtues_' + i).value   = f.virtues[i];
    $('vir_types_' + i).value = f.vir_types[i];
  }

  $('is_dead').value      = f.is_dead;
  $('total_winner').value = f.total_winner;
  $('noscore').value      = f.noscore;
  $('panic_save').value   = f.panic_save;
  $('feeling').value      = f.feeling;
  $('old_turn').value     = f.old_turn;
  $('confusing').value    = f.confusing;
  $('searching').value    = f.searching;
  $('seed_flavor').value  = '0x' + f.seed_flavor.toString(16).padStart(8, '0');

  // Equipment
  if (res.equipment) populateEquipTable(res.equipment);

  setStatus('Loaded: ' + f.player_name);
}

const SLOT_NAMES = ['WIELD','BOW','LEFT','RIGHT','NECK','LITE','BODY','OUTER','ARM','HEAD','HANDS','FEET'];
const TVAL_LABELS = {
  19:'Sling/Bow', 20:'Bow', 21:'Crossbow',
  23:'Sword', 24:'Polearm', 25:'Hafted',
  30:'Boots', 31:'Gloves', 33:'Helm', 34:'Shield', 35:'Cloak',
  36:'Soft Armor', 37:'Hard Armor', 38:'Dragon Armor',
  39:'Lite', 40:'Amulet', 45:'Ring',
};

function populateEquipTable(equipment) {
  const tbody = $('equip-body');
  tbody.innerHTML = '';
  equipment.forEach((item, idx) => {
    const tr = document.createElement('tr');
    const cat = TVAL_LABELS[item.tval] || ('tv'+item.tval);
    tr.innerHTML = `
      <td class="slot-name">${SLOT_NAMES[item._slot] || item._slot}</td>
      <td style="color:#606080">${item.k_idx}</td>
      <td style="color:#808090">${cat}</td>
      <td class="ego-name">${item.xname || ''}</td>
      <td><input class="stat" data-idx="${idx}" data-field="to_h" value="${item.to_h}"></td>
      <td><input class="stat" data-idx="${idx}" data-field="to_d" value="${item.to_d}"></td>
      <td><input class="stat" data-idx="${idx}" data-field="to_a" value="${item.to_a}"></td>
      <td><input class="stat" data-idx="${idx}" data-field="pval" value="${item.pval}"></td>
      <td><input class="stat" data-idx="${idx}" data-field="ac"   value="${item.ac}"></td>
    `;
    tbody.appendChild(tr);
  });
  // store for save
  window._equipment = equipment;
}

async function save() {
  const path = $('filepath').value.trim();
  if (!path) { setStatus('No file selected.', true); return; }

  const stat_max = [], stat_cur = [];
  for (let i = 0; i < 6; i++) {
    stat_max.push(statDisplayToRaw($('stat_max_' + i).value));
    stat_cur.push(statDisplayToRaw($('stat_cur_' + i).value));
  }
  const virtues = [], vir_types = [];
  for (let i = 0; i < 8; i++) {
    virtues.push(parseInt($('virtues_' + i).value) || 0);
    vir_types.push(parseInt($('vir_types_' + i).value) || 0);
  }

  const fields = {
    prace:  parseInt($('prace').value),
    pclass: parseInt($('pclass').value),
    psex:   parseInt($('psex').value),
    realm1: parseInt($('realm1').value),
    realm2: parseInt($('realm2').value),
    hitdie:  parseInt($('hitdie').value),
    expfact: parseInt($('expfact').value),
    age: parseInt($('age').value),
    ht:  parseInt($('ht').value),
    wt:  parseInt($('wt').value),
    sc:  parseInt($('sc').value),
    stat_max, stat_cur,
    lev:       parseInt($('lev').value),
    max_lev:   parseInt($('max_lev').value),
    au:        parseInt($('au').value),
    exp:       parseInt($('exp').value),
    max_exp:   parseInt($('max_exp').value),
    exp_frac:  parseInt($('exp_frac').value),
    place_num: parseInt($('place_num').value),
    mhp: parseInt($('mhp').value), chp: parseInt($('chp').value), chp_frac: parseInt($('chp_frac').value),
    msp: parseInt($('msp').value), csp: parseInt($('csp').value), csp_frac: parseInt($('csp_frac').value),
    food: parseInt($('food').value), energy: parseInt($('energy').value), see_infra: parseInt($('see_infra').value),
    blind: parseInt($('blind').value), paralyzed: parseInt($('paralyzed').value), confused: parseInt($('confused').value),
    afraid: parseInt($('afraid').value), cut: parseInt($('cut').value), stun: parseInt($('stun').value),
    poisoned: parseInt($('poisoned').value), image: parseInt($('image').value),
    fast: parseInt($('fast').value), slow: parseInt($('slow').value),
    hero: parseInt($('hero').value), shero: parseInt($('shero').value),
    shield: parseInt($('shield').value), blessed: parseInt($('blessed').value),
    invis: parseInt($('invis').value), infra: parseInt($('infra').value),
    protevil: parseInt($('protevil').value), invuln: parseInt($('invuln').value),
    esp: parseInt($('esp').value), wraith_form: parseInt($('wraith_form').value),
    resist_magic: parseInt($('resist_magic').value), word_recall: parseInt($('word_recall').value),
    oppose_fire: parseInt($('oppose_fire').value), oppose_cold: parseInt($('oppose_cold').value),
    oppose_acid: parseInt($('oppose_acid').value), oppose_elec: parseInt($('oppose_elec').value),
    oppose_pois: parseInt($('oppose_pois').value),
    chaos_patron: parseInt($('chaos_patron').value),
    muta1: parseInt($('muta1').value, 16),
    muta2: parseInt($('muta2').value, 16),
    muta3: parseInt($('muta3').value, 16),
    virtues, vir_types,
    is_dead: parseInt($('is_dead').value), total_winner: parseInt($('total_winner').value),
    noscore: parseInt($('noscore').value), panic_save: parseInt($('panic_save').value),
    feeling: parseInt($('feeling').value), old_turn: parseInt($('old_turn').value),
    confusing: parseInt($('confusing').value), searching: parseInt($('searching').value),
    seed_flavor: parseInt($('seed_flavor').value, 16),
  };

  // Collect equipment edits from table inputs
  const equip_edits = [];
  if (window._equipment) {
    document.querySelectorAll('#equip-body input.stat').forEach(inp => {
      const idx   = parseInt(inp.dataset.idx);
      const field = inp.dataset.field;
      const item  = window._equipment[idx];
      const val   = parseInt(inp.value) || 0;
      // always include all editable fields for this item so one round-trip patches all
      let existing = equip_edits.find(e => e._start === item._start);
      if (!existing) {
        existing = {_start: item._start};
        equip_edits.push(existing);
      }
      existing[field] = val;
    });
  }

  setStatus('Saving…');
  const res = await api('/save', {path, fields, equip_edits});
  if (res.ok) setStatus(res.message);
  else setStatus(res.error, true);
}
</script>
</body>
</html>
"""

def build_options(items, selected=None):
    opts = ""
    for i, name in enumerate(items):
        sel = ' selected' if i == selected else ''
        opts += f'<option value="{i}"{sel}>{name}</option>\n'
    return opts


def render_html():
    stat_names_enum = list(enumerate(STAT_NAMES))
    html = HTML
    html = html.replace("{{ race_options }}", build_options(RACES))
    html = html.replace("{{ class_options }}", build_options(CLASSES))
    html = html.replace("{{ sex_options }}", build_options(SEXES))
    html = html.replace("{{ realm_options }}", build_options(REALMS))
    # Simple template loop expansion for stat names
    stat_rows = ""
    for i, name in stat_names_enum:
        stat_rows += f"""    <div class="stat-grid">
      <div class="lbl">{name}</div>
      <input id="stat_max_{i}" placeholder="e.g. 18/50">
      <input id="stat_cur_{i}" placeholder="e.g. 18/50">
    </div>\n"""
    html = html.replace("    {% for i, name in stat_names %}\n    <div class=\"stat-grid\">\n      <div class=\"lbl\">{{ name }}</div>\n      <input id=\"stat_max_{{ i }}\" placeholder=\"e.g. 18/50\">\n      <input id=\"stat_cur_{{ i }}\" placeholder=\"e.g. 18/50\">\n    </div>\n    {% endfor %}", stat_rows)
    # Virtue loop
    virtue_rows = ""
    for i in range(8):
        virtue_rows += f"""    <div class="stat-grid">
      <div class="lbl">Virtue {i}</div>
      <input id="virtues_{i}" type="number" placeholder="score">
      <input id="vir_types_{i}" type="number" placeholder="type">
    </div>\n"""
    html = html.replace("    {% for i in range(8) %}\n    <div class=\"stat-grid\">\n      <div class=\"lbl\">Virtue {{ i }}</div>\n      <input id=\"virtues_{{ i }}\" type=\"number\" placeholder=\"score\">\n      <input id=\"vir_types_{{ i }}\" type=\"number\" placeholder=\"type\">\n    </div>\n    {% endfor %}", virtue_rows)
    return html


@app.route("/")
def index():
    return render_html()


@app.route("/browse", methods=["POST"])
def browse():
    """Open a native file picker. Falls through to the next tool only if the
    previous one was not found (exit 127). If the user cancels, returns path=null."""
    try:
        import platform
        if platform.system() == "Windows":
            ps = (
                "Add-Type -AssemblyName System.Windows.Forms; "
                "Add-Type -TypeDefinition 'using System; using System.Runtime.InteropServices; "
                "public class WinHelper { "
                "[DllImport(\"user32.dll\")] public static extern bool SetForegroundWindow(IntPtr hWnd); "
                "}'; "
                "$owner = New-Object System.Windows.Forms.Form; "
                "$owner.TopMost = $true; "
                "$owner.StartPosition = 'Manual'; "
                "$owner.Location = New-Object System.Drawing.Point(-2000,-2000); "
                "$owner.Size = New-Object System.Drawing.Size(1,1); "
                "$owner.Show(); "
                "[WinHelper]::SetForegroundWindow($owner.Handle); "
                "$f = New-Object System.Windows.Forms.OpenFileDialog; "
                "$f.Title = 'Select Zangband save file'; "
                "$null = $f.ShowDialog($owner); "
                "$owner.Dispose(); "
                "$f.FileName"
            )
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps],
                capture_output=True, text=True, timeout=60
            )
            path = r.stdout.strip()
            return jsonify({"path": path or None})

        # Linux/macOS: try zenity, kdialog, then tkinter
        dialogs = [
            ["zenity", "--file-selection", "--title=Select Zangband save file"],
            ["kdialog", "--getopenfilename", ".", "--title", "Select Zangband save file"],
        ]
        for cmd in dialogs:
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            except FileNotFoundError:
                continue
            if r.returncode == 0:
                return jsonify({"path": r.stdout.strip()})
            else:
                return jsonify({"path": None})

        script = (
            "import tkinter as tk; from tkinter import filedialog; "
            "root = tk.Tk(); root.withdraw(); "
            "path = filedialog.askopenfilename(title='Select Zangband save file'); "
            "print(path or '', end='')"
        )
        r = subprocess.run([sys.executable, "-c", script],
                           capture_output=True, text=True, timeout=60)
        path = r.stdout.strip()
        return jsonify({"path": path or None})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/decode", methods=["POST"])
def decode():
    path = request.json.get("path", "")
    if not Path(path).exists():
        return jsonify({"error": f"File not found: {path}"})
    out_path = path + ".decoded"
    try:
        result = subprocess.run(
            [sys.executable, str(CODEC), "decode", path, "-o", out_path],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return jsonify({"ok": True, "message": f"Decoded → {out_path}"})
        return jsonify({"error": result.stderr.strip() or result.stdout.strip() or "Decode failed"})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/encode", methods=["POST"])
def encode():
    path = request.json.get("path", "")
    # Codec input must be the .decoded file; output strips the .decoded suffix
    decoded_path = path if path.endswith(".decoded") else path + ".decoded"
    if not Path(decoded_path).exists():
        return jsonify({"error": f"Decoded file not found: {decoded_path}"})
    p = Path(decoded_path)
    out_path = str(p.with_suffix(""))  # strips .decoded → original filename
    try:
        result = subprocess.run(
            [sys.executable, str(CODEC), "encode", str(decoded_path), "-o", out_path],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return jsonify({"ok": True, "message": f"Encoded → {out_path}"})
        return jsonify({"error": result.stderr.strip() or result.stdout.strip() or "Encode failed"})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/load", methods=["POST"])
def load():
    path = request.json.get("path", "")
    # Auto-try .decoded variant
    decoded_path = path if path.endswith(".decoded") else path + ".decoded"
    if not Path(decoded_path).exists():
        if Path(path).exists():
            decoded_path = path
        else:
            return jsonify({"error": f"File not found: {decoded_path}\nDecode the save first."})
    try:
        data = Path(decoded_path).read_bytes()
        fields = read_fields(data)
        try:
            equipment = read_equipment(data)
            # Remove non-serialisable internal keys before sending
            equip_json = []
            for item in equipment:
                d = {k: v for k, v in item.items()}
                # triggers list contains tuples; convert to lists for JSON
                d["triggers"] = [list(t) for t in d["triggers"]]
                equip_json.append(d)
        except Exception as eq_err:
            equip_json = None  # non-fatal: equipment section optional
        return jsonify({"fields": fields, "equipment": equip_json})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/save", methods=["POST"])
def save():
    body = request.json
    path = body.get("path", "")
    fields = body.get("fields", {})
    decoded_path = path if path.endswith(".decoded") else path + ".decoded"
    if not Path(decoded_path).exists():
        if Path(path).exists():
            decoded_path = path
        else:
            return jsonify({"error": f"File not found: {decoded_path}"})
    try:
        data = Path(decoded_path).read_bytes()
        new_data = write_fields(data, fields)
        equip_edits = body.get("equip_edits", [])
        if equip_edits:
            new_data = write_equipment(new_data, equip_edits)
        Path(decoded_path).write_bytes(new_data)
        return jsonify({"ok": True, "message": f"Saved → {decoded_path}"})
    except Exception as e:
        return jsonify({"error": str(e)})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import socket
    port = 5174
    url = f"http://127.0.0.1:{port}"

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as _s:
        already_running = _s.connect_ex(("127.0.0.1", port)) == 0

    if already_running:
        print(f"Editor already running at {url} — opening browser.")
        webbrowser.open(url)
    else:
        print(f"Zangband Save Editor running at {url}")
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
        app.run(port=port, debug=False)
