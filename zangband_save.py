#!/usr/bin/env python3
"""
zangband_save.py — decode / encode / inspect Zangband save files.

Zangband save file layout (src/save.c, src/load.c):
  byte 0      VER_MAJOR   — written raw (xor_byte reset to 0 before each header byte)
  byte 1      VER_MINOR
  byte 2      VER_PATCH
  byte 3      seed        — random byte; becomes the initial rolling-XOR key
  bytes 4..N-9  body      — each encoded byte = prev_encoded_byte XOR decoded_byte
  bytes N-8..N-5  v_stamp — u32b LE checksum of decoded body bytes, itself encoded
  bytes N-4..N-1  x_stamp — u32b LE checksum of encoded body bytes, itself encoded

The "decoded" file format produced by this tool:
  • Bytes 0-3 are preserved verbatim (version + seed).
  • Bytes 4-end are the raw decoded values (XOR removed).
  • The last 8 bytes are the decoded v_stamp / x_stamp values.
  Encoding reverses this exactly, recomputing both checksums from scratch.
"""

import argparse
import datetime
import os
import struct
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Core codec
# ---------------------------------------------------------------------------

def decode(data: bytes) -> bytes:
    """Remove the rolling-XOR encoding from a Zangband save file."""
    if len(data) < 12:
        raise ValueError("File is too short to be a valid Zangband save")
    out = bytearray(data[:4])          # header copied verbatim
    xor_byte = data[3]                  # seed = initial key
    for c in data[4:]:
        out.append(c ^ xor_byte)
        xor_byte = c                    # next key = previous *encoded* byte
    return bytes(out)


def encode(decoded: bytes, seed: int | None = None) -> bytes:
    """Apply rolling-XOR encoding to a decoded save file, recomputing checksums.

    Args:
        decoded: bytes produced by decode() (or hand-edited equivalent)
        seed:    byte 3 value to use; if None, a fresh random byte is chosen
    """
    if len(decoded) < 12:
        raise ValueError("Decoded data is too short")

    if seed is None:
        seed = int.from_bytes(os.urandom(1))

    # Build output: 4-byte header (seed possibly updated), then encoded body
    header = bytearray(decoded[:4])
    header[3] = seed

    # Body = decoded bytes from offset 4, excluding the last 8 checksum bytes.
    # We recompute checksums, then encode body + checksums together.
    body_decoded = decoded[4:-8]   # everything between header and old checksums

    # --- v_stamp: sum of all decoded body bytes (offsets 4..end-9)
    # --- x_stamp: sum of all encoded body bytes PLUS the 4 encoded v_stamp bytes
    #
    # This matches load.c exactly:
    #   n_v_check = v_check                    -- saved before reading v_stamp
    #   rd_u32b(&o_v_check)                    -- reads 4 bytes; their encoded form
    #                                             is added to x_check by sf_get()
    #   n_x_check = x_check                    -- saved after those 4 encoded bytes
    #   rd_u32b(&o_x_check)
    # So x_stamp must cover encoded body bytes + encoded v_stamp bytes.

    v_stamp: int = 0
    x_stamp: int = 0
    xor_byte: int = seed
    encoded_body = bytearray()

    for d in body_decoded:
        e = xor_byte ^ d
        v_stamp = (v_stamp + d) & 0xFFFFFFFF
        x_stamp = (x_stamp + e) & 0xFFFFFFFF
        xor_byte = e
        encoded_body.append(e)

    # Encode v_stamp (4 bytes) and fold their encoded form into x_stamp
    encoded_v_stamp = bytearray()
    for d in struct.pack('<I', v_stamp):
        e = xor_byte ^ d
        x_stamp = (x_stamp + e) & 0xFFFFFFFF   # x_stamp accumulates these too
        xor_byte = e
        encoded_v_stamp.append(e)

    # x_stamp is now complete; encode it (its encoded bytes are NOT added to anything)
    encoded_x_stamp = bytearray()
    for d in struct.pack('<I', x_stamp):
        e = xor_byte ^ d
        xor_byte = e
        encoded_x_stamp.append(e)

    return bytes(header) + bytes(encoded_body) + bytes(encoded_v_stamp) + bytes(encoded_x_stamp)


# ---------------------------------------------------------------------------
# Metadata helpers
# ---------------------------------------------------------------------------

