# DGMarket_Master

Carpeta maestra de imágenes de productos de DG Market, sin duplicados (237 imágenes únicas).

## Estructura

```
images/
├── tecnologia/
│   ├── cables-iphone/                           14
│   ├── carcasas-silicona-iphone/                46
│   ├── carcasas-transparentes-magsafe-iphone/   16
│   ├── cargador-iphone-20w/                      3
│   ├── cargador-solma-45w/                       8
│   └── micas-de-vidrio-iphone/                   9
├── deportes/
│   ├── cascos-trip-enduro/                      27
│   ├── lentes-ciclismo/                         40
│   └── zapatillas-joma/                         11
├── pesca-y-caza/
│   ├── cintillo-linterna-led/                   12
│   └── senuelos-poseidon/                       35
├── cuidado-personal/
│   ├── maquina-cortar-pelo-dorada/               6
│   └── maquina-cortar-pelo-grande/               9
└── marca/
    └── dgmarket/                                 1   (banner)
```

Los nombres de archivo están en minúsculas y con guiones, sin espacios ni comas. `manifest.csv` indica de qué repo y archivo original viene cada imagen. `REPORTE.md` tiene el detalle de la deduplicación.

## Portadas (1500x1500, fondo blanco, JPG <= 140 KB)

Cada producto tiene portadas `1_portada_<nombre>.jpg` junto a sus fotos originales, generadas con `scripts/portadas.py`:

- Si la foto ya tiene fondo blanco o casi blanco, el fondo se lleva a blanco puro sin tocar el producto (así se conservan vidrios y carcasas transparentes). Si tiene otro fondo, se quita con `rembg`.
- El producto se centra en un lienzo blanco de 1500x1500 y se guarda como JPG de 140 KB como máximo.
- Se omiten las infografías, guías, banners y escenas: por nombre y por la lista `scripts/portadas_excluir.txt`.
- `portadas_reporte.csv` indica qué pasó con cada imagen.

Para regenerarlas (en Windows, desde la carpeta del repo):

```powershell
pip install -r requirements.txt
python scripts/portadas.py --forzar
```
