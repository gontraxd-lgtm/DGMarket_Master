"""Fondos de escena generados por código (gratis, sin IA).

Cada escena es una pared/fondo desenfocado + una superficie en perspectiva donde
se apoya el producto, con luz, bokeh y grano para que parezca foto. Con la misma
semilla sale siempre el mismo fondo, así todas las variantes de un producto
comparten escena.

    from fondos import generar
    img = generar("escritorio", semilla=123)   # Image RGB 1500x1500
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

SIZE = 1500


# ------------------------------------------------------------------ utilidades

def _ruido(rng, h, w, escala, octavas=4):
    """Ruido suave (value noise) en [0, 1]."""
    total, amp, norm = np.zeros((h, w)), 1.0, 0.0
    for o in range(octavas):
        paso = max(1.0, escala / 2 ** o)
        gh, gw = max(2, int(h / paso)), max(2, int(w / paso))
        capa = Image.fromarray((rng.random((gh, gw)) * 255).astype(np.uint8)).resize((w, h), Image.BILINEAR)
        capa = capa.filter(ImageFilter.GaussianBlur(paso / 2))
        arr = np.asarray(capa, dtype=float)
        arr = (arr - arr.min()) / max(1e-6, arr.max() - arr.min())
        total += arr * amp
        norm += amp
        amp *= 0.5
    return total / norm


def _degradado(h, w, arriba, abajo, curva=1.0):
    t = np.linspace(0, 1, h)[:, None, None] ** curva
    return np.asarray(arriba, float) * (1 - t) + np.asarray(abajo, float) * t * np.ones((1, w, 1))


def _img(arr):
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def _perspectiva(textura: Image.Image, alto_piso: int, cerca: float = 0.45) -> Image.Image:
    """Proyecta una textura plana como piso que se aleja hacia el horizonte.
    Arriba (lejos) se ve la textura completa comprimida; abajo (cerca), solo la
    fracción `cerca` central, ampliada."""
    w, h = textura.size
    # esquinas de la textura que caen en (0,0), (SIZE,0), (SIZE,alto), (0,alto)
    src = [(0, 0), (w, 0), (w * (0.5 + cerca / 2), h), (w * (0.5 - cerca / 2), h)]
    dst = [(0, 0), (SIZE, 0), (SIZE, alto_piso), (0, alto_piso)]
    a, b = [], []
    for (x, y), (u, v) in zip(dst, src):
        a.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        a.append([0, 0, 0, x, y, 1, -v * x, -v * y])
        b += [u, v]
    coef = np.linalg.solve(np.array(a, float), np.array(b, float))
    return textura.transform((SIZE, alto_piso), Image.PERSPECTIVE, tuple(coef), Image.BICUBIC)


def _bokeh(rng, lienzo: Image.Image, n, colores, radio=(12, 45), zona=(0, 1), alfa=(40, 110)):
    capa = Image.new("RGBA", lienzo.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    for _ in range(n):
        r = rng.integers(*radio)
        x = rng.integers(0, SIZE)
        y = rng.integers(int(zona[0] * SIZE), int(zona[1] * SIZE))
        c = colores[rng.integers(len(colores))]
        d.ellipse((x - r, y - r, x + r, y + r), fill=tuple(c) + (int(rng.integers(*alfa)),))
    lienzo.alpha_composite(capa.filter(ImageFilter.GaussianBlur(3)))


def _siluetas(rng, h, w, base, amplitud, escala, color):
    """Cordillera o línea de árboles: silueta rellena bajo una curva de ruido."""
    curva = _ruido(rng, 1, w, escala, 5)[0]
    alturas = base - (curva - 0.5) * 2 * amplitud
    ys = np.arange(h)[:, None]
    mascara = (ys >= alturas[None, :]).astype(np.uint8) * 255
    capa = Image.new("RGBA", (w, h), tuple(color) + (0,))
    capa.putalpha(Image.fromarray(mascara))
    return capa


def _arboles(rng, h, w, base, n, alto, color):
    capa = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    for _ in range(n):
        x = rng.integers(-50, w + 50)
        a = alto * rng.uniform(0.55, 1.35)
        an = a * rng.uniform(0.2, 0.3)
        tono = tuple(int(c * rng.uniform(0.8, 1.2)) for c in color)
        # copa en 3 pisos para que no sea un triángulo plano
        for k in range(3):
            y0 = base - a + k * a * 0.28
            d.polygon([(x, y0), (x - an * (0.6 + 0.2 * k), y0 + a * 0.45), (x + an * (0.6 + 0.2 * k), y0 + a * 0.45)],
                      fill=tono + (255,))
        d.rectangle((x - 6, base - a * 0.1, x + 6, base + 10), fill=tono + (255,))
    return capa


def _terminar(lienzo: Image.Image, horizonte: int, rng, desenfoque=14, grano=5, vineta=0.35) -> Image.Image:
    """Profundidad de campo (fondo borroso, piso cercano nítido), viñeta y grano."""
    rgb = lienzo.convert("RGB")
    borroso = rgb.filter(ImageFilter.GaussianBlur(desenfoque))
    y = np.arange(SIZE)[:, None]
    # nítido cerca de la cámara (abajo), borroso en el fondo y el horizonte
    t = np.clip((y - horizonte) / (SIZE - horizonte) * 1.6, 0, 1) ** 0.8
    arr = np.asarray(borroso, float) * (1 - t[..., None]) + np.asarray(rgb, float) * t[..., None]
    yy, xx = np.mgrid[0:SIZE, 0:SIZE] / SIZE - 0.5
    arr *= (1 - vineta * (xx ** 2 + yy ** 2) * 1.6)[..., None]
    arr += rng.normal(0, grano, arr.shape[:2])[..., None]
    return _img(arr)


def _luz(lienzo: Image.Image, cx, cy, radio, color, fuerza):
    capa = Image.new("RGBA", lienzo.size, (0, 0, 0, 0))
    ImageDraw.Draw(capa).ellipse((cx - radio, cy - radio, cx + radio, cy + radio), fill=tuple(color) + (fuerza,))
    lienzo.alpha_composite(capa.filter(ImageFilter.GaussianBlur(radio // 2)))


# ------------------------------------------------------------------- texturas

def _madera(rng, w, h, base, oscuro, tablas=0, veta=60):
    """Vetas y tablas a lo largo (verticales en la textura = hacia el horizonte)."""
    n = _ruido(rng, h, w, 300, 3)
    n2 = _ruido(rng, h, w, 900, 2)
    x = np.linspace(0, 1, w)[None, :]
    vetas = np.sin((x * veta * (0.8 + n2 * 0.4) + n * 2.5) * np.pi) * 0.5 + 0.5
    fibra = np.asarray(_img(rng.normal(128, 40, (h, w))).resize((w, h // 8)).resize((w, h), Image.BILINEAR), float) / 255
    vetas = vetas ** 4 * 0.3 + _ruido(rng, h, w, 400, 3) * 0.3 + fibra * 0.4
    arr = np.asarray(base, float) * (1 - vetas[..., None]) + np.asarray(oscuro, float) * vetas[..., None]
    if tablas:
        ancho = w / tablas
        tono = rng.uniform(0.9, 1.08, tablas)
        for i in range(tablas):
            x0, x1 = int(i * ancho), int((i + 1) * ancho)
            arr[:, x0:x1] *= tono[i]
            arr[:, max(0, x0 - 2):x0 + 2] *= 0.7
    return _img(arr)


def _marmol(rng, w, h, base, veta, contraste=0.8):
    n = _ruido(rng, h, w, 500, 5)
    xx = np.linspace(0, 1, w)[None, :]
    yy = np.linspace(0, 1, h)[:, None]
    v = np.abs(np.sin((xx * 2 + yy * 3 + n * 4) * np.pi))
    n2 = _ruido(rng, h, w, 180, 4)
    v2 = np.abs(np.sin((xx * 5 - yy * 2 + n2 * 5) * np.pi))
    vetas = (1 - v) ** 7 * contraste * 0.7 + (1 - v2) ** 9 * contraste * 0.35 + (n2 - 0.5) * 0.12
    vetas = np.clip(np.asarray(_img(np.clip(vetas, 0, 1) * 255).filter(ImageFilter.GaussianBlur(5)), float) / 255, 0, 1)
    arr = np.asarray(base, float) * (1 - vetas[..., None]) + np.asarray(veta, float) * vetas[..., None]
    arr *= (0.93 + _ruido(rng, h, w, 250, 3) * 0.14)[..., None]
    return _img(arr)


def _podio(lienzo: Image.Image, cx, top_y, ancho, alto, color):
    """Pedestal cilíndrico de estudio con sombreado lateral."""
    rx, ry = ancho // 2, max(18, ancho // 9)
    luz = 0.78 + 0.3 * np.sin(np.linspace(0.1, np.pi - 0.1, ancho)) ** 0.6
    cuerpo = np.asarray(color, float)[None, None, :] * luz[None, :, None] * np.ones((alto, 1, 1))
    mascara = Image.new("L", (ancho, alto + ry), 0)
    dm = ImageDraw.Draw(mascara)
    dm.rectangle((0, 0, ancho, alto), fill=255)
    dm.ellipse((0, alto - ry, ancho, alto + ry), fill=255)
    cuerpo = np.concatenate([cuerpo, np.repeat(cuerpo[-1:], ry, axis=0)])
    pieza = _img(cuerpo).convert("RGBA")
    pieza.putalpha(mascara)
    sombra = Image.new("RGBA", lienzo.size, (0, 0, 0, 0))
    ImageDraw.Draw(sombra).ellipse((cx - rx - 30, top_y + alto - ry, cx + rx + 70, top_y + alto + ry * 2),
                                   fill=(0, 0, 0, 90))
    lienzo.alpha_composite(sombra.filter(ImageFilter.GaussianBlur(30)))
    lienzo.alpha_composite(pieza, (cx - rx, top_y))
    tapa = Image.new("RGBA", lienzo.size, (0, 0, 0, 0))
    ImageDraw.Draw(tapa).ellipse((cx - rx, top_y - ry, cx + rx, top_y + ry),
                                 fill=tuple(min(255, int(v * 1.1)) for v in color) + (255,))
    lienzo.alpha_composite(tapa)


def _piedra(rng, w, h, base, variacion=40):
    n = _ruido(rng, h, w, 90, 5) - 0.5
    fino = rng.normal(0, 1, (h, w))  # grano de detalle: se ve nítido cerca de la cámara
    fino = np.asarray(_img((fino * 40 + 128)).filter(ImageFilter.GaussianBlur(0.8)), float) / 255 - 0.5
    arr = np.asarray(base, float) + (n * variacion * 2 + fino * variacion * 1.2)[..., None]
    return _img(arr)


# --------------------------------------------------------------------- escenas
# El producto se apoya en y = 0.86 * SIZE (ver crear_contexto en catalogo.py).
BASE_Y = int(SIZE * 0.86)


def escritorio(rng):
    horizonte = int(SIZE * 0.5)
    lienzo = _img(_degradado(SIZE, SIZE, (226, 220, 210), (200, 192, 180))).convert("RGBA")
    for i in range(3):  # luz de ventana en la pared
        _luz(lienzo, int(SIZE * (0.7 + 0.1 * i)), int(SIZE * 0.2), 170, (255, 250, 238), 90)
    d = ImageDraw.Draw(lienzo)
    d.rectangle((110, horizonte - 230, 200, horizonte), fill=(236, 234, 230, 255))  # macetero
    for _ in range(18):  # planta
        x, y = rng.integers(40, 280), rng.integers(horizonte - 560, horizonte - 200)
        g = rng.integers(0, 40)
        d.ellipse((x - 45, y - 80, x + 45, y + 80), fill=(50 + g, 95 + g, 58, 255))
    d.rectangle((1180, horizonte - 360, 1500, horizonte - 40), fill=(46, 48, 54, 255))  # monitor
    d.rectangle((1320, horizonte - 40, 1350, horizonte), fill=(90, 92, 98, 255))
    mesa = _madera(rng, SIZE * 2, SIZE, (196, 156, 112), (140, 100, 66), tablas=0, veta=90)
    lienzo.paste(_perspectiva(mesa, SIZE - horizonte, 0.5), (0, horizonte))
    _luz(lienzo, SIZE // 2, int(SIZE * 0.82), 420, (255, 240, 215), 45)
    return _terminar(lienzo, horizonte, rng, desenfoque=26)


def marmol(rng):
    horizonte = int(SIZE * 0.5)
    lienzo = _img(_degradado(SIZE, SIZE, (78, 82, 90), (44, 46, 52))).convert("RGBA")
    _luz(lienzo, int(SIZE * 0.28), int(SIZE * 0.18), 320, (200, 210, 225), 80)
    piso = _marmol(rng, SIZE * 2, SIZE, (54, 56, 60), (178, 178, 182))
    lienzo.paste(_perspectiva(piso, SIZE - horizonte, 0.5), (0, horizonte))
    _luz(lienzo, SIZE // 2, int(SIZE * 0.8), 400, (225, 230, 240), 45)
    return _terminar(lienzo, horizonte, rng, desenfoque=20, vineta=0.45)


def _estudio(rng, pared, piso, podio, sombra_hojas):
    horizonte = int(SIZE * 0.62)
    arriba = tuple(min(255, c + 12) for c in pared)
    lienzo = _img(_degradado(SIZE, SIZE, arriba, pared)).convert("RGBA")
    lienzo.paste(_img(_degradado(SIZE - horizonte, SIZE, piso, tuple(min(255, c + 14) for c in piso))), (0, horizonte))
    _luz(lienzo, int(SIZE * 0.5), int(SIZE * 0.45), 560, (255, 250, 245), 90)
    capa = Image.new("RGBA", lienzo.size, (0, 0, 0, 0))  # sombra de hojas en la pared
    d = ImageDraw.Draw(capa)
    for i in range(8):
        a = 0.35 + i * 0.16
        d.line([(1500, 0), (1500 - 620 * np.cos(a), 620 * np.sin(a))], fill=sombra_hojas + (70,), width=48)
    lienzo.alpha_composite(capa.filter(ImageFilter.GaussianBlur(26)))
    _podio(lienzo, SIZE // 2, BASE_Y, 1080, SIZE - BASE_Y + 40, podio)
    return _terminar(lienzo, horizonte, rng, desenfoque=6, grano=3, vineta=0.25)


def estudio(rng):
    """Estudio cálido (arena) con pedestal: para productos oscuros o de color."""
    return _estudio(rng, (228, 204, 184), (214, 188, 166), (214, 186, 162), (150, 110, 90))


def estudio_frio(rng):
    """Estudio claro gris azulado con pedestal: para productos transparentes o blancos."""
    return _estudio(rng, (206, 214, 224), (192, 200, 212), (178, 188, 202), (110, 120, 140))


def sendero(rng):
    horizonte = int(SIZE * 0.55)
    lienzo = _img(_degradado(SIZE, SIZE, (118, 168, 220), (238, 226, 200), curva=0.8)).convert("RGBA")
    _luz(lienzo, int(SIZE * 0.8), int(SIZE * 0.22), 280, (255, 236, 185), 150)  # sol de tarde
    lienzo.alpha_composite(_siluetas(rng, SIZE, SIZE, horizonte - 260, 120, 700, (128, 146, 168)))
    lienzo.alpha_composite(_arboles(rng, SIZE, SIZE, horizonte - 40, 45, 300, (70, 104, 88)))
    lienzo.alpha_composite(_arboles(rng, SIZE, SIZE, horizonte + 20, 30, 460, (36, 64, 44)))
    tierra = np.asarray(_piedra(rng, SIZE * 2, SIZE, (134, 106, 80), 30), float)
    tierra *= (0.85 + _ruido(rng, SIZE, SIZE * 2, 300, 3) * 0.3)[..., None]
    lienzo.paste(_perspectiva(_img(tierra), SIZE - horizonte, 0.4), (0, horizonte))
    _luz(lienzo, SIZE // 2, int(SIZE * 0.84), 450, (255, 225, 170), 45)
    return _terminar(lienzo, horizonte, rng, desenfoque=26)


def ruta(rng):
    horizonte = int(SIZE * 0.55)
    lienzo = _img(_degradado(SIZE, SIZE, (88, 148, 214), (214, 226, 236), curva=0.9)).convert("RGBA")
    lienzo.alpha_composite(_siluetas(rng, SIZE, SIZE, horizonte - 320, 190, 900, (152, 166, 186)))
    lienzo.alpha_composite(_siluetas(rng, SIZE, SIZE, horizonte - 150, 90, 500, (96, 116, 116)))
    lienzo.alpha_composite(_arboles(rng, SIZE, SIZE, horizonte + 10, 30, 280, (42, 72, 52)))
    asfalto = np.asarray(_piedra(rng, SIZE * 2, SIZE, (96, 96, 100), 16), float)
    asfalto[:, int(SIZE * 1.62):int(SIZE * 1.66)] = (228, 208, 112)  # línea amarilla
    lienzo.paste(_perspectiva(_img(asfalto), SIZE - horizonte, 0.4), (0, horizonte))
    _luz(lienzo, SIZE // 2, int(SIZE * 0.82), 420, (255, 245, 225), 40)
    return _terminar(lienzo, horizonte, rng, desenfoque=26)


def cancha(rng):
    horizonte = int(SIZE * 0.5)
    lienzo = _img(_degradado(SIZE, SIZE, (26, 32, 50), (62, 68, 86))).convert("RGBA")
    _bokeh(rng, lienzo, 70, [(255, 240, 200), (255, 255, 255), (200, 220, 255)], (12, 44), (0.04, 0.32), (60, 160))
    d = ImageDraw.Draw(lienzo)
    d.rectangle((0, horizonte - 150, SIZE, horizonte), fill=(28, 88, 168, 255))  # panel publicitario
    piso = np.asarray(_madera(rng, SIZE * 2, SIZE, (216, 172, 120), (190, 140, 92), tablas=40, veta=200), float)
    piso[int(SIZE * 0.28):int(SIZE * 0.31)] = (246, 246, 246)  # línea de la cancha
    lienzo.paste(_perspectiva(_img(piso), SIZE - horizonte, 0.4), (0, horizonte))
    _luz(lienzo, SIZE // 2, int(SIZE * 0.8), 480, (255, 240, 210), 60)
    return _terminar(lienzo, horizonte, rng, desenfoque=22)


def rio(rng):
    horizonte = int(SIZE * 0.56)
    lienzo = _img(_degradado(SIZE, SIZE, (156, 194, 218), (80, 128, 138))).convert("RGBA")
    lienzo.alpha_composite(_siluetas(rng, SIZE, SIZE, horizonte - 340, 90, 600, (66, 104, 76)))
    lienzo.alpha_composite(_arboles(rng, SIZE, SIZE, horizonte - 230, 60, 300, (32, 66, 46)))
    lienzo.paste(_img(_degradado(230, SIZE, (96, 146, 156), (56, 100, 114))), (0, horizonte - 230))
    _bokeh(rng, lienzo, 110, [(232, 246, 255), (255, 255, 242)], (6, 24), (0.41, 0.56), (70, 180))
    roca = np.asarray(_piedra(rng, SIZE * 2, SIZE, (108, 110, 108), 34), float)
    roca *= (0.85 + _ruido(rng, SIZE, SIZE * 2, 260, 3) * 0.3)[..., None]
    lienzo.paste(_perspectiva(_img(roca), SIZE - horizonte, 0.45), (0, horizonte))
    _luz(lienzo, SIZE // 2, int(SIZE * 0.82), 420, (255, 250, 235), 50)
    return _terminar(lienzo, horizonte, rng, desenfoque=26)


def camping(rng):
    horizonte = int(SIZE * 0.56)
    lienzo = _img(_degradado(SIZE, SIZE, (36, 34, 78), (216, 122, 92), curva=1.4)).convert("RGBA")
    _bokeh(rng, lienzo, 50, [(255, 255, 255)], (2, 5), (0.02, 0.3), (120, 220))  # estrellas
    lienzo.alpha_composite(_siluetas(rng, SIZE, SIZE, horizonte - 210, 120, 800, (54, 42, 72)))
    lienzo.alpha_composite(_arboles(rng, SIZE, SIZE, horizonte + 20, 50, 520, (16, 20, 30)))
    _luz(lienzo, int(SIZE * 0.82), horizonte - 30, 170, (255, 170, 80), 170)  # fogata a lo lejos
    _bokeh(rng, lienzo, 30, [(255, 190, 90), (255, 150, 60)], (10, 30), (0.4, 0.56), (70, 160))
    tierra = _piedra(rng, SIZE * 2, SIZE, (62, 50, 46), 20)
    lienzo.paste(_perspectiva(tierra, SIZE - horizonte, 0.45), (0, horizonte))
    _luz(lienzo, SIZE // 2, int(SIZE * 0.82), 460, (255, 200, 140), 60)
    return _terminar(lienzo, horizonte, rng, desenfoque=24, vineta=0.5)


def barberia(rng):
    horizonte = int(SIZE * 0.52)
    lienzo = _img(_degradado(SIZE, SIZE, (44, 36, 30), (24, 20, 20))).convert("RGBA")
    d = ImageDraw.Draw(lienzo)
    for x in (180, 520, 980, 1320):  # repisas con luz cálida
        d.rectangle((x - 120, 200, x + 120, 214), fill=(255, 200, 130, 255))
        d.rectangle((x - 120, 480, x + 120, 494), fill=(255, 200, 130, 255))
    _bokeh(rng, lienzo, 50, [(255, 200, 120), (255, 170, 90), (255, 230, 180)], (20, 60), (0.08, 0.45), (50, 130))
    piso = _marmol(rng, SIZE * 2, SIZE, (32, 32, 34), (120, 112, 104), 0.4)
    lienzo.paste(_perspectiva(piso, SIZE - horizonte, 0.5), (0, horizonte))
    _luz(lienzo, SIZE // 2, int(SIZE * 0.8), 440, (255, 215, 160), 60)
    return _terminar(lienzo, horizonte, rng, desenfoque=24, vineta=0.5)


ESCENAS = {f.__name__: f for f in (escritorio, marmol, estudio, estudio_frio, sendero, ruta, cancha, rio, camping, barberia)}


def generar(escena: str, semilla: int = 0) -> Image.Image:
    return ESCENAS[escena](np.random.default_rng(semilla))
