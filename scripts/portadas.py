#!/usr/bin/env python3
"""Genera portadas de producto: fondo blanco puro, 1500x1500 px, JPG <= 140 KB.

Recorre images/ y, por cada imagen:
  1. Si ya es cuadrada, de 1500x1500, con fondo blanco puro (255,255,255) y
     pesa <= 140 KB, la deja intacta.
  2. Si no, quita el fondo: si ya es blanco o casi blanco lo lleva a blanco puro
     sin tocar el producto (así no se pierden vidrios ni transparencias); si es
     otro fondo usa rembg (o la transparencia que ya traiga el PNG),
  3. centra el producto en un lienzo blanco de 1500x1500,
  4. guarda un JPG <= 140 KB como 1_portada_<nombre>.jpg en la misma carpeta.

Las infografías, guías, banners y escenas se omiten porque no tienen un producto
único que recortar: por nombre (info, caracteristicas, guia...) y por la lista
scripts/portadas_excluir.txt. Usa --todas para incluirlas.

Uso:
    pip install -r requirements.txt
    python scripts/portadas.py [--todas] [--forzar] [ruta ...]
"""
import argparse
import csv
import io
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageOps
from scipy import ndimage

ROOT = Path(__file__).resolve().parent.parent
IMAGES = ROOT / "images"
REPORT = ROOT / "portadas_reporte.csv"
EXCLUIR = ROOT / "scripts" / "portadas_excluir.txt"

SIZE = 1500
MAX_BYTES = 140 * 1024
MARGIN = 0.06  # 6% de aire por lado
BORDER = 10  # px del borde que deben ser blanco puro para considerar el fondo blanco
CLARO = 235  # un fondo con el borde >= este valor se trata como "ya blanco"
TOLERANCIA = 18  # distancia al color del fondo que se rellena a 255 en fondos claros
EXTS = {".jpg", ".jpeg", ".png", ".webp"}
PREFIX = "1_portada_"
NO_PRODUCT = re.compile(
    r"(^|-)(info|informacion|caracteristicas|guia|instrucciones|publi|modelos|"
    r"proteccion|banner|tallas|luces|mas)(-|$)"
)


def cumple(path: Path, img: Image.Image) -> bool:
    if img.size != (SIZE, SIZE) or path.stat().st_size > MAX_BYTES:
        return False
    return all(p == (255, 255, 255) for p in borde(img.convert("RGB")))


def borde(img: Image.Image) -> list:
    w, h = img.size
    px = []
    for box in ((0, 0, w, BORDER), (0, h - BORDER, w, h), (0, 0, BORDER, h), (w - BORDER, 0, w, h)):
        px += list(img.crop(box).getdata())
    return px


def fondo_claro(rgb: Image.Image) -> bool:
    px = borde(rgb)
    return sum(min(p) >= CLARO for p in px) >= 0.98 * len(px)


