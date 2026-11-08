import requests
import spotipy
from spotipy.oauth2 import SpotifyOAuth

def crear_cliente():
    return spotipy.Spotify(
        requests_timeout=(3, 10),
        retries=1,
        status_retries=1,
        auth_manager=SpotifyOAuth(
            client_id="fe91e7167ff7470a9be408d2dd1788bb",#Identificador de la aplicacion
            client_secret="8439288bab2d48ca9c6ebf9655fad87a",#Contraseña
            redirect_uri="http://127.0.0.1:9090",
            scope="user-library-read"#Solo permisos de lectura
        )
    )

def buscar_reccobeats(track):#Buscar data 
    spotify_id = track.get("id")
    if not spotify_id:
        return
    try:
        url = "https://api.reccobeats.com/v1/track"
        respuesta = requests.get(
            url,
            params={"ids": spotify_id},
            timeout=15
        )
        respuesta.raise_for_status()
        resultados = respuesta.json().get("content", [])
        if not resultados:
            return
        cancion_recco = resultados[0]
        recco_id = cancion_recco.get("id")
        if not recco_id:
            return
        #Caracteristicas
        url_audio = (
            f"https://api.reccobeats.com/v1/"
            f"track/{recco_id}/audio-features"
        )
        respuesta_audio = requests.get(
            url_audio,
            timeout=10
        )
        respuesta_audio.raise_for_status()
        datos_audio = respuesta_audio.json()
        return cancion_recco, datos_audio

    except requests.exceptions.RequestException: print("ReccoBeats: error de conexión o respuesta del servicio.")
    except ValueError: print("ReccoBeats: respuesta no válida.")


