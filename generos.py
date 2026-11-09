"""Completa el género ausente usando el álbum de una grabación identificada por ISRC."""

from functools import lru_cache

import requests


def normalizar_genero(nombre):
    texto = " ".join(nombre.casefold().split())
    return {
        "r&b/soul": "r&b", "r & b": "r&b", "rnb": "r&b",
        "hip hop": "hip-hop", "rap/hip hop": "hip-hop",
        "classique": "classical", "clásica": "classical",
        "indie-pop": "indie pop",
    }.get(texto, texto)


@lru_cache(maxsize=256)
def generos_album(album_id):
    """Reutiliza las respuestas correctas de álbumes durante esta ejecución."""
    respuesta = requests.get(f"https://api.deezer.com/album/{album_id}", timeout=(3, 5))
    respuesta.raise_for_status()
    datos = respuesta.json()
    if datos.get("error"):
        raise ValueError("Deezer devolvió un error de catálogo")
    if str(datos.get("id")) != str(album_id):
        raise ValueError("El álbum recibido no coincide")
    nombres = []
    for genero in (datos.get("genres") or {}).get("data", []):
        nombre = genero.get("name")
        if isinstance(nombre, str) and nombre.strip():
            nombre = normalizar_genero(nombre)
            if nombre not in nombres:
                nombres.append(nombre)
    return tuple(nombres)


def completar_genero(cancion, pista, isrc):
    """Conserva el género directo y registra el origen de cualquier estimación."""
    if cancion.get("genero"):
        return
    if not isinstance(isrc, str) or not isrc:
        return
    if (pista.get("isrc") or "").upper() != isrc.upper():
        return
    album_id = (pista.get("album") or {}).get("id")
    if not str(album_id).isdigit():
        return
    try:
        generos = generos_album(str(album_id))
    except (requests.RequestException, ValueError, TypeError, AttributeError):
        print("Género: no se pudo consultar el álbum en Deezer.")
        return
    if generos:
        # Usa la primera etiqueta del catálogo para el grafo y conserva todas para filtrar.
        cancion["genero"] = generos[0]
        cancion["generos"] = list(generos)
        cancion.setdefault("fuentes", {})["genero"] = "álbum de Deezer"
        cancion.setdefault("estimaciones", {})["genero"] = (
            f"Estimado desde el álbum {album_id}, grabación verificada por ISRC"
        )
