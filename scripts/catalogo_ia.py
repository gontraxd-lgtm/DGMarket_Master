#!/usr/bin/env python3
"""Arma el catálogo con OpenAI sin deformar los productos reales.

Por cada images/**/1_portada_<nombre>.jpg genera, en la misma carpeta:

  2_contexto_<nombre>.jpg  OpenAI (DALL-E 3) genera SOLO un fondo vacío acorde al
                           producto; el producto real se recorta de la portada y
                           se pega intacto encima con una sombra base. 1500x1500.
  3_specs_<nombre>.jpg     OpenAI (texto) propone 3 características cortas; se
                           dibuja un lienzo gris claro con el producto real a la
                           izquierda y las características a la derecha. 1500x1500.

La IA nunca dibuja el producto: solo el fondo y el texto. Los píxeles del
producto salen tal cual de la portada.

Si un archivo 2_ o 3_ ya existe, se salta. Si la API falla o se corta internet,
espera y reintenta (sin límite) en vez de detenerse. Solo se detiene ante errores
que esperar no arregla: API key inválida, sin saldo o modelo inexistente.

Uso:
    python scripts/catalogo_ia.py                   # todo images/
    python scripts/catalogo_ia.py --limite 3        # prueba con 3 portadas
    python scripts/catalogo_ia.py images/deportes   # solo una carpeta
    python scripts/catalogo_ia.py --simular         # sin API ni costo, en _simulacion/

La API key se lee de la variable de entorno OPENAI_API_KEY o del archivo .env
en la raíz del repo (ver .env.example).
"""
import argparse
import base64
import io
import json
import logging
import os
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent.parent
IMAGES = ROOT / "images"
CACHE = ROOT / ".cache_catalogo"
SIM_DIR = ROOT / "_simulacion"
LOG_FILE = ROOT / "catalogo_ia.log"

SIZE = 1500
GRIS = (238, 238, 238)
ACENTO = (31, 91, 191)  # azul del logo DG Market
TEXTO = (34, 34, 34)
ESPERA_INICIAL = 30  # segundos
ESPERA_MAXIMA = 15 * 60

log = logging.getLogger("catalogo")

# Escenas por producto (carpeta) y, si no hay, por categoría.
# Siempre se pide el centro vacío: ahí va el producto real.
ESCENAS = {
    "cables-iphone": "a clean minimalist white desk setup with a blurred laptop and a small plant at the edges",
    "cargador-iphone-20w": "a clean minimalist white desk setup with a blurred laptop and a small plant at the edges",
    "cargador-solma-45w": "a modern dark wooden desk setup with a blurred monitor in the background",
    "carcasas-silicona-iphone": "a soft pastel studio tabletop with a subtle fabric texture",
    "carcasas-transparentes-magsafe-iphone": "a light marble tabletop with soft natural window light",
    "micas-de-vidrio-iphone": "a light marble tabletop with soft natural window light",
    "cascos-trip-enduro": "a mountain bike trail in a forest at golden hour, a flat rock in the foreground",
    "lentes-ciclismo": "a scenic mountain road for cycling on a sunny day, a flat stone ledge in the foreground",
    "zapatillas-joma": "an indoor futsal court with wooden floor and soft arena lights, blurred background",
    "senuelos-poseidon": "a calm river bank in Patagonia with clear water and a flat wet rock in the foreground",
    "cintillo-linterna-led": "a camping site in a forest at dusk with a blurred tent, a flat log in the foreground",
    "maquina-cortar-pelo-dorada": "a modern barbershop counter with dark marble and warm lights, blurred background",
    "maquina-cortar-pelo-grande": "a modern barbershop counter with dark marble and warm lights, blurred background",
}
# Productos blancos o transparentes: rembg los dañaría, se recortan con relleno.
# El resto usa rembg, que también limpia los huecos (correas, marcos, agujeros).
USAR_RELLENO = {"cables-iphone", "cargador-iphone-20w", "micas-de-vidrio-iphone",
                "carcasas-transparentes-magsafe-iphone"}
