#!/usr/bin/env python3
"""Gera o mod de ícones de botão do Pokémon Pokopia para Steam Deck, Xbox ou PlayStation.

Lê os arquivos do SEU jogo (romfs da versão 2.0.1 / 2.0.1a), redesenha os ícones e monta uma pasta de mod
LayeredFS para emuladores da família yuzu/Eden/Eglantine. Opcionalmente usa o mod de tradução PT-BR como base,
para os dois funcionarem juntos (eles mexem nos mesmos arquivos).

uso:
  build_mod.py --game <romfs do jogo> --variant steamdeck|xbox|playstation|all --out <pasta>
               [--base "<pasta do mod PT-BR>"] [--font <fonte .ttf negrito>]
"""
import argparse, glob, os, shutil, struct, sys, zlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image
import g1t_decode as g, glyphs, kt_rdb, kt_scan

KIDS = os.path.join('motor_asset_re', 'KIDS_PLATFORM_OUNCE')
UI_FDATA = '0x00011c54.fdata'          # pacote da interface (índice 0 no root.rdx)
TARGET_FDATA, TARGET_INDEX = '0x4b13d561.fdata', 0x10  # pacote pequeno onde as texturas novas são anexadas
ATLAS_KTID, ATLAS_TEX = 0xbc2c37f5, 18  # atlas dos ícones de botão
TITLE_KTID = 0x79c6dd0e                 # tela de título em inglês ("PRESS Ⓐ BUTTON"; o PT-BR traduz esta)
NAMES = {'steamdeck': 'Steam Deck', 'xbox': 'Xbox', 'playstation': 'PlayStation'}
FONTS = ['/usr/share/fonts/noto/NotoSans-Bold.ttf', '/usr/local/share/fonts/noto/NotoSans-Bold.ttf',
         '/usr/share/fonts/TTF/DejaVuSans-Bold.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
         'C:/Windows/Fonts/arialbd.ttf', '/Library/Fonts/Arial Bold.ttf']


def entry_of(fdata, ktid):
    for e in kt_scan.entries(fdata):
        if e['ktid'] == ktid:
            return e
    raise SystemExit(f'{ktid:08x} não encontrado em {fdata} (versão do jogo diferente de 2.0.1?)')


def read_by_rdb(kids_dir, ktid):
    """Lê um arquivo seguindo o root.rdb (serve para o jogo original e para mods como o PT-BR)."""
    _, ents, _ = kt_rdb.read(os.path.join(kids_dir, 'root.rdb'))
    off, size, idx = struct.unpack_from('<IIH', ents[ktid]['loc'], 2)
    name = {0: UI_FDATA, TARGET_INDEX: TARGET_FDATA}.get(idx)
    if name is None:
        raise SystemExit(f'{ktid:08x} está num pacote inesperado ({idx})')
    path = os.path.join(kids_dir, name)
    e = next(x for x in kt_scan.entries(path) if x['offset'] == off)
    return kt_scan.read_data(path, e)


