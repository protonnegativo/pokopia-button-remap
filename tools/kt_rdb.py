#!/usr/bin/env python3
"""Lê o root.rdb (_DRK0000) da Koei Tecmo: um registro IDRK por arquivo, com o bloco de localização no fim.

uso: kt_rdb.py <root.rdb> [--ktid HEX] [--diff OUTRO.rdb]
"""
import argparse, struct


def read(path):
    d = open(path, 'rb').read()
    assert d[:8] == b'_DRK0000', 'nao e _DRK0000'
    hdr_size, system_id, count, ktid = struct.unpack_from('<IIII', d, 8)
    path_end = d.index(b'\0', 0x18)
    pos = (path_end + 1 + 3) & ~3
    out = {}
    order = []
    while pos + 0x30 <= len(d):
        if d[pos:pos + 8] != b'IDRK0000':
            raise SystemExit(f'IDRK esperado em 0x{pos:x}')
        entry_size, loc_size, file_size = struct.unpack_from('<QQQ', d, pos + 8)
        entry_type, fktid, tktid, flags = struct.unpack_from('<IIII', d, pos + 0x20)
        params = d[pos + 0x30:pos + entry_size - loc_size]
        loc = d[pos + entry_size - loc_size:pos + entry_size]
        e = dict(pos=pos, entry_size=entry_size, loc_size=loc_size, file_size=file_size, entry_type=entry_type,
                 ktid=fktid, type_ktid=tktid, flags=flags, params=params, loc=loc)
        out[fktid] = e
        order.append(fktid)
        pos += entry_size
        pos = (pos + 3) & ~3
    return d, out, order


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('rdb'); ap.add_argument('--ktid'); ap.add_argument('--diff')
    a = ap.parse_args()
    _, ents, order = read(a.rdb)
    print(f'{len(ents)} registros')
    if a.ktid:
        e = ents[int(a.ktid, 16)]
        print({k: (v.hex(' ') if isinstance(v, bytes) else (hex(v) if isinstance(v, int) else v)) for k, v in e.items()})
    if a.diff:
        _, other, _ = read(a.diff)
        changed = [k for k in order if k in other and (other[k]['loc'] != ents[k]['loc'] or other[k]['file_size'] != ents[k]['file_size'])]
        print(f'{len(changed)} registros diferentes; {len(set(other) - set(ents))} novos')
        for k in changed[:12]:
            o, n = ents[k], other[k]
            print(f'{k:08x} tipo={o["type_ktid"]:08x} size {o["file_size"]}->{n["file_size"]}\n   orig loc={o["loc"].hex(" ")}\n   mod  loc={n["loc"].hex(" ")}')


if __name__ == '__main__':
    main()
