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

## Catálogo con IA: contexto y especificaciones

`scripts/catalogo_ia.py` toma cada `1_portada_<nombre>.jpg` y crea en la misma carpeta:

- **`2_contexto_<nombre>.jpg`**: OpenAI (DALL-E 3) genera **solo un fondo vacío** acorde al producto (escritorio, sendero, río…). El script recorta tu producto real de la portada y lo pega intacto encima, con sombra para que no flote. 1500x1500.
- **`3_specs_<nombre>.jpg`**: OpenAI (texto) propone 3 características cortas. El script dibuja un lienzo gris claro con el producto real a la izquierda y las características a la derecha. 1500x1500.

La IA nunca dibuja el producto, así que no puede inventarle puertos ni cambiarle colores.

### 1. Instalar (una sola vez)

Necesitas Python 3.10 o superior ([python.org](https://www.python.org/downloads/); al instalar marca **"Add Python to PATH"**). En PowerShell:

```powershell
cd C:\Users\pc\DGMarket_Master
git pull
pip install -r requirements.txt
```

### 2. Configurar tu API key

1. Crea una clave en https://platform.openai.com/api-keys y carga saldo en *Settings → Billing*.
2. En la carpeta del repo, copia el ejemplo y ábrelo:
   ```powershell
   copy .env.example .env
   notepad .env
   ```
3. Reemplaza `sk-pega-aqui-tu-clave` por tu clave, guarda y cierra.

El archivo `.env` está en `.gitignore`: **nunca se sube a GitHub**. No compartas tu clave ni la pegues en el código.

### 3. Ejecutar

```powershell
python scripts/catalogo_ia.py --simular            # prueba gratis, sin API, guarda en _simulacion/
python scripts/catalogo_ia.py --limite 3           # prueba real con 3 productos
python scripts/catalogo_ia.py                      # todo el catálogo
python scripts/catalogo_ia.py images/deportes      # solo una carpeta
```

- Si `2_…` o `3_…` ya existen, se saltan: puedes cortar y volver a correr, y sigue donde quedó.
- Si se corta internet o la API falla, espera (30 s, 1 min, 2 min… hasta 15 min) y reintenta sin detenerse.
- Solo se detiene ante lo que esperar no arregla: clave inválida, sin saldo o modelo no disponible. El mensaje dice qué hacer.
- Lo ya pagado (fondos y textos) queda en `.cache_catalogo/`: si algo falla después, no se vuelve a cobrar.
- Todo queda registrado en `catalogo_ia.log`.
- Costo aproximado: una imagen de DALL-E 3 por producto (cerca de US$0,04 cada una con la tarifa estándar, unos US$7 para las 179 portadas) más el texto, que cuesta muy poco. Revisa los precios vigentes en https://openai.com/api/pricing.
- Si OpenAI retira DALL-E 3, usa otro modelo: `--modelo-imagen gpt-image-1`.

### Limitaciones

- Las carcasas transparentes y las micas se ven con el interior blanco sobre el fondo. La portada tiene fondo blanco y no hay forma de saber qué había detrás del plástico.
- Las escenas se eligen por carpeta de producto (diccionario `ESCENAS` en el script). Puedes editarlas ahí.
- Revisa las características antes de publicar: la IA solo conoce el nombre del producto. Se le pide no inventar cifras, pero puede equivocarse.
