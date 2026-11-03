"""Desenho dos ícones de botão por plataforma, no estilo dos ícones originais do Pokopia."""
import numpy as np
from PIL import Image, ImageDraw, ImageFont

SS = 4  # supersampling para bordas suaves

# Caixas (x0, y0, x1, y1) dos ícones na textura 18 do atlas bc2c37f5 (1024x1024).
BOXES = {
    'A': (249, 345, 314, 410), 'B': (937, 417, 1002, 482), 'Y': (9, 609, 74, 674), 'X': (713, 605, 778, 670),
    'PLUS': (9, 521, 74, 586), 'MINUS': (777, 517, 842, 582), 'ZL': (95, 612, 164, 671), 'ZR': (183, 612, 252, 671),
    'L': (271, 520, 340, 579), 'R': (535, 524, 604, 583), 'LS_PRESS': (97, 513, 162, 586),
    'RS_PRESS': (185, 513, 250, 586), 'LSTICK': (449, 517, 514, 582), 'RSTICK': (865, 593, 930, 658),
}

# O emulador mapeia o controle por posição: o botão do Switch na direita (A) é o da direita do controle.
# Cada variante diz o que mostrar no lugar de cada ícone do Switch.
VARIANTS = {
    'steamdeck': {'A': 'B', 'B': 'A', 'X': 'Y', 'Y': 'X', 'L': 'L1', 'R': 'R1', 'ZL': 'L2', 'ZR': 'R2',
                  'PLUS': 'MENU', 'MINUS': 'VIEW', 'LS_PRESS': 'L3', 'RS_PRESS': 'R3'},
    'xbox': {'A': 'B', 'B': 'A', 'X': 'Y', 'Y': 'X', 'L': 'LB', 'R': 'RB', 'ZL': 'LT', 'ZR': 'RT',
             'PLUS': 'MENU', 'MINUS': 'VIEW', 'LS_PRESS': 'LS', 'RS_PRESS': 'RS'},
    'playstation': {'A': 'CIRCLE', 'B': 'CROSS', 'X': 'TRIANGLE', 'Y': 'SQUARE', 'L': 'L1', 'R': 'R1',
                    'ZL': 'L2', 'ZR': 'R2', 'PLUS': 'MENU', 'MINUS': 'CREATE', 'LS_PRESS': 'L3', 'RS_PRESS': 'R3'},
}
SYMBOLS = {'MENU', 'VIEW', 'CROSS', 'CIRCLE', 'SQUARE', 'TRIANGLE', 'CREATE'}


def colors(t):
    a = np.asarray(t.convert('RGBA')).reshape(-1, 4)
    op = a[a[:, 3] > 200][:, :3]
    lum = op.mean(1)
    fill = tuple(int(v) for v in np.median(op[lum > 200], 0)) if (lum > 200).any() else (255, 255, 255)
    ink = tuple(int(v) for v in np.median(op[lum < 90], 0)) if (lum < 90).any() else (40, 40, 40)
    return fill, ink