ESCENAS_CATEGORIA = {
    "tecnologia": "a clean modern desk setup with soft daylight",
    "deportes": "an outdoor sports environment with soft natural light",
    "pesca-y-caza": "a natural outdoor environment near a lake with soft light",
    "cuidado-personal": "a clean bathroom vanity with marble and soft light",
}
PROMPT_FONDO = (
    "Professional product photography background: {escena}. "
    "The center of the image is completely EMPTY: no objects, no products, no devices, "
    "no people, no hands, no text, no logos. There is a flat surface in the lower center "
    "where a product will be placed later. Photorealistic, shallow depth of field, "
    "soft even lighting, e-commerce style."
)
PROMPT_SPECS = (
    "Eres redactor de fichas de producto para una tienda online chilena. Responde SOLO con JSON "
    'con la forma {"titulo": str, "caracteristicas": [str, str, str]}. '
    "titulo: nombre comercial corto del producto (máximo 5 palabras). "
    "caracteristicas: 3 características técnicas cortas (máximo 6 palabras cada una), "
    "lógicas para este tipo de producto, en español. No inventes cifras, certificaciones "
    "ni compatibilidades que no se deduzcan del nombre; si el nombre trae datos (20W, USB-C, "
    "10 gr, iPhone 15), úsalos."
)


class ErrorFatal(Exception):
    """Error que esperar no arregla: detiene el script."""


class ErrorProducto(Exception):
    """Error que afecta solo a este producto: se salta y se sigue con el siguiente."""


# --------------------------------------------------------------------- utilidades

def humano(slug: str) -> str:
    return slug.replace("-", " ").replace("_", " ").strip()


