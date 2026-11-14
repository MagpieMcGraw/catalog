"""Copy the tables catalog reads out of a Diablo II Resurrected install.

The game keeps its files in CASC archives (Data\\data\\data.NNN), not as
loose text, so this reads them: build config -> encoding file (content key
to encoded key) -> root manifest (file path to content key) -> the BLTE
blobs in the archives. Writes Runes.txt, cubemain.txt, misc.txt and
ItemTypes.txt to ..\\data beside this folder.

    python -I extract_tables.py [install folder]

The default install folder is GAME below. Nothing in the install is changed.
"""
import os
import struct
import sys
import zlib

GAME = r"D:\Games\Diablo II Resurrected"

# The game's files this catalog reads, by path inside the manifest.
WANT = [
    "data:data/global/excel/Runes.txt",
    "data:data/global/excel/cubemain.txt",
    "data:data/global/excel/misc.txt",
    "data:data/global/excel/ItemTypes.txt",
    "data:data/global/excel/armor.txt",
    "data:data/global/excel/weapons.txt",
]

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "data")


class Archives:
    def __init__(self, game):
        self.data = os.path.join(game, "Data", "data")
        self.index = {}
        for name in sorted(os.listdir(self.data)):
            if name.endswith(".idx"):
                self.add_index(os.path.join(self.data, name))

    def add_index(self, path):
        # Index records are 18 bytes: a 9-byte key prefix, a 5-byte big-endian
        # offset (archive = offset >> 30, position = the rest) and a 4-byte
        # little-endian size. Records are found by scanning, then checked
        # against the archive itself in find().
        with open(path, "rb") as f:
            b = f.read()
        for pos in range(0x28, len(b) - 18 + 1):
            key = b[pos:pos + 9]
            if key == b"\x00" * 9:
                continue
            off = int.from_bytes(b[pos + 9:pos + 14], "big")
            size = struct.unpack("<I", b[pos + 14:pos + 18])[0]
            if 0 < size <= 200 * 1024 * 1024:
                self.index.setdefault(key, []).append((off >> 30, off & ((1 << 30) - 1), size))

    def find(self, ekey):
        key = bytes.fromhex(ekey)
        for archive, pos, size in self.index.get(key[:9], []):
            path = os.path.join(self.data, "data.%03d" % archive)
            if not os.path.exists(path):
                continue
            with open(path, "rb") as f:
                f.seek(pos)
                head = f.read(34)
            # Local headers keep the whole key reversed, or (some entries) the
            # first 9 bytes reversed after 7 zeros; the blob starts 30 bytes in.
            full = head[:16] == key[::-1]
            short = head[:7] == b"\x00" * 7 and head[7:16] == key[:9][::-1]
            if (full or short) and head[30:34] == b"BLTE":
                return path, pos, size
        raise KeyError("no archive entry for " + ekey)

    def read(self, ekey):
        path, pos, size = self.find(ekey)
        with open(path, "rb") as f:
            f.seek(pos + 30)
            return blte(f.read(size))


def blte(data):
    assert data[:4] == b"BLTE", "not a BLTE blob"
    hsize = struct.unpack(">I", data[4:8])[0]
    if hsize == 0:
        return chunk(data[8:])
    # The header size counts the magic and itself: the chunk table is
    # flags (1), chunk count (3), then 24 bytes per chunk (sizes and a hash).
    count = data[9] << 16 | data[10] << 8 | data[11]
    out = []
    pos = hsize
    for i in range(count):
        csize = struct.unpack(">I", data[12 + i * 24:16 + i * 24])[0]
        out.append(chunk(data[pos:pos + csize]))
        pos += csize
    return b"".join(out)


def chunk(c):
    mode = c[0:1]
    if mode == b"N":
        return c[1:]
    if mode == b"Z":
        return zlib.decompress(c[1:])
    raise NotImplementedError("BLTE chunk mode %r" % mode)


def build_config(game):
    with open(os.path.join(game, ".build.info"), "rb") as f:
        rows = f.read().decode("utf-8", "replace").splitlines()
    build_key = rows[1].split("|")[2]
    path = os.path.join(game, "Data", "config", build_key[0:2], build_key[2:4], build_key)
    keys = {}
    with open(path, "rb") as f:
        for line in f.read().decode("utf-8", "replace").splitlines():
            if " = " in line:
                name, value = line.split(" = ", 1)
                keys[name] = value.split()
    return keys


def encoding_table(enc):
    """Content key (hex) to its first encoded key (hex), from the encoding file."""
    assert enc[:2] == b"EN", "not an encoding file"
    ckey_len = enc[3]
    page_size = struct.unpack(">H", enc[5:7])[0] * 1024
    page_count = struct.unpack(">I", enc[9:13])[0]
    espec_size = struct.unpack(">I", enc[18:22])[0]
    pages = 22 + espec_size + page_count * (ckey_len + 16)
    table = {}
    for p in range(page_count):
        pos = pages + p * page_size
        end = pos + page_size
        while pos < end:
            n = enc[pos]
            if n == 0:
                break
            ckey = enc[pos + 6:pos + 22].hex()
            if ckey not in table:
                table[ckey] = enc[pos + 22:pos + 38].hex()
            pos += 22 + 16 * n
    return table


def manifest_hashes(root):
    """Path (as in the manifest) to content key, from the root text manifest."""
    hashes = {}
    for line in root.decode("utf-8", "replace").splitlines():
        cols = line.split("|")
        if len(cols) >= 2:
            hashes[cols[0]] = cols[1]
    return hashes


def main():
    game = sys.argv[1] if len(sys.argv) > 1 else GAME
    archives = Archives(game)
    keys = build_config(game)
    encoding = encoding_table(archives.read(keys["encoding"][1]))
    root = archives.read(encoding[keys["root"][0]])
    hashes = manifest_hashes(root)
    os.makedirs(OUT, exist_ok=True)
    for want in WANT:
        ckey = hashes[want]
        data = archives.read(encoding[ckey])
        name = want.split("/")[-1]
        with open(os.path.join(OUT, name), "wb") as f:
            f.write(data)
        print("wrote", os.path.normpath(os.path.join(OUT, name)), len(data), "bytes")


if __name__ == "__main__":
    main()