def recortar_fondo_claro(rgb: Image.Image) -> Image.Image | None:
    """Fondo casi blanco: lo lleva a blanco puro sin tocar el producto (sirve para vidrio y transparentes)."""
    # se rellena desde el color real del fondo (puede ser gris muy claro), no desde el blanco
    px = borde(rgb)
    fondo = tuple(sorted(c[i] for c in px)[len(px) // 2] for i in range(3))
    img = ImageOps.expand(rgb, border=2, fill=fondo)
    ImageDraw.floodfill(img, (0, 0), (255, 255, 255), thresh=TOLERANCIA)
    mask = img.convert("L").point(lambda v: 255 if v < 255 else 0)
    # el relleno deja 255 exacto en el fondo; lo que no es 255 es producto
    bbox = mask.getbbox()
    if not bbox:
        return None
    return img.crop(bbox).convert("RGBA")


def recortar(img: Image.Image, session) -> Image.Image | None:
    """Devuelve el producto en RGBA recortado a su contorno, o None si no se detecta."""
    from rembg import remove

    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        rgba = img.convert("RGBA")
        if rgba.getchannel("A").getextrema()[0] < 128:  # ya trae el fondo transparente
            return _ajustar(rgba)
        rgb = Image.alpha_composite(Image.new("RGBA", rgba.size, (255, 255, 255, 255)), rgba).convert("RGB")
    else:
        rgb = img.convert("RGB")
    if fondo_claro(rgb):
        return recortar_fondo_claro(rgb)
    return _ajustar(remove(rgb, session=session, post_process_mask=True))


def _ajustar(cut: Image.Image) -> Image.Image | None:
    """Borra restos sueltos (letras, motas) que rembg deja lejos del producto y recorta."""
    alpha = np.array(cut.getchannel("A"))
    labels, n = ndimage.label(alpha > 24)
    if n == 0:
        return None
    areas = ndimage.sum_labels(np.ones_like(labels), labels, range(1, n + 1))
    keep = np.isin(labels, 1 + np.flatnonzero(areas >= 0.02 * areas.max()))
    alpha[~ndimage.binary_dilation(keep, iterations=3)] = 0
    cut.putalpha(Image.fromarray(alpha))
    return cut.crop(Image.fromarray(np.where(keep, 255, 0).astype(np.uint8)).getbbox())


def componer(product: Image.Image) -> Image.Image:
    inner = round(SIZE * (1 - 2 * MARGIN))
    scale = min(inner / product.width, inner / product.height)
    size = (max(1, round(product.width * scale)), max(1, round(product.height * scale)))
    product = product.resize(size, Image.LANCZOS)
    canvas = Image.new("RGB", (SIZE, SIZE), (255, 255, 255))
    canvas.paste(product, ((SIZE - size[0]) // 2, (SIZE - size[1]) // 2), product)
    return canvas


def guardar_jpg(img: Image.Image, dest: Path) -> tuple[int, int]:
    for quality in range(92, 29, -4):
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=quality, optimize=True, progressive=True, subsampling=2)
        if buf.tell() <= MAX_BYTES:
            break
    dest.write_bytes(buf.getvalue())
    return buf.tell(), quality


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("rutas", nargs="*", type=Path, default=[IMAGES], help="carpetas o imágenes (por defecto images/)")
    ap.add_argument("--todas", action="store_true", help="procesar también infografías, guías y banners")
    ap.add_argument("--forzar", action="store_true", help="regenerar portadas que ya existen")
    ap.add_argument("--modelo", default="isnet-general-use", help="modelo de rembg")
    args = ap.parse_args()

    files = []
    for r in args.rutas:
        files += sorted(p for p in r.rglob("*") if p.is_file()) if r.is_dir() else [r]
    files = [p for p in files if p.suffix.lower() in EXTS and not p.name.startswith(PREFIX)]

    def destino(path: Path) -> Path:
        # fire-tiger.jpg y fire-tiger.png no pueden compartir portada
        gemelos = [q for q in path.parent.iterdir() if q.stem == path.stem and q.suffix.lower() in EXTS]
        nombre = path.stem if len(gemelos) == 1 else f"{path.stem}-{path.suffix.lower().lstrip('.')}"
        return path.with_name(f"{PREFIX}{nombre}.jpg")

    from rembg import new_session

    excluir = set()
    if EXCLUIR.exists():
        excluir = {l.strip() for l in EXCLUIR.read_text().splitlines() if l.strip() and not l.startswith("#")}

    session = new_session(args.modelo)
    rows, counts = [], {}
    for i, path in enumerate(files, 1):
        rel = path.resolve().relative_to(ROOT).as_posix()
        dest = destino(path)
        kb = quality = ""
        with Image.open(path) as im:
            img = ImageOps.exif_transpose(im)
            img.load()
        if cumple(path, img):
            status = "cumple (intacta)"
        elif not args.todas and ("marca" in path.parts or NO_PRODUCT.search(path.stem.lower())):
            status = "omitida (infografia/banner)"
        elif not args.todas and rel.removeprefix("images/") in excluir:
            status = "omitida (lista de exclusion)"
        elif dest.exists() and not args.forzar:
            status = "ya procesada"
        else:
            product = recortar(img, session)
            if product is None:
                status = "error: no se detecto producto"
            else:
                size, quality = guardar_jpg(componer(product), dest)
                kb = round(size / 1024, 1)
                status = "procesada"
        counts[status] = counts.get(status, 0) + 1
        rows.append((rel, status, dest.resolve().relative_to(ROOT).as_posix() if status == "procesada" else "", kb, quality))
        print(f"[{i}/{len(files)}] {status:28} {rel}", flush=True)

    with REPORT.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["imagen", "estado", "portada", "kb", "calidad_jpg"])
        w.writerows(rows)
    print("\nResumen:")
    for status, n in sorted(counts.items()):
        print(f"  {status:30} {n}")
    return 1 if any(s.startswith("error") for s in counts) else 0


if __name__ == "__main__":
    sys.exit(main())
