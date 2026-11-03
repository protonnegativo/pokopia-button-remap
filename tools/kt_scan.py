#!/usr/bin/env python3
"""Lista as entradas IDRK de arquivos .fdata da Koei Tecmo (formato KIDS / PDRK0000).

uso: kt_scan.py <arquivo.fdata> [--type HEX] [--extract DIR]
Só lê; com --extract grava as entradas (descomprimidas) em DIR/<ktid>.<ext>.
"""
import argparse, os, struct, sys, zlib

EXT = {0xafbec60c: 'g1t', 0xad57ebba: 'g1t', 0x563bdef1: 'g1m', 0x6fa91671: 'g1a', 0x20a6a0bb: 'kidsobjdb',
       0x5153729b: 'mtl', 0xb340861a: 'mtl', 0xf20de437: 'texinfo', 0xbf6b52c7: 'name', 0x79c724c2: 'g1p'}
CHUNK = 16384


def entries(path):
    with open(path, 'rb') as f:
        if f.read(8) != b'PDRK0000':
            raise SystemExit(f'{path}: nao e PDRK0000')
        pos = 0x10
        size = os.path.getsize(path)
        while pos + 0x30 <= size:
            f.seek(pos)
            h = f.read(0x30)
            if h[:8] != b'IDRK0000':
                raise SystemExit(f'{path}: IDRK esperado em 0x{pos:x}, achei {h[:8]!r}')
            entry_size, comp_size, file_size = struct.unpack_from('<QQQ', h, 8)
            entry_type, ktid, type_ktid, flags = struct.unpack_from('<IIII', h, 0x20)
            data_off = pos + entry_size - comp_size
            yield dict(offset=pos, entry_size=entry_size, comp_size=comp_size, file_size=file_size,
                       entry_type=entry_type, ktid=ktid, type_ktid=type_ktid, flags=flags, data_off=data_off)
            pos += entry_size
            pos += (0x10 - pos % 0x10) % 0x10


def read_data(path, e):
    with open(path, 'rb') as f:
        f.seek(e['data_off'])
        if e['comp_size'] == e['file_size']:
            return f.read(e['file_size'])
        out = bytearray(); left = e['file_size']
        while left > 0:
            zsize = struct.unpack('<H', f.read(2))[0]
            f.read(8)  # preenchimento
            out += zlib.decompress(f.read(zsize))
            left -= min(left, CHUNK)
        return bytes(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('fdata')
    ap.add_argument('--type', help='filtra por type ktid (hex)')
    ap.add_argument('--extract', help='pasta de saída')
    a = ap.parse_args()
    want = int(a.type, 16) if a.type else None
    counts = {}
    for e in entries(a.fdata):
        counts[e['type_ktid']] = counts.get(e['type_ktid'], 0) + 1
        if want is not None and e['type_ktid'] != want:
            continue
        ext = EXT.get(e['type_ktid'], f"{e['type_ktid']:08x}")
        if want is not None or a.extract:
            print(f"0x{e['offset']:010x} ktid={e['ktid']:08x} {ext:9} size={e['file_size']:>9} comp={e['comp_size']:>9}")
        if a.extract and (want is None or e['type_ktid'] == want):
            os.makedirs(a.extract, exist_ok=True)
            with open(os.path.join(a.extract, f"{e['ktid']:08x}.{ext}"), 'wb') as o:
                o.write(read_data(a.fdata, e))
    if want is None:
        for t, c in sorted(counts.items(), key=lambda x: -x[1]):
            print(f'  {EXT.get(t, f"{t:08x}"):10} {c}')


if __name__ == '__main__':
    main()
