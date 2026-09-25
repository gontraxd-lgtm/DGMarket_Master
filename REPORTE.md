# Reporte de consolidación de imágenes (DGMarket_Master)

Fecha: 2026-09-25 · Método: hash MD5 del contenido (todos los duplicados también se verificaron byte a byte con `cmp`).

## Resumen

| Métrica | Cantidad |
|---|---:|
| Imágenes analizadas | **270** |
| Duplicados descartados | **33** |
| Imágenes únicas en `images/` | **237** |

## Fuentes

- **GitHub**: los 14 repositorios de producto de `gontraxd-lgtm` (`fotos-productos-dgmarket` está vacío).
- **Google Drive**: las imágenes propias de la cuenta. Solo hay una: `image.jpg`, que en realidad es un PNG con el banner de DG Market. Se guardó como `images/google-drive/image.png`. Se excluyeron 4 imágenes que otras personas compartieron contigo y no son de productos: tareas de inglés, una captura de Word y `cadena.png`.
- Se excluyó `cintillo-de-cabeza/cintillo_led_ficha.pdf` porque no es una imagen.

| Fuente | Total | Únicas | Duplicadas |
|---|---:|---:|---:|
| cables-iphone | 14 | 14 | 0 |
| carcasas-silicona-iphone | 46 | 46 | 0 |
| carcasas-transparentes-magsafe-iphone | 19 | 16 | 3 |
| cargador-iphones-20w | 13 | 3 | 10 |
| cintillo-de-cabeza | 12 | 12 | 0 |
| crgador-solma-45w | 8 | 8 | 0 |
| fotos-cascos | 27 | 27 | 0 |
| fotos-productos-dgmarket | 0 | 0 | 0 |
| lentes-ciclismo | 40 | 40 | 0 |
| maquina-de-afeitar-grande | 9 | 9 | 0 |
| maquina-dorada-de-cortar-pelo | 6 | 6 | 0 |
| micas-de-vidrio-iphone | 9 | 9 | 0 |
| senuelos-poseidon | 55 | 35 | 20 |
| google-drive | 1 | 1 | 0 |
| **TOTAL** | **270** | **237** | **33** |

## Dónde están los duplicados

- **senuelos-poseidon (20)**: cada foto `…10gr` es idéntica a la versión sin `10gr` (por ejemplo, `Fire Tiger10gr.png` = `Fire Tiger.png`).
- **cargador-iphones-20w (10)**: 9 son copias de fotos de `cables-iphone` y 1 es una copia interna (`KIT-USBC-1_1.jpg`).
- **carcasas-transparentes-magsafe-iphone (3)**: `MAG-12PROMAX.jpg` = `MAG-12.jpg`, la foto de la variante Pro/Pro Max = la de la variante estándar, e `info.webp` = `carcasas-silicona-iphone/info.webp`.

> ⚠️ Revisar: en los señuelos de 10 gr y en las carcasas Pro Max la misma foto se usa para variantes distintas. Si esas variantes deben verse diferentes, faltan sus fotos reales.

## Archivos

- `images/<fuente>/…`: una copia de cada imagen única. Se conserva la primera aparición, recorriendo las fuentes en orden alfabético y Drive al final.
- `manifest.csv`: cada imagen de origen con su MD5, si es única o duplicada, y el archivo maestro que le corresponde.
- `scripts/dedup_images.py`: script para repetir el proceso sobre carpetas locales:

```bash
python3 scripts/dedup_images.py --dest images ruta/repo_github google-drive=ruta/carpeta_drive
```

Los repositorios y el Drive de origen **no se modificaron**. Los duplicados solo se dejaron fuera de la carpeta maestra.
