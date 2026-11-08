import re
import subprocess
from bisect import bisect_right
from math import isfinite
from statistics import median
from time import sleep

import requests

PESOS = dict(genero=.30, bpm=.20, energia=.20, densidad=.10, brillo=.10, valencia=.10)
ESCALAS = {
    "bpm": ((70, 100, 120, 140), ("muy lento", "lento", "moderado", "rápido", "muy rápido")),
    "energia": ((.20, .40, .60, .80), ("muy baja", "baja", "media", "alta", "muy alta")),
    "densidad": ((.25, .50, .75), ("muy baja", "baja", "media", "alta")),
    "brillo": ((.34, .67), ("oscuro", "moderado", "brillante")),
    "valencia": ((.35, .65), ("melancólica", "intermedia", "alegre")),
}
MATRIZ = {  # Los pares de géneros sin criterio asignado quedan fuera de la cobertura.
    frozenset(("rock", "hard rock")): .25,
    frozenset(("rock", "pop")): .50,
    frozenset(("rock", "jazz")): .75,
    frozenset(("hard rock", "classical")): 1.,
}
ISRC = re.compile(r"[A-Za-z]{2}[A-Za-z0-9]{3}[0-9]{7}")
CAMPOS_AUDIO = ("brillo", "densidad")


def faltan_medidas(cancion):
    return any(cancion[campo] is None for campo in CAMPOS_AUDIO)


def guardar_medidas(cancion, medidas, fuente):
    """Conserva los valores directos y registra la procedencia de cada estimación."""
    for campo, (valor, detalle) in medidas.items():
        if cancion[campo] is None:
            cancion[campo] = min(1, valor)
            cancion.setdefault("estimaciones", {})[campo] = detalle
            cancion.setdefault("fuentes", {})[campo] = fuente


def clasificar(track, audio):
    """Acepta género explícito de pista y medidas directas, nunca sustitutos."""
    genero = track.get("genre") or audio.get("genre")
    genero = genero.strip().casefold() if isinstance(genero, str) else None
    cancion = dict(titulo=track.get("name") or "Título desconocido", genero=genero or None)
    artistas = track.get("artists") or []
    cancion["artista"] = ", ".join(a["name"] for a in artistas if a and a.get("name"))
    for campo, origen in zip(ESCALAS, ("tempo", "energy", "rhythmic_density", "brightness", "valence")):
        valor = audio.get(origen)
        valido = type(valor) in (int, float) and isfinite(valor)
        if valido:
            valido = valor > 0 if campo == "bpm" else 0 <= valor <= 1
        cancion[campo] = valor if valido else None
    return cancion


def etiqueta(campo, valor):#Asigna el intervalo que comienza en el umbral alcanzado
    cortes, nombres = ESCALAS[campo]
    return nombres[bisect_right(cortes, valor)]


def arista(a, b):#Devuelve distancia en escala 0–100 y fracción del peso nominal cubierto
    suma = cobertura = 0.
    for campo, factor in PESOS.items():
        x, y = a[campo], b[campo]
        if x is None or y is None:
            continue
        if campo in CAMPOS_AUDIO and a.get("fuentes", {}).get(campo) != b.get("fuentes", {}).get(campo):
            continue
        if campo == "genero":
            delta = 0 if x == y else MATRIZ.get(frozenset((x, y)))
            if delta is None:
                continue
        elif campo == "bpm":
            delta = min(abs(x - y) / 100, 1)
        else:
            delta = abs(x - y)
        suma += factor * delta
        cobertura += factor
    return (100 * suma / cobertura if cobertura else None), cobertura


def estimar_audio(ruta, bpm):#Analiza hasta 30 s desde el inicio. `ruta` es un Path o los bytes del audio
    filtro = ("atrim=duration=30,aformat=channel_layouts=mono,aresample=22050,"
              "aspectralstats=win_size=1024:overlap=0.75:measure=centroid,"
              "astats=metadata=1:reset=1:measure_perchannel=none:measure_overall=RMS_level,"
              "ametadata=print:file=-")
    resultado = subprocess.run(
        ["ffmpeg", "-nostdin", "-v", "error", "-i", ("pipe:0" if isinstance(ruta, bytes) else str(ruta.resolve())), "-map", "0:a:0",
         "-af", filtro, "-f", "null", "-"], capture_output=True, input=ruta if isinstance(ruta, bytes) else None,
        timeout=45, check=True)
    niveles, centroides = [], []
    for linea in resultado.stdout.decode().splitlines():
        clave, _, dato = linea.partition("=")
        if clave.endswith(".Overall.RMS_level"):
            niveles.append(10 ** (float(dato) / 20))
        elif clave.endswith(".centroid"):
            centroides.append(float(dato))
    paso = 256 / 22050
    segundos = min(30, len(niveles) * paso)
    if segundos < 1 or len(niveles) != len(centroides):
        return {}
    umbral = max(1e-8, max(niveles) * .01)
    activos = [hz for nivel, hz in zip(niveles, centroides)
               if nivel > umbral and isfinite(hz) and hz > 0]
    if not activos:
        return {}
    hz = median(activos)
    medidas = {"brillo": (min(hz / 4000, 1), f"{hz:.0f} Hz")}
    if bpm:  # Ataque: subida de nivel frente a los ~93 ms anteriores, separada ≥70 ms.
        ataques = 0
        ultimo = -100
        for i, nivel in enumerate(niveles):
            if nivel <= umbral or (i - ultimo) * paso < .07:
                continue
            base = median(niveles[max(0, i - 8):i]) if i else 0
            if nivel > base * 1.5:
                ataques += 1
                ultimo = i
        densidad = ataques / (segundos * bpm / 60)
        medidas["densidad"] = (min(densidad / 4, 1), f"{densidad:.2f} ataques/pulso")
    return {k: (v, f"{unidad}, primeros {segundos:.1f} s del archivo")
            for k, (v, unidad) in medidas.items()}


