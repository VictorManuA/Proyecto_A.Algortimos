def recorrido_profundidad(canciones, conexiones):
    n = len(canciones)
    vecinos = [[] for _ in canciones]
    for c in conexiones:
        vecinos[c.origen].append(c.destino)
        vecinos[c.destino].append(c.origen)
    visitados = [False] * n

    def visitar(actual, grupo):
        visitados[actual] = True
        grupo.append(actual)
        for vecino in vecinos[actual]:
            if not visitados[vecino]:
                visitar(vecino, grupo)

    grupos = []
    for inicio in range(n):
        if not visitados[inicio]:
            grupo = []
            visitar(inicio, grupo)
            grupos.append(grupo)
    return grupos