def _info(decoded: bytes) -> dict:
    """Extract header metadata from a decoded save file."""
    if len(decoded) < 30:
        raise ValueError("Decoded data too short for metadata")

    offset = 4
    savefile_version = struct.unpack_from('<I', decoded, offset)[0]; offset += 4
    sf_xtra          = struct.unpack_from('<I', decoded, offset)[0]; offset += 4
    sf_when          = struct.unpack_from('<I', decoded, offset)[0]; offset += 4
    sf_lives         = struct.unpack_from('<H', decoded, offset)[0]; offset += 2
    sf_saves         = struct.unpack_from('<H', decoded, offset)[0]; offset += 2

    try:
        ts = datetime.datetime.fromtimestamp(sf_when).strftime('%Y-%m-%d %H:%M:%S')
    except (OSError, OverflowError):
        ts = f'(unix={sf_when})'

    v_stamp = struct.unpack_from('<I', decoded, -8)[0]
    x_stamp = struct.unpack_from('<I', decoded, -4)[0]

    # Verify v_stamp against body
    body = decoded[4:-8]
    computed_v = sum(body) & 0xFFFFFFFF

    return {
        'version':          f"{decoded[0]}.{decoded[1]}.{decoded[2]}",
        'seed':             decoded[3],
        'savefile_version': savefile_version,
        'sf_xtra':          sf_xtra,
        'saved_at':         ts,
        'sf_lives':         sf_lives,
        'sf_saves':         sf_saves,
        'v_stamp':          v_stamp,
        'x_stamp':          x_stamp,
        'v_stamp_ok':       computed_v == v_stamp,
        'size':             len(decoded),
    }


def print_info(decoded: bytes, label: str = '') -> None:
    m = _info(decoded)
    if label:
        print(f"File        : {label}")
    print(f"Version     : {m['version']}  (savefile_version={m['savefile_version']})")
    print(f"Seed byte   : 0x{m['seed']:02x}")
    print(f"Saved at    : {m['saved_at']}")
    print(f"Past lives  : {m['sf_lives']}")
    print(f"Times saved : {m['sf_saves']}")
    print(f"Size        : {m['size']:,} bytes")
    ok = 'OK' if m['v_stamp_ok'] else 'MISMATCH — file may be corrupt'
    print(f"Checksum    : v_stamp=0x{m['v_stamp']:08x}  x_stamp=0x{m['x_stamp']:08x}  [{ok}]")


def verify(raw: bytes) -> bool:
    """Decode raw bytes and verify the embedded checksums. Returns True if valid."""
    decoded = decode(raw)
    m = _info(decoded)
    return m['v_stamp_ok']


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def cmd_decode(args):
    for src in args.files:
        raw = Path(src).read_bytes()
        if args.verify_only:
            ok = verify(raw)
            status = 'OK' if ok else 'CORRUPT'
            print(f"{src}: checksum {status}")
            continue

        decoded = decode(raw)

        if args.info:
            print_info(decoded, label=src)
            print()
            continue

        if args.output:
            out_path = Path(args.output)
        else:
            out_path = Path(src).with_suffix(Path(src).suffix + '.decoded')

        out_path.write_bytes(decoded)
        print(f"Decoded  {src}  →  {out_path}  ({len(decoded):,} bytes)")

        if args.info:
            print_info(decoded)


def cmd_encode(args):
    seed = None
    if args.seed is not None:
        seed = int(args.seed, 0)
        if not 0 <= seed <= 255:
            sys.exit("--seed must be a value 0-255")

    for src in args.files:
        decoded = Path(src).read_bytes()

        # If the file looks already-encoded (high entropy), warn.
        # Simple heuristic: if byte[3] XOR byte[4] produces a printable or 0 result
        # in the first few decoded positions it is probably already decoded.
        # We can't be definitive, so just encode and trust the user.

        encoded = encode(decoded, seed=seed)

        if args.output:
            out_path = Path(args.output)
        else:
            # Strip a trailing .decoded suffix if present, else add .encoded
            p = Path(src)
            if p.suffix == '.decoded':
                out_path = p.with_suffix('')
            else:
                out_path = p.with_suffix(p.suffix + '.encoded')

        out_path.write_bytes(encoded)
        print(f"Encoded  {src}  →  {out_path}  ({len(encoded):,} bytes)")
        if args.verbose:
            print_info(decode(encoded), label=str(out_path))


def cmd_info(args):
    for src in args.files:
        raw = Path(src).read_bytes()
        # Auto-detect: if v_stamp checks out after decode it's an encoded file;
        # if it checks out directly treat it as already decoded.
        decoded = decode(raw)
        m = _info(decoded)
        if not m['v_stamp_ok']:
            # Maybe it's already decoded
            m2 = _info(raw)
            if m2['v_stamp_ok']:
                decoded = raw
                m = m2
                note = ' (already decoded)'
            else:
                note = ' ⚠ checksum MISMATCH'
        else:
            note = ''
        print_info(decoded, label=src + note)
        print()


