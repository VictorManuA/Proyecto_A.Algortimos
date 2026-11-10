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