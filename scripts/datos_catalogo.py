"""Fichas de producto para las imágenes 3_specs (sin IA).

Los datos salen de las infografías y fotos del propio catálogo (images/**/info*,
caracteristicas*, guia*, etiquetas de caja). Solo se agrega lo que se ve ahí.
El color y los modelos compatibles se leen del nombre de cada archivo.
"""
import re

# escena de fondo (ver fondos.py), título y 3 características por producto
PRODUCTOS = {
    "cables-iphone": {
        "escena": "escritorio",
        "titulo": "Cable de Carga para iPhone",
        "caracteristicas": ["Largo de 1 metro", "Carga y transferencia de datos", "Compatible con cargador 20W"],
    },
    "cargador-iphone-20w": {
        "escena": "escritorio",
        "titulo": "Cargador USB-C 20W",
        "caracteristicas": ["Potencia de 20W por USB-C", "Carga rápida para iPhone", "Incluye cable de 1 metro"],
    },
    "cargador-solma-45w": {
        "escena": "escritorio",
        "titulo": "Cargador Solma 45W USB-C",
        "caracteristicas": ["Carga súper rápida PD 3.0 hasta 45W", "Compatible con Android y iPhone",
                            "Entrada universal 100–240 V"],
    },
    "micas-de-vidrio-iphone": {  # todas las fotos son del mismo pack (las de 1 mica son detalle)
        "escena": "estudio_frio",
        "titulo": "Pack 4 Micas de Vidrio iPhone",
        "caracteristicas": ["Pack de 4 unidades", "Protege la pantalla de rayas y golpes", "Máxima sensibilidad táctil"],
    },
    "carcasas-transparentes-magsafe-iphone": {
        "escena": "estudio_frio",
        "titulo": "Carcasa Transparente MagSafe",
        "caracteristicas": ["Compatible con MagSafe", "Bordes reforzados anti caídas",
                            "Transparente: luce el color de tu iPhone"],
    },
    "carcasas-silicona-iphone": {
        "escena": "estudio",
        "titulo": "Carcasa de Silicona iPhone",
        "caracteristicas": ["Suave al tacto y antideslizante", "Delgada y ligera", "Compatible con carga inalámbrica"],
    },
    "cascos-trip-enduro": {
        "escena": "sendero",
        "titulo": "Casco MTB Trip Enduro",
        "caracteristicas": ["Visera frontal integrada", "Múltiples ventilaciones", "Ajuste trasero regulable"],
    },
    "lentes-ciclismo": {
        "escena": "ruta",
        "titulo": "Lentes de Ciclismo UV400",
        "caracteristicas": ["Protección UV400 total", "Marco TR90 flexible, 28–35 g", "Monolente de policarbonato"],
    },
    "zapatillas-joma": {
        "escena": "cancha",
        "titulo": "Zapatillas Joma Toledo Jr",
        "caracteristicas": ["Modelo junior para niños", "Tallas EU 24 a 30 (CL 23 a 29)", "Ideal para futsal y cancha"],
    },
    "senuelos-poseidon": {
        "escena": "rio",
        "titulo": "Señuelo Poseidon Minnow",
        "caracteristicas": ["2 anzuelos triples incluidos", "Spinning, casting y trolling", "Para agua dulce y salada"],
    },
    "cintillo-linterna-led": {
        "escena": "camping",
        "titulo": "Linterna Frontal LED Recargable",
        "caracteristicas": ["350 lúmenes, haz de 230°", "Sensor de movimiento sin contacto", "Carga por USB"],
    },
    "maquina-cortar-pelo-dorada": {
        "escena": "barberia",
        "titulo": "Recortadora Tasbel Dorada",
        "caracteristicas": ["Cuchilla T de acero inoxidable", "Batería de litio, hasta 90 min",
                            "Incluye peines de 1, 2 y 3 mm"],
    },
    "maquina-cortar-pelo-grande": {
        "escena": "barberia",
        "titulo": "Máquina de Corte con Pantalla LCD",
        "caracteristicas": ["Hoja T de acero de precisión", "Pantalla LCD de batería", "Carga USB-C, batería 500 mAh"],
    },
}

