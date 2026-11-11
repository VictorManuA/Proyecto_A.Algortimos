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
    n = len(canciones)
    grupos = list(range(n))
    elegidas = []
    for conexion in sorted(candidatas, key=lambda c: c.peso):
        a = grupos[conexion.origen]
        b = grupos[conexion.destino]
        if a != b:
            elegidas.append(conexion)
            for i in range(n):
                if grupos[i] == b:
                    grupos[i] = a
    return elegidas
