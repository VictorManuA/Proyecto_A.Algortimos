from algortimo import kruskal
from clasificador import biblioteca

def recorrido_profundidad(canciones, conexiones):#Devuelve los índices visitados por DFS, agrupados por componente
    vecinos = [[] for _ in canciones]
    for c in conexiones:
        vecinos[c.origen].append(c.destino)
        vecinos[c.destino].append(c.origen)
    visitados = set()
    grupos = []
    for inicio in range(len(canciones)):
        if inicio in visitados:
            continue
        grupo = []
        pendientes = [inicio]
        while pendientes:
            actual = pendientes.pop()
            if actual in visitados:
                continue
            visitados.add(actual)
            grupo.append(actual)# La pila procesa primero la conexión que Kruskal seleccionó antes.
            pendientes.extend(reversed(vecinos[actual]))
        grupos.append(grupo)
    return grupos

def resultados(canciones):#Presenta las conexiones elegidas y la secuencia de canciones por componente
    canciones = list(canciones)
    conexiones = kruskal(canciones)
    grupos = recorrido_profundidad(canciones, conexiones)
    lineas = ["Conexiones de Kruskal (números originales de la biblioteca)"]
    for c in conexiones:
        lineas.append(f"#{c.origen + 1} ↔ #{c.destino + 1} | peso {c.peso:.2f} | cobertura {c.cobertura:.0%}")
    if not conexiones:
        lineas.append("Sin conexiones")
    lineas.append(f"Peso total de las conexiones elegidas: {sum(c.peso for c in conexiones):.2f}")
    lineas.append("\nPlaylist en orden de visita DFS")
    for numero, grupo in enumerate(grupos, 1):
        if len(grupos) > 1:
            lineas.append(f"Grupo {numero}")
        for posicion, i in enumerate(grupo, 1):
            cancion = canciones[i]
            lineas.append(f"{posicion}. {cancion['titulo']} · {cancion['artista'] or 'Artista desconocido'} (#{i + 1})")
    return "\n".join(lineas)

if __name__ == "__main__":
    from requests.exceptions import RequestException
    from spotipy.exceptions import SpotifyException, SpotifyOauthError

    print("Cargando canciones", flush=True)
    try:
        canciones = list(biblioteca())
        grupos = recorrido_profundidad(canciones, kruskal(canciones))
        print(f"Recorrido listo: {len(canciones)} canciones, {len(grupos)} grupos.")
    except (RequestException, SpotifyException, SpotifyOauthError, OSError) as error:
        print(f"Error de carga ({type(error).__name__})No hay internet")
        raise SystemExit(1)