def cmd_diff(args):
    files = args.files
    if len(files) != 2:
        sys.exit("diff requires exactly 2 files")

    def load(path):
        raw = Path(path).read_bytes()
        dec = decode(raw)
        if _info(dec)['v_stamp_ok']:
            return dec
        # Maybe already decoded
        if _info(raw)['v_stamp_ok']:
            return raw
        # Return decoded anyway
        return dec

    a = load(files[0])
    b = load(files[1])

    print(f"=== {files[0]}")
    print_info(a)
    print()
    print(f"=== {files[1]}")
    print_info(b)
    print()

    minlen = min(len(a), len(b))

    # Collect contiguous differing runs
    runs = []
    in_diff = False
    start = 0
    for i in range(minlen):
        if a[i] != b[i]:
            if not in_diff:
                start = i
                in_diff = True
        else:
            if in_diff:
                runs.append((start, i - 1))
                in_diff = False
    if in_diff:
        runs.append((start, minlen - 1))

    total_diff = sum(e - s + 1 for s, e in runs)
    tail = abs(len(a) - len(b))

    print(f"Differing regions : {len(runs)}")
    print(f"Differing bytes   : {total_diff:,} out of {minlen:,} (plus {tail} tail bytes in the longer file)")
    print()

    limit = args.limit if args.limit else 30
    shown = 0
    for s, e in runs:
        if shown >= limit:
            print(f"  ... ({len(runs) - shown} more regions not shown; use --limit to see more)")
            break
        length = e - s + 1
        peek = min(24, length)
        a_hex = a[s:s+peek].hex(' ')
        b_hex = b[s:s+peek].hex(' ')
        a_str = ''.join(chr(c) if 32 <= c < 127 else '.' for c in a[s:s+peek])
        b_str = ''.join(chr(c) if 32 <= c < 127 else '.' for c in b[s:s+peek])
        print(f"  offset {s:6d}-{e:6d}  ({length} bytes)")
        print(f"    A hex : {a_hex}")
        print(f"    B hex : {b_hex}")
        if any(32 <= c < 127 for c in a[s:s+peek]):
            print(f"    A str : {a_str}")
            print(f"    B str : {b_str}")
        shown += 1

    if len(a) != len(b):
        longer, shorter_len = (files[0], len(b)) if len(a) > len(b) else (files[1], len(a))
        print(f"\n  {longer} has {tail} extra bytes at offset {shorter_len}:")
        extra = a[shorter_len:shorter_len+48] if len(a) > len(b) else b[shorter_len:shorter_len+48]
        print(f"  {extra.hex(' ')}")


def main():
    parser = argparse.ArgumentParser(
        description='Decode, encode, and inspect Zangband save files.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Inspect a save file
  %(prog)s info 1000

  # Decode a save file (remove XOR encoding)
  %(prog)s decode 1000          # → 1000.decoded
  %(prog)s decode 1000 -o plain.bin

  # Encode a decoded file back to a valid save (fresh random seed)
  %(prog)s encode 1000.decoded  # → 1000
  %(prog)s encode 1000.decoded --seed 0x42

  # Compare two save files (works on raw or decoded files)
  %(prog)s diff 1000.pre 1000.post

  # Verify checksums without writing output
  %(prog)s decode 1000 --verify-only
        """)

    sub = parser.add_subparsers(dest='command', required=True)

    # --- decode ---
    p_dec = sub.add_parser('decode', help='Remove XOR encoding from a save file')
    p_dec.add_argument('files', nargs='+', metavar='FILE')
    p_dec.add_argument('-o', '--output', metavar='OUT',
                       help='Output path (only valid with a single input file)')
    p_dec.add_argument('--info', action='store_true',
                       help='Print metadata instead of writing a file')
    p_dec.add_argument('--verify-only', action='store_true',
                       help='Check checksums and exit (no output file written)')

    # --- encode ---
    p_enc = sub.add_parser('encode', help='Apply XOR encoding to a decoded save file')
    p_enc.add_argument('files', nargs='+', metavar='FILE')
    p_enc.add_argument('-o', '--output', metavar='OUT',
                       help='Output path (only valid with a single input file)')
    p_enc.add_argument('--seed', metavar='BYTE',
                       help='Seed byte (0-255, hex ok: 0x7d). Default: random')
    p_enc.add_argument('-v', '--verbose', action='store_true',
                       help='Print metadata of the encoded file')

    # --- info ---
    p_info = sub.add_parser('info', help='Print save file metadata')
    p_info.add_argument('files', nargs='+', metavar='FILE')

    # --- diff ---
    p_diff = sub.add_parser('diff', help='Compare two save files')
    p_diff.add_argument('files', nargs=2, metavar='FILE')
    p_diff.add_argument('--limit', type=int, default=30, metavar='N',
                        help='Max number of differing regions to show (default 30)')

    args = parser.parse_args()

    dispatch = {
        'decode': cmd_decode,
        'encode': cmd_encode,
        'info':   cmd_info,
        'diff':   cmd_diff,
    }
    dispatch[args.command](args)


if __name__ == '__main__':
    main()