def guardar_jpg(img: Image.Image, dest: Path, quality: int = 90) -> None:
    """Escribe a un temporal y renombra: un corte a mitad no deja un archivo a medias
    (que la próxima corrida confundiría con uno terminado)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".tmp")
    img.convert("RGB").save(tmp, "JPEG", quality=quality, optimize=True, progressive=True)
    os.replace(tmp, dest)


def fuente(peso: str, tam: int) -> ImageFont.FreeTypeFont:
    """Fuente moderna: la de fonts/ si existe, si no Segoe UI (Windows), Helvetica (Mac) o DejaVu."""
    candidatos = {
        "bold": ["fonts/Poppins-SemiBold.ttf", "C:/Windows/Fonts/seguisb.ttf", "C:/Windows/Fonts/segoeuib.ttf",
                 "/System/Library/Fonts/Helvetica.ttc", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
        "regular": ["fonts/Poppins-Regular.ttf", "C:/Windows/Fonts/segoeui.ttf",
                    "/System/Library/Fonts/Helvetica.ttc", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"],
    }[peso]
    for c in candidatos:
        p = Path(c) if Path(c).is_absolute() else ROOT / c
        if p.exists():
            return ImageFont.truetype(str(p), tam)
    return ImageFont.load_default(tam)


def envolver(texto: str, font: ImageFont.FreeTypeFont, ancho: int) -> list[str]:
    lineas, actual = [], ""
    for palabra in texto.split():
        prueba = f"{actual} {palabra}".strip()
        if font.getlength(prueba) <= ancho or not actual:
            actual = prueba
        else:
            lineas.append(actual)
            actual = palabra
    return lineas + ([actual] if actual else [])


# -------------------------------------------------------------- producto real

_REMBG = None


def extraer_producto(portada: Path, metodo: str) -> tuple[Image.Image, float]:
    """Recorta el producto de la portada (fondo blanco puro) sin tocar sus píxeles.

    metodo="relleno": rellena el blanco desde los bordes. Lo blanco DENTRO del
      producto (cajas, vidrios, carcasas transparentes) se conserva, pero los
      huecos cerrados (entre correas, agujeros) quedan blancos.
    metodo="rembg": rembg recorta también los huecos, pero puede comerse partes
      blancas o transparentes del producto.

    Devuelve (producto RGBA recortado, base): base es la fracción de la altura
    donde termina el cuerpo del producto. Debajo puede quedar un resto claro de
    la sombra original; la base real se usa para apoyar el producto."""
    global _REMBG
    rgb = Image.open(portada).convert("RGB")
    if metodo == "rembg":
        from rembg import new_session, remove

        _REMBG = _REMBG or new_session("isnet-general-use")
        alpha = remove(rgb, session=_REMBG, post_process_mask=True).getchannel("A")
    else:
        marca = (255, 0, 255)
        relleno = ImageOps.expand(rgb, border=2, fill=(255, 255, 255))
        ImageDraw.floodfill(relleno, (0, 0), marca, thresh=6)
        es_fondo = (np.array(relleno.crop((2, 2, rgb.width + 2, rgb.height + 2))) == marca).all(axis=2)
        alpha = Image.fromarray(np.where(es_fondo, 0, 255).astype(np.uint8))
        # borde suave de 1 px para que no se vea recortado con tijera
        alpha = alpha.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1.2))
    bbox = alpha.point(lambda a: 255 if a > 16 else 0).getbbox()
    if not bbox:
        raise ErrorProducto("no se encontró el producto en la portada")
    producto = rgb.convert("RGBA")
    producto.putalpha(alpha)
    # cuerpo = lo claramente no blanco; el filtro de mediana ignora motas sueltas
    cuerpo = (np.array(rgb.convert("L")) < 235) & (np.array(alpha) > 16)
    cuerpo = Image.fromarray(cuerpo.astype(np.uint8) * 255).filter(ImageFilter.MedianFilter(5)).getbbox()
    base = (min(cuerpo[3], bbox[3]) - bbox[1]) / (bbox[3] - bbox[1]) if cuerpo else 1.0
    return producto.crop(bbox), base


def ajustar(producto: Image.Image, ancho: int, alto: int) -> Image.Image:
    escala = min(ancho / producto.width, alto / producto.height)
    return producto.resize((max(1, round(producto.width * escala)), max(1, round(producto.height * escala))),
                           Image.LANCZOS)


def pegar_con_sombra(lienzo: Image.Image, producto: Image.Image, cx: int, base_y: int,
                     intensidad: float = 1.0, base: float = 1.0) -> None:
    """Pega el producto con su base (fracción `base` de su altura) en base_y,
    con sombra de contacto y sombra suave."""
    w, h = producto.size
    x, y = cx - w // 2, base_y - round(h * base)
    capa = Image.new("RGBA", lienzo.size, (0, 0, 0, 0))

    # sombra suave: la silueta del producto, desplazada hacia abajo y difuminada
    silueta = Image.new("RGBA", producto.size, (0, 0, 0, 0))
    silueta.putalpha(producto.getchannel("A").point(lambda a: int(a * 0.28 * intensidad)))
    capa.alpha_composite(silueta, (x, y + max(6, h // 60)))
    capa = capa.filter(ImageFilter.GaussianBlur(max(8, w // 45)))

    # sombra de contacto: elipse oscura bajo la base para que no flote
    contacto = Image.new("RGBA", lienzo.size, (0, 0, 0, 0))
    eh = max(14, int(w * 0.06))
    ImageDraw.Draw(contacto).ellipse((cx - int(w * 0.45), base_y - eh // 2, cx + int(w * 0.45), base_y + eh // 2),
                                     fill=(0, 0, 0, int(120 * intensidad)))
    capa.alpha_composite(contacto.filter(ImageFilter.GaussianBlur(max(10, eh))))

    lienzo.alpha_composite(capa)
    lienzo.alpha_composite(producto, (x, y))


# -------------------------------------------------------------------- OpenAI

def con_reintentos(fn, que: str):
    """Llama fn() hasta que funcione. Espera 30 s, 60 s, 120 s... (máx. 15 min) entre intentos."""
    import openai

    espera, intento = ESPERA_INICIAL, 1
    while True:
        try:
            return fn()
        except openai.AuthenticationError as e:
            raise ErrorFatal("La API key no es válida. Revisa OPENAI_API_KEY en tu .env.") from e
        except openai.PermissionDeniedError as e:
            raise ErrorFatal(f"Tu cuenta no tiene permiso para esto ({que}): {e}") from e
        except openai.NotFoundError as e:
            raise ErrorFatal(f"Modelo no disponible ({que}). Prueba con otro modelo: --modelo-imagen / "
                             f"--modelo-texto. Detalle: {e}") from e
        except openai.RateLimitError as e:
            if "insufficient_quota" in str(e):
                raise ErrorFatal("Tu cuenta de OpenAI no tiene saldo (insufficient_quota). "
                                 "Carga crédito en platform.openai.com/settings/organization/billing.") from e
            motivo = "límite de uso de la API"
        except (openai.BadRequestError, openai.UnprocessableEntityError) as e:
            # p. ej. el filtro de contenido rechazó el prompt: reintentar da lo mismo
            raise ErrorProducto(f"OpenAI rechazó la solicitud ({que}): {e}") from e
        except (openai.APIConnectionError, openai.APITimeoutError, openai.InternalServerError,
                openai.APIStatusError, OSError) as e:
            motivo = f"{type(e).__name__}: {e}"
        log.warning("Falló %s (intento %d, %s). Reintento en %d s...", que, intento, motivo, espera)
        time.sleep(espera)
        espera, intento = min(espera * 2, ESPERA_MAXIMA), intento + 1


class OpenAIBackend:
    def __init__(self, modelo_imagen: str, modelo_texto: str):
        from openai import OpenAI

        if not os.environ.get("OPENAI_API_KEY"):
            raise ErrorFatal("Falta OPENAI_API_KEY. Crea el archivo .env (ver .env.example) o define la variable.")
        # los reintentos los manejamos nosotros, con esperas largas
        self.client = OpenAI(max_retries=0, timeout=180)
        self.modelo_imagen, self.modelo_texto = modelo_imagen, modelo_texto

    def fondo(self, escena: str) -> Image.Image:
        kwargs = dict(model=self.modelo_imagen, prompt=PROMPT_FONDO.format(escena=escena), size="1024x1024", n=1)
        if self.modelo_imagen.startswith("dall-e"):
            kwargs["response_format"] = "b64_json"  # los gpt-image siempre devuelven base64
        resp = con_reintentos(lambda: self.client.images.generate(**kwargs), "generar fondo")
        datos = resp.data[0].b64_json
        if not datos:
            raise ErrorProducto("la API no devolvió imagen")
        return Image.open(io.BytesIO(base64.b64decode(datos))).convert("RGB")

    def specs(self, descripcion: str) -> dict:
        def pedir():
            resp = self.client.chat.completions.create(
                model=self.modelo_texto,
                response_format={"type": "json_object"},
                temperature=0.4,
                messages=[{"role": "system", "content": PROMPT_SPECS},
                          {"role": "user", "content": f"Producto: {descripcion}"}],
            )
            return resp.choices[0].message.content

        for _ in range(3):  # si el JSON viene mal formado, se vuelve a pedir
            try:
                return validar_specs(json.loads(con_reintentos(pedir, "generar características")))
            except (ValueError, KeyError, TypeError) as e:
                log.warning("Respuesta de texto inválida (%s), se pide de nuevo.", e)
        raise ErrorProducto("la API de texto no devolvió 3 características válidas")


class SimuladoBackend:
    """Sin API ni costo: fondo degradado y características de ejemplo. Para probar el montaje."""

    def fondo(self, escena: str) -> Image.Image:
        arriba, abajo = (205, 220, 235), (150, 160, 150)
        img = Image.new("RGB", (1024, 1024))
        d = ImageDraw.Draw(img)
        for y in range(1024):
            t = y / 1023
            d.line([(0, y), (1023, y)], fill=tuple(round(a + (b - a) * t) for a, b in zip(arriba, abajo)))
        return img

    def specs(self, descripcion: str) -> dict:
        return {"titulo": descripcion.split(" (")[0].title(),
                "caracteristicas": ["Característica de ejemplo uno", "Segunda característica de ejemplo",
                                    "Tercera característica corta"]}


def validar_specs(d: dict) -> dict:
    carac = [str(c).strip().rstrip(".") for c in d["caracteristicas"] if str(c).strip()]
    if len(carac) < 3:
        raise ValueError("menos de 3 características")
    return {"titulo": str(d.get("titulo", "")).strip()[:60], "caracteristicas": [c[:80] for c in carac[:3]]}


# ------------------------------------------------------------------- montajes

def cache_json(ruta: Path, generar):
    """Guarda en .cache_catalogo lo que ya se pagó, para no pedirlo de nuevo si algo falla después."""
    if ruta.exists():
        return json.loads(ruta.read_text(encoding="utf-8"))
    valor = generar()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(valor, ensure_ascii=False, indent=2), encoding="utf-8")
    return valor


def crear_contexto(producto: Image.Image, base: float, fondo: Image.Image) -> Image.Image:
    lienzo = fondo.resize((SIZE, SIZE), Image.LANCZOS).convert("RGBA")
    pieza = ajustar(producto, int(SIZE * 0.62), int(SIZE * 0.58))
    pegar_con_sombra(lienzo, pieza, SIZE // 2, int(SIZE * 0.86), base=base)
    return lienzo


def crear_specs(producto: Image.Image, base: float, specs: dict) -> Image.Image:
    lienzo = Image.new("RGBA", (SIZE, SIZE), GRIS + (255,))
    pieza = ajustar(producto, 560, 880)
    pegar_con_sombra(lienzo, pieza, 350, 750 + round(pieza.height * base) // 2, intensidad=0.6, base=base)

    d = ImageDraw.Draw(lienzo)
    x, ancho = 720, 700
    f_titulo, f_item, f_num = fuente("bold", 76), fuente("regular", 54), fuente("bold", 46)
    alto_linea_t, alto_linea_i, circulo, sangria = 92, 70, 88, 120
    titulo = envolver(specs["titulo"], f_titulo, ancho) if specs["titulo"] else []
    items = [envolver(c, f_item, ancho - sangria) for c in specs["caracteristicas"]]

    alto_titulo = len(titulo) * alto_linea_t + (80 if titulo else 0)
    alto_items = sum(max(circulo, len(l) * alto_linea_i) for l in items) + 64 * (len(items) - 1)
    y = (SIZE - alto_titulo - alto_items) // 2
    for linea in titulo:
        d.text((x, y), linea, font=f_titulo, fill=TEXTO)
        y += alto_linea_t
    if titulo:
        d.rounded_rectangle((x, y + 18, x + 130, y + 30), radius=6, fill=ACENTO)
        y += 80
    for n, lineas in enumerate(items, 1):
        bloque = len(lineas) * alto_linea_i
        d.ellipse((x, y, x + circulo, y + circulo), fill=ACENTO)
        d.text((x + circulo // 2, y + circulo // 2), str(n), font=f_num, fill=(255, 255, 255), anchor="mm")
        ty = y + max(0, (circulo - bloque) // 2)
        for linea in lineas:
            d.text((x + sangria, ty), linea, font=f_item, fill=TEXTO)
            ty += alto_linea_i
        y += max(circulo, bloque) + 64
    return lienzo


# ----------------------------------------------------------------------- main

def procesar(portada: Path, backend, args) -> tuple[bool, bool]:
    nombre = portada.stem.removeprefix("1_portada_")
    rel = portada.resolve().relative_to(IMAGES)
    carpeta = portada.parent if not args.simular else SIM_DIR / rel.parent
    dest_ctx, dest_specs = carpeta / f"2_contexto_{nombre}.jpg", carpeta / f"3_specs_{nombre}.jpg"
    producto_slug, categoria = rel.parent.name, rel.parts[0]
    hacer_ctx, hacer_specs = not dest_ctx.exists(), not dest_specs.exists()
    if not (hacer_ctx or hacer_specs):
        return False, False

    metodo = args.extractor
    if metodo == "auto":
        metodo = "relleno" if producto_slug in USAR_RELLENO else "rembg"
    producto, base = extraer_producto(portada, metodo)
    clave = CACHE / ("simulado" if args.simular else "api") / rel.parent / nombre
    if hacer_ctx:
        escena = ESCENAS.get(producto_slug) or ESCENAS_CATEGORIA.get(categoria, "a clean studio tabletop")
        cache_fondo = clave.with_suffix(".fondo.png")
        if cache_fondo.exists():
            fondo = Image.open(cache_fondo).convert("RGB")
        else:
            fondo = backend.fondo(escena)
            cache_fondo.parent.mkdir(parents=True, exist_ok=True)
            fondo.save(cache_fondo)
        guardar_jpg(crear_contexto(producto, base, fondo), dest_ctx)
        log.info("  creado %s", dest_ctx.relative_to(ROOT))
    if hacer_specs:
        descripcion = f"{humano(producto_slug)} ({humano(nombre)})"
        specs = cache_json(clave.with_suffix(".specs.json"), lambda: backend.specs(descripcion))
        guardar_jpg(crear_specs(producto, base, specs), dest_specs)
        log.info("  creado %s", dest_specs.relative_to(ROOT))
    return hacer_ctx, hacer_specs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("rutas", nargs="*", type=Path, default=[IMAGES], help="carpetas o portadas (por defecto images/)")
    ap.add_argument("--limite", type=int, default=0, help="procesar como máximo N portadas pendientes (para probar)")
    ap.add_argument("--simular", action="store_true", help="sin API ni costo; guarda en _simulacion/")
    ap.add_argument("--extractor", choices=["auto", "relleno", "rembg"], default="auto",
                    help="cómo recortar el producto de la portada (auto: según el tipo de producto)")
    ap.add_argument("--modelo-imagen", default=os.environ.get("OPENAI_MODELO_IMAGEN", "dall-e-3"))
    ap.add_argument("--modelo-texto", default=os.environ.get("OPENAI_MODELO_TEXTO", "gpt-4o-mini"))
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S",
                        handlers=[logging.StreamHandler(), logging.FileHandler(LOG_FILE, encoding="utf-8")])
    for ruidoso in ("openai", "httpx", "httpx2"):
        logging.getLogger(ruidoso).setLevel(logging.WARNING)
    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env")
    except ImportError:
        pass

    portadas = []
    for r in args.rutas:
        r = r.resolve()
        portadas += sorted(r.rglob("1_portada_*.jpg")) if r.is_dir() else [r]
    if not portadas:
        log.error("No encontré archivos 1_portada_*.jpg en %s", ", ".join(map(str, args.rutas)))
        return 1

    try:
        backend = SimuladoBackend() if args.simular else OpenAIBackend(args.modelo_imagen, args.modelo_texto)
    except ErrorFatal as e:
        log.error("DETENIDO: %s", e)
        return 2

    log.info("%d portadas encontradas. Modelos: imagen=%s texto=%s%s", len(portadas), args.modelo_imagen,
             args.modelo_texto, " (SIMULACIÓN)" if args.simular else "")
    hechos = saltados = fallidos = 0
    for i, portada in enumerate(portadas, 1):
        if args.limite and hechos >= args.limite:
            break
        etiqueta = portada.resolve().relative_to(ROOT)
        try:
            ctx, specs = procesar(portada, backend, args)
            if ctx or specs:
                hechos += 1
                log.info("[%d/%d] listo %s", i, len(portadas), etiqueta)
            else:
                saltados += 1
        except ErrorFatal as e:
            log.error("DETENIDO en %s: %s", etiqueta, e)
            return 2
        except KeyboardInterrupt:
            log.info("Interrumpido por el usuario. Lo ya creado queda guardado; vuelve a correr para seguir.")
            return 130
        except Exception as e:  # un producto con problemas no detiene el resto
            fallidos += 1
            log.error("[%d/%d] ERROR en %s: %s (se sigue con el siguiente)", i, len(portadas), etiqueta, e)

    log.info("Terminado: %d productos procesados, %d ya estaban listos, %d con error.", hechos, saltados, fallidos)
    return 1 if fallidos else 0


if __name__ == "__main__":
    sys.exit(main())