def completar_audio(cancion, ruta):
    """Completa únicamente datos ausentes y conserva el origen y la medida original."""
    if not faltan_medidas(cancion):
        return
    try:
        medidas = estimar_audio(ruta, cancion["bpm"])
    except (OSError, ValueError, subprocess.SubprocessError):
        print(f"No se pudo analizar {ruta.name}")
        return
    guardar_medidas(cancion, medidas, "audio local")


def completar_catalogo(cancion, isrc):
    """Busca una grabación inequívoca por ISRC y usa su análisis público, sin audio."""
    if not isinstance(isrc, str) or not ISRC.fullmatch(isrc):
        return
    if not faltan_medidas(cancion):
        return
    try:
        servicio = "MusicBrainz"
        sleep(1.1)  # Límite de consultas a MusicBrainz.
        r = requests.get("https://musicbrainz.org/ws/2/isrc/" + isrc.upper(),
                         params={"fmt": "json"}, headers={"User-Agent": "ClasificadorMusical/1.0 (local music analysis)"},
                         timeout=5)
        if r.status_code == 404:
            return
        r.raise_for_status()
        grabaciones = r.json().get("recordings", [])
        if len(grabaciones) != 1:
            return
        mbid = grabaciones[0]["id"]
        servicio = "AcousticBrainz"
        r = requests.get(f"https://acousticbrainz.org/api/v1/{mbid}/low-level", timeout=5)
        if r.status_code == 404:
            return
        r.raise_for_status()
        datos = r.json()
        ritmo = datos.get("rhythm", {})
        hz = datos.get("lowlevel", {}).get("spectral_centroid", {}).get("median")
        tasa, bpm = ritmo.get("onset_rate"), ritmo.get("bpm")
        medidas = {}
        if type(hz) in (int, float) and isfinite(hz) and hz > 0:
            medidas["brillo"] = (hz / 4000, f"{hz:.0f} Hz")
        if all(type(x) in (int, float) and isfinite(x) for x in (tasa, bpm)) and tasa >= 0 and bpm > 0:
            densidad = tasa * 60 / bpm
            medidas["densidad"] = (densidad / 4, f"{densidad:.2f} ataques/pulso")
        guardar_medidas(cancion, medidas, "AcousticBrainz")
    except (requests.RequestException, ValueError, AttributeError, KeyError, TypeError) as error:
        print(f"{cancion['titulo']} · {servicio}: {type(error).__name__}")


def completar_muestra(cancion, isrc):#Analiza en memoria la muestra oficial de la misma grabación
    if not faltan_medidas(cancion):
        return
    if not isinstance(isrc, str) or not ISRC.fullmatch(isrc):
        return "sin ISRC válido"
    etapa = "catálogo Deezer"
    try:
        r = requests.get(f"https://api.deezer.com/track/isrc:{isrc.upper()}", timeout=8)
        r.raise_for_status()
        pista = r.json()
        if pista.get("error"):
            return f"Deezer: {pista['error'].get('message', 'error de catálogo')}"
        if (pista.get("isrc") or "").upper() != isrc.upper():
            return "Deezer: sin coincidencia exacta"
        url = pista.get("preview") or ""
        if not url.startswith("https://"):
            return "Deezer: grabación sin muestra disponible"
        etapa = "muestra Deezer"
        with requests.get(url, stream=True, timeout=10) as clip:
            clip.raise_for_status()
            contenido = bytearray()
            for bloque in clip.iter_content(65536):
                contenido.extend(bloque)
                if len(contenido) > 8_000_000:
                    return "muestra demasiado grande"
        bpm = cancion["bpm"] or pista.get("bpm")
        if type(bpm) not in (int, float) or not isfinite(bpm) or bpm <= 0:
            bpm = None
        etapa = "análisis de la muestra"
        medidas = estimar_audio(bytes(contenido), bpm)
        guardar_medidas(cancion, medidas, "muestra de Deezer")
        if not medidas:
            return "muestra sin señal analizable"
        if cancion["densidad"] is None:
            return "densidad pendiente por falta de BPM"
    except requests.HTTPError as error:
        return f"{etapa}: HTTP {error.response.status_code}"
    except (requests.RequestException, OSError, ValueError, subprocess.SubprocessError) as error:
        return f"{etapa}: {type(error).__name__}"


def biblioteca(carpeta=None):#Reutiliza los lectores del proyecto y conserva incluso pistas inaccesibles
    from main import buscar_reccobeats, crear_cliente
    items = crear_cliente().current_user_saved_tracks(limit=20)["items"]
    for item in items:
        track = item.get("track") or {}
        respuesta = buscar_reccobeats(track) if track.get("id") else None
        audio = respuesta[1] if respuesta and isinstance(respuesta[1], dict) else {}
        if respuesta and not track.get("genre"):
            track = {**track, "genre": respuesta[0].get("genre")}
        cancion = clasificar(track, audio)
        if carpeta and track.get("id"):
            for ext in (".wav", ".flac", ".mp3", ".m4a"):
                ruta = carpeta / (track["id"] + ext)
                if ruta.is_file():
                    completar_audio(cancion, ruta)
                    break
        isrc = (track.get("external_ids") or {}).get("isrc")
        aviso = completar_muestra(cancion, isrc)
        if aviso:
            print(f"{cancion['titulo']} · {aviso}")
            if faltan_medidas(cancion) and isrc:
                completar_catalogo(cancion, isrc)
        yield cancion