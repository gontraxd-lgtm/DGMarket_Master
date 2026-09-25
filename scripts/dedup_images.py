#!/usr/bin/env python3
"""Consolida imágenes de varias carpetas en una carpeta maestra sin duplicados.

Compara por hash MD5 del contenido (no por nombre), copia una única copia de
cada imagen a la carpeta destino y genera un manifiesto CSV + reporte.

Uso:
    python3 scripts/dedup_images.py --dest images SRC [SRC ...]

Cada SRC puede ser "etiqueta=ruta" para controlar el nombre de la subcarpeta
en destino; si no, se usa el nombre de la carpeta. Las carpetas fuente no se
modifican: los duplicados simplemente no se copian al destino.
"""
import argparse
import csv
import hashlib
import shutil
import sys
from pathlib import Path

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".heic", ".avif", ".tif", ".tiff"}


def md5sum(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def iter_images(root: Path):
    for p in sorted(root.rglob("*")):
        if ".git" in p.parts or not p.is_file():
            continue
        if p.suffix.lower() in IMAGE_EXTS:
            yield p


def parse_source(arg: str):
    if "=" in arg:
        label, path = arg.split("=", 1)
    else:
        path = arg
        label = Path(arg).resolve().name
    return label.strip("-_ ") or "source", Path(path)


def unique_dest(dest: Path) -> Path:
    if not dest.exists():
        return dest
    i = 2
    while True:
        cand = dest.with_name(f"{dest.stem}_{i}{dest.suffix}")
        if not cand.exists():
            return cand
        i += 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sources", nargs="+", help="carpetas fuente (opcional: etiqueta=ruta)")
    ap.add_argument("--dest", required=True, help="carpeta maestra de salida")
    ap.add_argument("--manifest", default=None, help="ruta del CSV (por defecto <dest>/../manifest.csv)")
    args = ap.parse_args()

    dest_root = Path(args.dest)
    dest_root.mkdir(parents=True, exist_ok=True)
    manifest_path = Path(args.manifest) if args.manifest else dest_root.parent / "manifest.csv"

    seen = {}  # md5 -> ruta en destino
    rows = []
    per_source = {}

    for arg in args.sources:
        label, root = parse_source(arg)
        if not root.is_dir():
            sys.exit(f"No existe la carpeta: {root}")
        stats = per_source.setdefault(label, {"total": 0, "unique": 0, "dups": 0})
        for img in iter_images(root):
            digest = md5sum(img)
            stats["total"] += 1
            src_ref = f"{label}/{img.relative_to(root).as_posix()}"
            if digest in seen:
                stats["dups"] += 1
                rows.append((digest, src_ref, "duplicado", seen[digest]))
                continue
            target = unique_dest(dest_root / label / img.name)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(img, target)
            rel = target.relative_to(dest_root.parent).as_posix()
            seen[digest] = rel
            stats["unique"] += 1
            rows.append((digest, src_ref, "unica", rel))

    with manifest_path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["md5", "origen", "estado", "archivo_maestro"])
        w.writerows(rows)

    total = sum(s["total"] for s in per_source.values())
    dups = sum(s["dups"] for s in per_source.values())
    print(f"{'Fuente':45} {'Total':>6} {'Únicas':>7} {'Dupl.':>6}")
    for label, s in per_source.items():
        print(f"{label:45} {s['total']:>6} {s['unique']:>7} {s['dups']:>6}")
    print(f"{'TOTAL':45} {total:>6} {len(seen):>7} {dups:>6}")


if __name__ == "__main__":
    main()