COLORES_CARCASA = {"azl": "Azul navy", "azul": "Azul navy", "neg": "Negro", "negro": "Negro"}
COLORES_ZAPATILLA = {"blue-yellow": "Azul / Amarillo", "naranja-amarilla": "Naranja / Amarillo",
                     "navy-orange": "Azul marino / Naranja"}
COLORES_SENUELO = ["copper-black", "fire-tiger", "fire-trout", "hot-pink-blue", "natural-trout", "orange-silver",
                   "pink-brown-trout", "pink-purple-trout", "silver-pink-shad"]
NO_MODELO = {"sil", "azl", "neg", "negro", "azul", "navy", "iphone", "carcasa", "transparente", "magsafe", "mag",
             "jpg", "png"}
SUFIJOS = {"pro": "Pro", "max": "Max", "mini": "Mini", "plus": "Plus", "air": "Air", "e": "e"}


def modelos_iphone(nombre: str) -> str | None:
    """'13-pro-max-14-pro' -> 'iPhone 13 Pro Max, 14 Pro'; 'sil-azl-12promax' -> 'iPhone 12 Pro Max'."""
    tokens = []
    for tok in nombre.split("-"):
        if tok in NO_MODELO:
            continue
        m = re.fullmatch(r"(\d+)([a-z]*)", tok)
        if m:
            tokens.append(m.group(1))
            resto = m.group(2)
            for suf in ("promax", "pro", "max", "mini", "plus", "air", "e"):
                if resto == suf:
                    tokens += ["pro", "max"] if suf == "promax" else [suf]
                    break
        elif tok in SUFIJOS:
            tokens.append(tok)
    modelos = []
    for tok in tokens:
        if tok.isdigit():
            modelos.append(tok)
        elif modelos:
            modelos[-1] += SUFIJOS[tok] if tok == "e" else f" {SUFIJOS[tok]}"
    return "iPhone " + ", ".join(modelos) if modelos else None


def ficha(producto: str, nombre: str) -> dict | None:
    """Título, subtítulo y 3 características para una portada (nombre sin '1_portada_')."""
    base = PRODUCTOS.get(producto)
    if not base:
        return None
    titulo, subtitulo, carac = base["titulo"], None, list(base["caracteristicas"])
    partes = set(nombre.split("-"))

    if producto in ("carcasas-silicona-iphone", "carcasas-transparentes-magsafe-iphone"):
        color = next((COLORES_CARCASA[p] for p in nombre.split("-") if p in COLORES_CARCASA), None)
        subtitulo = " · ".join(x for x in (color, modelos_iphone(nombre)) if x) or None
    elif producto == "zapatillas-joma":
        subtitulo = next((c for k, c in COLORES_ZAPATILLA.items() if nombre.startswith(k)), None)
    elif producto == "senuelos-poseidon":
        if nombre.startswith("pack-5"):
            peso = "10 g" if "10gr" in nombre else "8 g"
            titulo, subtitulo = "Pack 5 Señuelos Poseidon Minnow", f"5 colores · {peso} cada uno"
        elif nombre.startswith("senuelos-4en1"):
            titulo, subtitulo = "Pack 4 Señuelos Poseidon Minnow", "4 colores"
        else:
            color = next((c for c in COLORES_SENUELO if nombre.startswith(c)), None)
            if color:
                peso = "10 g" if "10gr" in nombre else "8 g y 10 g"
                subtitulo = f"Color {color.replace('-', ' ').title()} · {peso}"
    elif producto == "cables-iphone":
        cargador = "cargador" in partes
        lightning = bool(partes & {"lightning", "ltn"})
        if cargador and lightning:
            titulo = "Kit Cargador 20W + Cable Lightning"
        elif cargador and "usb" in partes:
            titulo = "Kit Cargador 20W + Cable USB-C"
        elif cargador:
            titulo = "Cargador USB-C 20W"
        elif lightning:
            titulo, subtitulo = "Cable USB-C a Lightning", "1 metro"
        else:
            titulo, subtitulo = "Cable USB-C a USB-C", "1 metro"
        if cargador:
            carac = ["Potencia de 20W por USB-C", "Carga rápida para iPhone", "Enchufe de 2 patas redondas"]
    elif producto == "cargador-iphone-20w":
        titulo = "Kit Cargador 20W + Cable " + ("Lightning" if "lightning" in partes else "USB-C")
    return {"titulo": titulo, "subtitulo": subtitulo, "caracteristicas": carac}
