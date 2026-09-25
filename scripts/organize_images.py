#!/usr/bin/env python3
"""Ordena images/ por categoría y producto, con nombres de archivo uniformes.

Pasa de images/<fuente>/<nombre original> a
images/<categoría>/<producto>/<nombre-normalizado> y actualiza manifest.csv.

Uso:
    python3 scripts/organize_images.py
"""
import csv
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IMAGES = ROOT / "images"
MANIFEST = ROOT / "manifest.csv"

# carpeta de origen -> (categoría, producto)
LAYOUT = {
    "cables-iphone": ("tecnologia", "cables-iphone"),
    "carcasas-silicona-iphone": ("tecnologia", "carcasas-silicona-iphone"),
    "carcasas-transparentes-magsafe-iphone": ("tecnologia", "carcasas-transparentes-magsafe-iphone"),
    "cargador-iphones-20w": ("tecnologia", "cargador-iphone-20w"),
    "crgador-solma-45w": ("tecnologia", "cargador-solma-45w"),
    "micas-de-vidrio-iphone": ("tecnologia", "micas-de-vidrio-iphone"),
    "fotos-cascos": ("deportes", "cascos-trip-enduro"),
    "lentes-ciclismo": ("deportes", "lentes-ciclismo"),
    "zapatillas-joma": ("deportes", "zapatillas-joma"),
    "senuelos-poseidon": ("pesca-y-caza", "senuelos-poseidon"),
    "cintillo-de-cabeza": ("pesca-y-caza", "cintillo-linterna-led"),
    "maquina-de-afeitar-grande": ("cuidado-personal", "maquina-cortar-pelo-grande"),
    "maquina-dorada-de-cortar-pelo": ("cuidado-personal", "maquina-cortar-pelo-dorada"),
    "google-drive": ("marca", "dgmarket"),
}

# nombres puntuales con un nombre más claro
RENAMES = {
    ("google-drive", "image.png"): "banner-dgmarket.png",
    ("maquina-de-afeitar-grande", "MA SINFO.webp"): "mas-info.webp",
}

TYPOS = {
    "iphoen": "iphone",
    "ligthning": "lightning",
    "tranparente": "transparente",
    "prodcuto": "producto",
    "ubs": "usb",
    "por": "pro",
    "intru": "instrucciones",
}


def slugify(stem: str) -> str:
    s = unicodedata.normalize("NFKD", stem).encode("ascii", "ignore").decode().lower()
    words = [TYPOS.get(w, w) for w in re.split(r"[^a-z0-9]+", s) if w]
    return "-".join(words)


def new_name(source: str, product: str, name: str) -> str:
    if (source, name) in RENAMES:
        return RENAMES[(source, name)]
    p = Path(name)
    stem = slugify(p.stem)
    if stem.isdigit():  # "1.jpg" -> "lentes-ciclismo-1.jpg"
        stem = f"{product}-{stem}"
    return f"{stem}{p.suffix.lower().replace('.jpeg', '.jpg')}"


def main():
    moves = {}
    for source, (category, product) in LAYOUT.items():
        src_dir = IMAGES / source
        if not src_dir.is_dir():
            continue
        dest_dir = IMAGES / category / product
        dest_dir.mkdir(parents=True, exist_ok=True)
        for f in sorted(src_dir.iterdir()):
            target = dest_dir / new_name(source, product, f.name)
            i = 2
            while target.exists():
                target = target.with_name(f"{target.stem}-{i}{target.suffix}")
                i += 1
            f.rename(target)
            moves[f.relative_to(ROOT).as_posix()] = target.relative_to(ROOT).as_posix()
        src_dir.rmdir()

    with MANIFEST.open(newline="") as fh:
        rows = list(csv.reader(fh))
    for row in rows[1:]:
        row[3] = moves.get(row[3], row[3])
    with MANIFEST.open("w", newline="") as fh:
        csv.writer(fh).writerows(rows)

    print(f"{len(moves)} imágenes reubicadas")


if __name__ == "__main__":
    main()
