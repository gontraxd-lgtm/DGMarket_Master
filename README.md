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

## Catálogo: contexto y especificaciones (gratis)

Cada `1_portada_<nombre>.jpg` tiene al lado dos imágenes más, generadas con `scripts/catalogo.py`:

- **`2_contexto_<nombre>.jpg`**: tu producto real, recortado de la portada y pegado **intacto** sobre una escena acorde, con sombra para que no flote. 1500x1500.
- **`3_specs_<nombre>.jpg`**: lienzo gris claro con el producto real a la izquierda y, a la derecha, título, color/modelos y 3 características. 1500x1500.

Todo es local y **gratis**: no usa IA ni internet, así que el producto nunca se deforma.

| Producto | Escena |
|---|---|
| Cables, cargador 20W, cargador Solma | Escritorio de madera con planta y monitor desenfocados |
| Carcasas de silicona | Estudio cálido con pedestal |
| Carcasas transparentes, micas | Estudio claro con pedestal (el blanco no desentona) |
| Cascos | Sendero de tierra con bosque |
| Lentes | Ruta de montaña |
| Zapatillas | Cancha de futsal |
| Señuelos | Roca a la orilla de un río |
| Linterna frontal | Camping al anochecer |
| Máquinas de corte | Barbería |

- Las escenas se generan por código en `scripts/fondos.py`. Todas las variantes de un producto comparten la misma escena.
- Las características están en `scripts/datos_catalogo.py`, escritas a partir de tus propias infografías (`info…`, `caracteristicas…`, guía de tallas, etiqueta de la caja). El color y los modelos compatibles se leen del nombre de cada archivo. Para cambiar un texto, edítalo ahí y vuelve a generar.

### Regenerar o agregar productos

```powershell
cd C:\Users\pc\DGMarket_Master
pip install -r requirements.txt
python scripts/catalogo.py                    # solo crea las que faltan
python scripts/catalogo.py images/deportes    # solo una carpeta
```

- Si `2_…` o `3_…` ya existen, se saltan. Para rehacer una, bórrala y vuelve a correr.
- Para un producto nuevo, agrega su carpeta en `PRODUCTOS` (escena, título y 3 características) dentro de `scripts/datos_catalogo.py`.

### Opcional: con OpenAI (pagado)

Si algún día quieres fondos fotográficos generados por IA, `python scripts/catalogo.py --openai` usa DALL-E 3 para el fondo y la API de texto para las características. El producto se sigue pegando intacto. Requiere tu clave en `.env` (copia `.env.example`) y tiene costo, cerca de US$0,04 por fondo. En ese modo, si se corta internet, espera y reintenta sin detenerse.

### Limitaciones

- Las carcasas transparentes y las micas se ven con el interior blanco. La portada tiene fondo blanco y no se puede saber qué había detrás del plástico.
- Las escenas son ilustraciones por código, no fotos reales: están desenfocadas a propósito para que el producto sea el protagonista.