def encode_into(g1t_bytes, tex_index, img):
    """Grava a imagem (BC3 + swizzle do Switch 2) no lugar da textura e confere decodificando de volta."""
    data = bytearray(g1t_bytes)
    t = g.parse(bytes(data))[tex_index]
    assert t['fmt'] in (0x62, 0x66) and img.size == (t['width'], t['height']), t
    sw = g.swizzle(g.encode_bc3(img), t['width'] // 4, t['height'] // 4, 16)
    assert len(sw) <= t['data_end'] - t['data_off']
    data[t['data_off']:t['data_off'] + len(sw)] = sw
    data[t['header'] + 1] = 0x62  # BC3 tem o mesmo tamanho por bloco do BC7
    back = g.decode(bytes(data), g.parse(bytes(data))[tex_index]).convert('RGBA')
    err = np.abs(np.asarray(back, np.int16) - np.asarray(img.convert('RGBA'), np.int16)).mean()
    assert err < 6, f'conferência falhou (erro {err:.1f})'
    return bytes(data)


def append_and_redirect(kids_out, ktid, new_data, params, entry):
    fpath = os.path.join(kids_out, TARGET_FDATA)
    rpath = os.path.join(kids_out, 'root.rdb')
    params = struct.pack('<I', zlib.crc32(new_data)) + params[4:]  # 1º parâmetro = CRC32 dos dados
    with open(fpath, 'r+b') as f:
        f.seek(0, 2); end = f.tell(); pad = (0x10 - end % 0x10) % 0x10
        f.write(b'\0' * pad); offset = end + pad
        size = 0x30 + len(params) + len(new_data)
        f.write(b'IDRK0000' + struct.pack('<QQQIIII', size, len(new_data), len(new_data), entry['entry_type'], ktid,
                                          entry['type_ktid'], 0) + params + new_data)
    rdb, ents, _ = kt_rdb.read(rpath)
    r = ents[ktid]; rdb = bytearray(rdb)
    assert r['file_size'] == len(new_data)
    struct.pack_into('<I', rdb, r['pos'] + 0x2c, r['flags'] & ~0x400000)  # sem o bit de "comprimido"
    loc = r['pos'] + r['entry_size'] - r['loc_size']
    rdb[loc:loc + 13] = bytes([0x01, 0x04]) + struct.pack('<IIH', offset, size, TARGET_INDEX) + b'\0'
    open(rpath, 'wb').write(rdb)
    assert read_by_rdb(kids_out, ktid) == new_data  # conferência ponta a ponta


def build(game, base, variant, out_root, font):
    game_kids = os.path.join(game, KIDS)
    name = f'Botoes {NAMES[variant]}' + (' + PT-BR' if base else '')
    out = os.path.join(out_root, name)
    if os.path.exists(out):
        shutil.rmtree(out)
    if base:
        shutil.copytree(base, out)
    else:
        os.makedirs(os.path.join(out, 'romfs', KIDS))
        for f in ('root.rdb', TARGET_FDATA):
            shutil.copy2(os.path.join(game_kids, f), os.path.join(out, 'romfs', KIDS, f))
    kids_out = os.path.join(out, 'romfs', KIDS)
    src_kids = os.path.join(base, 'romfs', KIDS) if base else game_kids
    ui = os.path.join(game_kids, UI_FDATA)

    # atlas dos ícones
    atlas = kt_scan.read_data(ui, entry_of(ui, ATLAS_KTID))
    t = g.parse(atlas)[ATLAS_TEX]
    if (t['width'], t['height']) != (1024, 1024):
        raise SystemExit('atlas inesperado: confira se o jogo é a versão 2.0.1')
    im = g.decode(atlas, t).convert('RGBA')
    new_atlas = encode_into(atlas, ATLAS_TEX, glyphs.remap_atlas(im, variant, font))
    e = entry_of(ui, ATLAS_KTID)
    with open(ui, 'rb') as f:
        f.seek(e['offset'] + 0x30); params = f.read(e['entry_size'] - e['comp_size'] - 0x30)
    append_and_redirect(kids_out, ATLAS_KTID, new_atlas, params, e)

    # tela de título (a do base, se houver: o PT-BR traduz esta textura)
    title = read_by_rdb(src_kids, TITLE_KTID)
    tt = g.parse(title)[0]
    new_title = encode_into(title, 0, glyphs.remap_title(g.decode(title, tt).convert('RGBA'), variant, font))
    e = entry_of(ui, TITLE_KTID)
    with open(ui, 'rb') as f:
        f.seek(e['offset'] + 0x30); params = f.read(e['entry_size'] - e['comp_size'] - 0x30)
    append_and_redirect(kids_out, TITLE_KTID, new_title, params, e)
    print(f'ok: {out}')
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--game', required=True, help='pasta romfs do jogo (a que tem motor_asset_re/)')
    ap.add_argument('--variant', default='all', choices=['steamdeck', 'xbox', 'playstation', 'all'])
    ap.add_argument('--out', required=True)
    ap.add_argument('--base', help='pasta do mod PT-BR (a que tem romfs/) para combinar')
    ap.add_argument('--font', help='fonte .ttf em negrito para os rótulos')
    a = ap.parse_args()
    font = a.font or next((f for f in FONTS if os.path.exists(f)), None)
    if not font:
        raise SystemExit('nenhuma fonte negrito encontrada; use --font')
    if not os.path.isdir(os.path.join(a.game, KIDS)):
        raise SystemExit(f'{a.game} não tem {KIDS}: aponte para a pasta romfs do jogo')
    for v in (['steamdeck', 'xbox', 'playstation'] if a.variant == 'all' else [a.variant]):
        build(a.game, a.base, v, a.out, font)


if __name__ == '__main__':
    main()
