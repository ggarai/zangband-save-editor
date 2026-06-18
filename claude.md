You’ll construct a save game editor for the rogue-like RPG called Zangband.
Under /home/gg/Git/, the repository zangband/zangband/ contains the game’s source code, written in C. Don’t commit anything here, it is for reference.
The repository zangband-save-editor is where you’ll work.
The codec is at /home/gg/Git/zangband/zangband_save.py — it handles decoding/encoding of save files (rolling-XOR). Always work on decoded files.

## Save file layout

Save files use a rolling-XOR encoding. Decoded with zangband_save.py, the body is raw binary.
Multi-byte integers are little-endian (low byte first). The source comments say “big-endian” in places — this is wrong; the actual wr_u16b/wr_u32b functions write low byte first.

Character data begins with the PC’s name (null-terminated string) at around decoded offset 0xC800, immediately followed by the died_from string. For a living character, died_from is always “(saved)”.

All character property offsets are counted from the closing ‘)’ of “(saved)”:
- 0x00: ‘)’ (anchor)
- 0x01: ‘\0’ (end of died_from)
- 0x02–0x05: four empty history strings (each ‘\0’)
- 0x06 onward: character properties (see value-mapping.md)

The complete property map, including sizes, types, field names, and a sample value from Chin-su (level 15 High-Elf Monk), is in value-mapping.md.

Key source references:
- save.c lines 888–1004: wr_extra() — writes character properties in order
- load.c lines 1228–1398: rd_extra() — reads them back (use save.c as the authoritative layout)

## What’s done

- value-mapping.md: complete offset table from 0x06 (prace) through 0x141 (old_turn), verified against Chin-su.bak.

## What's next

Add inventory management to the editor. First, find out how inventory items and equipped items are saved. Reference files in the folder are 1000.Gg (a savegame), inventory.txt and equipped.txt (the inventory and equipped items as listed in-game).
