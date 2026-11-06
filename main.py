import requests
import json
import spotipy
from spotipy.oauth2 import SpotifyOAuth

def crear_cliente():
    """Abre el cliente de lectura de Spotify del proyecto."""
    return spotipy.Spotify(
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
        print("No ID de spotify")
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
            print("No se encontró en Recco")
            return

        cancion_recco = resultados[0]
        recco_id = cancion_recco.get("id")

        if not recco_id:
            print("No se obtuvo el ID de ReccoBeats.")
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

    except requests.exceptions.RequestException:
        print("ReccoBeats: consulta fallida.")
    except ValueError:
        print("ReccoBeats: respuesta no válida.")

if __name__ == "__main__":
    control = crear_cliente()
    results = control.current_user_saved_tracks(limit=20)

    for idx, item in enumerate(results["items"], start=1):

        track = item["track"]
        if not track: continue
        print("\n" + "=" * 55)
        print(f"CANCIÓN {idx}")
        print("Artista:", track["artists"][0]["name"])
        print("Título:", track["name"])
        print("Spotify ID:", track["id"])
        resultado = buscar_reccobeats(track)
        if resultado:
            for etiqueta, datos in zip(("DATOS GENERALES RECCOBEATS", "CARACTERÍSTICAS ACÚSTICAS"), resultado):
                print(etiqueta, json.dumps(datos, indent=4, ensure_ascii=False), sep="\n")
        print("=" * 55)