def draw_symbol(d, name, cx, cy, r, ink):
    """Símbolos desenhados (sem depender de fonte): ☰ ⧉ ✕ ○ □ △ e o Create do PS5."""
    lw = max(2, int(r * 0.17))
    c = ink + (255,)
    if name == 'MENU':
        for k in (-1, 0, 1):
            y = cy + k * r * 0.36
            d.rounded_rectangle((cx - r * 0.5, y - lw / 2, cx + r * 0.5, y + lw / 2), radius=lw // 2, fill=c)
    elif name == 'VIEW':
        s = r * 0.78
        d.rounded_rectangle((cx - s * 0.75, cy - s * 0.75, cx + s * 0.35, cy + s * 0.35), radius=lw // 2, outline=c, width=lw)
        d.rounded_rectangle((cx - s * 0.35, cy - s * 0.35, cx + s * 0.75, cy + s * 0.75), radius=lw // 2, fill=c)
    elif name == 'CROSS':
        s = r * 0.52
        d.line((cx - s, cy - s, cx + s, cy + s), fill=c, width=lw); d.line((cx - s, cy + s, cx + s, cy - s), fill=c, width=lw)
    elif name == 'CIRCLE':
        s = r * 0.55
        d.ellipse((cx - s, cy - s, cx + s, cy + s), outline=c, width=lw)
    elif name == 'SQUARE':
        s = r * 0.5
        d.rectangle((cx - s, cy - s, cx + s, cy + s), outline=c, width=lw)
    elif name == 'TRIANGLE':
        s = r * 0.62
        pts = [(cx, cy - s), (cx + s * 0.87, cy + s * 0.5), (cx - s * 0.87, cy + s * 0.5)]
        d.line(pts + [pts[0], pts[1]], fill=c, width=lw, joint='curve')
    elif name == 'CREATE':  # ícone do Create do PS5: três traços em leque saindo de baixo
        ox, oy = cx, cy + r * 0.5
        for ang in (-38, 0, 38):
            t = np.radians(ang - 90)
            x0, y0 = ox + np.cos(t) * r * 0.32, oy + np.sin(t) * r * 0.32
            x1, y1 = ox + np.cos(t) * r * 0.98, oy + np.sin(t) * r * 0.98
            d.line((x0, y0, x1, y1), fill=c, width=int(lw * 1.2))
            d.ellipse((x1 - lw * 0.6, y1 - lw * 0.6, x1 + lw * 0.6, y1 + lw * 0.6), fill=c)
            d.ellipse((x0 - lw * 0.6, y0 - lw * 0.6, x0 + lw * 0.6, y0 + lw * 0.6), fill=c)


def relabel(t, label, shape, inset, ink, font_path):
    fill, _ = colors(t)
    w, h = t.size
    big = t.resize((w * SS, h * SS), Image.LANCZOS)
    d = ImageDraw.Draw(big)
    i = inset * SS
    if shape == 'circle':
        d.ellipse((i, i, w * SS - i, h * SS - i), fill=fill + (255,))
    else:
        d.rounded_rectangle((i, i, w * SS - i, h * SS - i), radius=6 * SS, fill=fill + (255,))
    if label in SYMBOLS:
        draw_symbol(d, label, w * SS / 2, h * SS / 2, w * SS / 2 - i, ink)
    else:
        box_w, box_h = w * SS - 2 * i - 4 * SS, h * SS - 2 * i - 2 * SS
        size = box_h
        font = ImageFont.truetype(font_path, size)
        while True:
            l, tp, r, b = d.textbbox((0, 0), label, font=font)
            if ((r - l) <= box_w and (b - tp) <= box_h * 0.9) or size < 8:
                break
            size -= SS
            font = ImageFont.truetype(font_path, size)
        l, tp, r, b = d.textbbox((0, 0), label, font=font)
        d.text(((w * SS - (r - l)) / 2 - l, (h * SS - (b - tp)) / 2 - tp), label, font=font, fill=ink + (255,))
    return big.resize((w, h), Image.LANCZOS)


def remap_atlas(im, variant, font_path):
    """Recebe a textura 18 original (RGBA) e devolve a versão com os ícones da plataforma."""
    mapping = VARIANTS[variant]
    new = im.copy()
    tiles = {k: im.crop((b[0], b[1], b[2] + 1, b[3] + 1)) for k, b in BOXES.items()}
    ink = colors(tiles['A'])[1]
    letters = {'A', 'B', 'X', 'Y'}
    for key, label in mapping.items():
        x0, y0 = BOXES[key][:2]
        t = tiles[key]
        if label in letters:  # reaproveita o ícone original da letra (mesmo tamanho de caixa)
            new.paste(tiles[label], (x0, y0))
            continue
        if key in ('LS_PRESS', 'RS_PRESS'):
            base = tiles['LSTICK' if key == 'LS_PRESS' else 'RSTICK']
            lab = relabel(base, label, 'circle', 9, ink, font_path)
            canvas = Image.new('RGBA', t.size, (0, 0, 0, 0))
            canvas.paste(lab, ((t.size[0] - base.size[0]) // 2, t.size[1] - base.size[1]))
        else:
            shape = 'circle' if key in ('A', 'B', 'X', 'Y', 'PLUS', 'MINUS') else 'rect'
            canvas = relabel(t, label, shape, 7, ink, font_path)
        new.paste(Image.new('RGBA', t.size, (0, 0, 0, 0)), (x0, y0))
        new.alpha_composite(canvas, (x0, y0))
    return new


def find_title_glyph(im):
    """Acha o botão desenhado (disco branco) na linha de texto mais baixa da tela de título."""
    a = np.asarray(im)
    op = a[..., 3] > 100
    rows = np.nonzero(op.any(1))[0]
    runs, start, prev = [], rows[0], rows[0]
    for r in rows[1:]:
        if r != prev + 1:
            runs.append((start, prev)); start = r
        prev = r
    runs.append((start, prev))
    y0, y1 = runs[-1]
    cols = np.nonzero(op[y0:y1 + 1].any(0))[0]
    segs, s, p = [], cols[0], cols[0]
    for c in cols[1:]:
        if c > p + 3:
            segs.append((s, p)); s = c
        p = c
    segs.append((s, p))
    best = None
    for x0, x1 in segs:
        cell = a[y0:y1 + 1, x0:x1 + 1]
        w, h = x1 - x0 + 1, y1 - y0 + 1
        white = ((cell[..., :3].min(-1) > 230) & (cell[..., 3] > 200)).mean()
        if abs(w - h) <= 3 and white > 0.45:  # quadrado e majoritariamente branco = o disco do botão
            best = (int(x0), int(y0), int(x1), int(y1))
    if best is None:
        raise ValueError('botão da tela de título não encontrado')
    return best


def remap_title(im, variant, font_path):
    """Troca o Ⓐ desenhado no título pelo botão que confirma na plataforma (o da direita)."""
    label = VARIANTS[variant]['A']
    x0, y0, x1, y1 = find_title_glyph(im)
    cell = im.crop((x0, y0, x1 + 1, y1 + 1))
    w, h = cell.size
    ink = colors(cell)[1]
    big = cell.resize((w * SS * 2, h * SS * 2), Image.LANCZOS)
    d = ImageDraw.Draw(big)
    W, H = big.size
    i = int(W * 0.14)
    d.ellipse((i, i, W - i, H - i), fill=(255, 255, 255, 255))
    if label in SYMBOLS:
        draw_symbol(d, label, W / 2, H / 2, W / 2 - i, ink)
    else:
        font = ImageFont.truetype(font_path, int(H * 0.62))
        l, t, r, b = d.textbbox((0, 0), label, font=font)
        d.text(((W - (r - l)) / 2 - l, (H - (b - t)) / 2 - t), label, font=font, fill=ink + (255,))
    out = im.copy()
    out.paste(big.resize((w, h), Image.LANCZOS), (x0, y0))
    return out
