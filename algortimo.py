from itertools import combinations
from typing import NamedTuple
from clasificador import arista

class Conexion(NamedTuple):
    origen: int
    destino: int
    peso: float
    cobertura: float

def conexiones(canciones):
    indices = range(len(canciones))
    candidatas = []
    for i, j in combinations(indices, 2):
        peso, cobertura = arista(canciones[i], canciones[j])
        if peso is not None:
            candidatas.append(Conexion(i, j, peso, cobertura))
    return candidatas

def kruskal(canciones, candidatas=None):
    if candidatas is None:
        candidatas = conexiones(canciones)
    padres = list(range(len(canciones)))
    tamanos = [1] * len(canciones)
    def raiz(i):
        while i != padres[i]:
            padres[i] = padres[padres[i]]
            i = padres[i]
        return i
    elegidas = []    # El orden estable conserva el orden original de los pares en los empates.
    for conexion in sorted(candidatas, key=lambda c: c.peso):
        a, b = raiz(conexion.origen), raiz(conexion.destino)
        if a == b:
            continue
        if tamanos[a] < tamanos[b]:
            a, b = b, a
        padres[b] = a
        tamanos[a] += tamanos[b]
        elegidas.append(conexion)
        if len(elegidas) == len(canciones) - 1:
            break
    return elegidas
