#!/usr/bin/env python3
"""Decodifica texturas .g1t (GT1G0600) de Switch/Switch 2 para PNG.

Formatos suportados: 0x62 (BC3/DXT5), 0x60 (BC1), 0x66 (BC7), com swizzle block-linear da Tegra.
uso: g1t_decode.py <arquivo.g1t|pasta> <saida> [--max-size N] [--info]
"""
import argparse, os, struct, sys
import numpy as np
from PIL import Image

# formato -> (decoder bcn, bytes por bloco 4x4)
BCN = {0x60: (1, 8), 0x61: (2, 16), 0x62: (3, 16), 0x63: (4, 8), 0x64: (5, 16), 0x66: (7, 16),
       0x59: (1, 8), 0x5b: (3, 16), 0x5f: (7, 16)}


def parse(data):
    if data[:4] != b'GT1G':
        raise ValueError('nao e GT1G')
    file_size, hdr_size, count, platform = struct.unpack_from('<IIII', data, 8)
    offsets = struct.unpack_from(f'<{count}I', data, hdr_size)
    texs = []
    for i, rel in enumerate(offsets):
        off = hdr_size + rel
        zmip, fmt, dxdy = data[off], data[off + 1], data[off + 2]
        extended = data[off + 7]
        pos = off + 8
        ext_size = 0
        if extended:
            ext_size = struct.unpack_from('<I', data, pos)[0]
            pos += ext_size
        end = hdr_size + offsets[i + 1] if i + 1 < count else len(data)
        w, h = 1 << (dxdy & 0xf), 1 << (dxdy >> 4)
        texs.append(dict(index=i, fmt=fmt, width=w, height=h, mips=zmip >> 4, header=off, data_off=pos,
                         data_end=end, ext_size=ext_size, platform=platform))
    return texs


NATIVE_TILING = True


def block_height_for(height_blocks):
    bh = 16
    while bh > 1 and height_blocks <= (bh // 2) * 8:
        bh //= 2
    return bh


def deswizzle(raw, width_el, height_el, bpe):
    """Desfaz o block-linear da Tegra; elemento = bloco 4x4 (bpe bytes)."""
    bh = block_height_for(height_el)
    width_bytes = width_el * bpe
    gobs_x = (width_bytes + 63) // 64
    rows = ((height_el + 8 * bh - 1) // (8 * bh)) * 8 * bh
    need = gobs_x * 64 * rows
    src = np.frombuffer(raw[:need].ljust(need, b'\0'), dtype=np.uint8)
    y, xb = np.mgrid[0:height_el, 0:width_bytes]
    gob = ((y // (8 * bh)) * 512 * bh * gobs_x + (xb // 64) * 512 * bh + ((y % (8 * bh)) // 8) * 512)
    addr = gob + ((xb % 64) // 32) * 256 + ((y % 8) // 2) * 64 + ((xb % 32) // 16) * 32 + (y % 2) * 16 + (xb % 16)
    if NATIVE_TILING:
        # Switch 2 (tiling nativo): troca os bits 5 e 6 do endereço, como o NativeGobOffset do Eglantine.
        diff = ((addr >> 5) ^ (addr >> 6)) & 1
        addr = addr ^ (diff << 5) ^ (diff << 6)
    return src[addr].tobytes()


def decode(data, tex, swizzled=True):
    if tex['fmt'] not in BCN:
        raise ValueError(f"formato 0x{tex['fmt']:02x} nao suportado")
    n, bpe = BCN[tex['fmt']]
    w, h = tex['width'], tex['height']
    wb, hb = (w + 3) // 4, (h + 3) // 4
    raw = data[tex['data_off']:tex['data_end']]
    lin = deswizzle(raw, wb, hb, bpe) if swizzled else raw[:wb * hb * bpe]
    mode = 'L' if n == 4 else 'RGBA'
    return Image.frombytes(mode, (w, h), lin, 'bcn', n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src'); ap.add_argument('out')
    ap.add_argument('--max-size', type=int, default=0, help='só texturas com lado <= N')
    ap.add_argument('--info', action='store_true')
    ap.add_argument('--linear', action='store_true', help='não desfaz o swizzle')
    a = ap.parse_args()
    files = [a.src] if os.path.isfile(a.src) else [os.path.join(a.src, f) for f in sorted(os.listdir(a.src))]
    os.makedirs(a.out, exist_ok=True)
    ok = bad = 0
    for f in files:
        data = open(f, 'rb').read()
        try:
            texs = parse(data)
        except Exception as e:
            bad += 1; continue
        for t in texs:
            if a.max_size and (t['width'] > a.max_size or t['height'] > a.max_size):
                continue
            name = os.path.splitext(os.path.basename(f))[0] + (f"_{t['index']}" if len(texs) > 1 else '')
            if a.info:
                print(f"{name} {t['width']}x{t['height']} fmt=0x{t['fmt']:02x} mips={t['mips']} plat=0x{t['platform']:x} ext={t['ext_size']}")
                continue
            try:
                decode(data, t, not a.linear).save(os.path.join(a.out, name + '.png'))
                ok += 1
            except Exception as e:
                bad += 1
    print(f'ok={ok} falhas={bad}', file=sys.stderr)


if __name__ == '__main__':
    main()


def swizzle(lin, width_el, height_el, bpe):
    """Inverso do deswizzle: linear -> block-linear (com o tiling nativo do Switch 2)."""
    bh = block_height_for(height_el)
    width_bytes = width_el * bpe
    gobs_x = (width_bytes + 63) // 64
    rows = ((height_el + 8 * bh - 1) // (8 * bh)) * 8 * bh
    need = gobs_x * 64 * rows
    y, xb = np.mgrid[0:height_el, 0:width_bytes]
    gob = ((y // (8 * bh)) * 512 * bh * gobs_x + (xb // 64) * 512 * bh + ((y % (8 * bh)) // 8) * 512)
    addr = gob + ((xb % 64) // 32) * 256 + ((y % 8) // 2) * 64 + ((xb % 32) // 16) * 32 + (y % 2) * 16 + (xb % 16)
    if NATIVE_TILING:
        diff = ((addr >> 5) ^ (addr >> 6)) & 1
        addr = addr ^ (diff << 5) ^ (diff << 6)
    out = np.zeros(need, dtype=np.uint8)
    out[addr.ravel()] = np.frombuffer(lin, dtype=np.uint8)[:addr.size]
    return out.tobytes()


def encode_bc3(im):
    """Codifica RGBA em BC3/DXT5 (blocos em ordem linear) usando o encoder da Pillow."""
    import io
    b = io.BytesIO()
    im.convert('RGBA').save(b, 'DDS', pixel_format='DXT5')
    d = b.getvalue()
    assert d[:4] == b'DDS ', 'DDS inesperado'
    return d[128:]
