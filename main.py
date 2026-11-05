import spotipy
from spotipy.oauth2 import SpotifyOAuth

control = spotipy.Spotify(
    auth_manager=SpotifyOAuth(
        client_id="fe91e7167ff7470a9be408d2dd1788bb",#Identificador de la aplicacion
        client_secret="8439288bab2d48ca9c6ebf9655fad87a",#Contraseña
        redirect_uri="http://127.0.0.1:9090",
        scope="user-library-read"#Solo permisos de lectura
    )
)

results = control.current_user_saved_tracks(limit=10)
for idx, item in enumerate(results['items']):
    track = item['track']
    print(idx +1, track['artists'][0]['name'], " – ", track['name'])