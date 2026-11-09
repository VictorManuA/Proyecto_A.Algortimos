import argparse
import json
import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame

from algortimo import conexiones, kruskal
from clasificador import biblioteca
from recorrido import recorrido_profundidad

ANCHO, ALTO = 1360, 820
CONTROLES_ANCHO = 300
PANEL = 340
FONDO = (18, 20, 28)
PANEL_FONDO = (26, 29, 40)
TEXTO = (232, 234, 240)
TEXTO_SUAVE = (140, 146, 165)
ARISTA_TENUE = (60, 66, 88)
PALETA_GENEROS = [(86, 156, 255), (255, 120, 110), (110, 220, 160), (255, 205, 90),
                  (190, 130, 255), (120, 210, 230), (255, 150, 200), (170, 170, 170)]
CONTROLES = ("P ocultar lista",
             "E ocultar aristas",)

AMBIENTES = (
    ("Cualquiera", None), ("Muy tranquilo", (.15, 70, .4)),
    ("Relajado", (.3, 90, .5)), ("Equilibrado", (.5, 110, .55)),
    ("Animado", (.7, 125, .8)), ("Energético", (.9, 145, .75)),
)
RANGOS_ANIMO = (
    None, (0, .25, 0, 90), (0, .45, 0, 110),
    (.3, .7, 80, 140), (.55, 1, 95, 180), (.75, 1, 120, float("inf")),
)

def normalizar_genero(valor):
    texto = " ".join((valor or "").casefold().split())
    return {"rnb": "r&b", "r & b": "r&b", "hip hop": "hip-hop",
            "indie-pop": "indie pop"}.get(texto, texto)

def seleccionar_indices(pool, genero, ambiente, energia_max, bpm_max, cantidad):
    candidatas = []
    objetivo = AMBIENTES[ambiente][1]
    for indice, cancion in enumerate(pool):
        if genero != "Todos" and normalizar_genero(cancion.get("genero")) != normalizar_genero(genero):
            continue
        energia, bpm = cancion.get("energia"), cancion.get("bpm")# El extremo superior permite todos los valores, incluidos los desconocidos.
        if energia_max < 100 and (energia is None or energia > energia_max / 100):
            continue
        if bpm_max < 300 and (bpm is None or bpm > bpm_max):
            continue
        rango = RANGOS_ANIMO[ambiente]
        if rango:
            energia_min, energia_tope, bpm_min, bpm_tope = rango
            if energia is None or bpm is None:
                continue
            if not (energia_min <= energia <= energia_tope and bpm_min <= bpm <= bpm_tope):
                continue
        puntuacion = 0.
        if objetivo:
            for campo, deseado, escala in zip(("energia", "bpm", "valencia"), objetivo, (1, 100, 1)):
                valor = cancion.get(campo)
                if valor is not None and math.isfinite(valor):
                    puntuacion += max(0., 1 - abs(valor - deseado) / escala)
        candidatas.append((indice, puntuacion))
    if objetivo:
        candidatas.sort(key=lambda par: par[1], reverse=True)
    return tuple(indice for indice, _ in candidatas[:cantidad])

class Barra:
    def __init__(self, titulo, y, minimo, maximo, valor, opciones=None):
        self.titulo, self.y = titulo, y
        self.minimo, self.maximo, self.valor = minimo, maximo, valor
        self.opciones = opciones
        self.rect = pygame.Rect(24, y + 32, CONTROLES_ANCHO - 48, 12)

    def actualizar(self, x):
        proporcion = max(0., min(1., (x - self.rect.left) / self.rect.width))
        self.valor = round(self.minimo + proporcion * (self.maximo - self.minimo))

    def texto(self):
        if self.opciones:
            return self.opciones[self.valor]
        if self.titulo == "Energía máxima":
            return "Sin límite" if self.valor == 100 else f"{self.valor}%"
        if self.titulo == "BPM máximo":
            return "Sin límite" if self.valor == 300 else f"{self.valor} BPM"
        return str(self.valor)

    def dibujar(self, pantalla, fuentes):
        chica, media, _ = fuentes
        pantalla.blit(media.render(self.titulo, True, TEXTO), (24, self.y))
        valor = chica.render(recortar(self.texto(), chica, 250), True, TEXTO)
        pantalla.blit(valor, (24, self.y + 55))
        pygame.draw.rect(pantalla, (55, 57, 66), self.rect, border_radius=6)
        amplitud = self.maximo - self.minimo
        proporcion = (self.valor - self.minimo) / amplitud if amplitud else 0
        x = self.rect.left + round(proporcion * self.rect.width)
        pygame.draw.circle(pantalla, TEXTO, (x, self.rect.centery), 10)

class Preferencias:
    def __init__(self, pool, cantidad):
        generos = {normalizar_genero(c.get("genero")) for c in pool}
        generos.discard("")
        self.sin_genero = sum(not normalizar_genero(c.get("genero")) for c in pool)
        self.generos = ["Todos", *sorted(generos)]
        self.barras = [
            Barra("Género musical", 150, 0, len(self.generos) - 1, 0, self.generos),
            Barra("Estado de ánimo", 250, 0, len(AMBIENTES) - 1, 0, [a[0] for a in AMBIENTES]),
            Barra("Energía máxima", 350, 0, 100, 100),
            Barra("BPM máximo", 450, 40, 300, 300),
            Barra("Cantidad de canciones", 550, 1, max(1, len(pool)), max(1, cantidad)),
        ]
        self.activa = None

    def valores(self):
        return tuple(barra.valor for barra in self.barras)

    def seleccionar(self, pool):
        genero, ambiente, energia, bpm, cantidad = self.valores()
        return seleccionar_indices(pool, self.generos[genero], ambiente, energia, bpm, cantidad)

    def evento(self, evento):
        if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            self.activa = next((barra for barra in self.barras
                                if barra.rect.inflate(20, 24).collidepoint(evento.pos)), None)
            if self.activa:
                self.activa.actualizar(evento.pos[0])
        elif evento.type == pygame.MOUSEMOTION and self.activa:
            self.activa.actualizar(evento.pos[0])
        elif evento.type == pygame.MOUSEBUTTONUP and evento.button == 1:
            self.activa = None

    def dibujar(self, pantalla, fuentes, total, seleccionadas):
        chica, media, grande = fuentes
        pygame.draw.rect(pantalla, PANEL_FONDO, (0, 0, CONTROLES_ANCHO, ALTO))
        pantalla.blit(grande.render("FILTROS", True, TEXTO), (24, 24))
        pantalla.blit(media.render("Mis canciones favoritas", True, TEXTO), (24, 72))
        pantalla.blit(chica.render(f"{total} canciones cargadas", True, TEXTO_SUAVE), (24, 102))
        for barra in self.barras:
            barra.dibujar(pantalla, fuentes)


def construir_grafo(canciones):
    candidatas = conexiones(canciones)
    return candidatas, kruskal(canciones, candidatas)

def color_peso(peso):
    t = max(0.0, min(1.0, peso / 100.0))
    if t < 0.5:
        a, b, u = (70, 220, 140), (250, 210, 80), t / 0.5
    else:
        a, b, u = (250, 210, 80), (240, 80, 80), (t - 0.5) / 0.5
    return tuple(int(a[k] + (b[k] - a[k]) * u) for k in range(3))

def recortar(texto, fuente, ancho_max):
    if fuente.size(texto)[0] <= ancho_max:
        return texto
    while texto and fuente.size(texto + "…")[0] > ancho_max:
        texto = texto[:-1]
    return texto + "…"

def punto_medio(a, b):
    return (a[0] + b[0]) / 2, (a[1] + b[1]) / 2

def etiqueta(pantalla, fuente, texto, centro, color, fondo=False):
    img = fuente.render(texto, True, TEXTO if fondo else color)
    rect = img.get_rect(center=centro)
    if fondo:
        caja = rect.inflate(8, 4)
        pygame.draw.rect(pantalla, FONDO, caja, border_radius=5)
        pygame.draw.rect(pantalla, color, caja, 1, border_radius=5)
    pantalla.blit(img, rect)

class Escena:
    def __init__(self, pool, n, area):
        self.area = area  # pygame.Rect donde vive el grafo
        self.canciones = pool[:n]
        self.n = len(self.canciones)
        self.candidatas, self.elegidas = construir_grafo(self.canciones)
        self.grupos = recorrido_profundidad(self.canciones, self.elegidas)
        self.orden = [i for grupo in self.grupos for i in grupo]
        self.numero_dfs = {i: pos for pos, i in enumerate(self.orden, 1)}
        self.grupo_dfs = {i: num for num, grupo in enumerate(self.grupos, 1) for i in grupo}
        self.total = sum(c.peso for c in self.elegidas)
        self.radio = int(max(11, min(26, 300 / max(self.n, 1))))
        self.ver_playlist = True
        self.mostrar_tenues = True
        self.inicio_lista = 0
        self.generos = {}
        for c in self.canciones:
            g = c.get("genero") or "desconocido"
            self.generos.setdefault(g, PALETA_GENEROS[len(self.generos) % len(PALETA_GENEROS)])
        self.posiciones = self.circulo()

    def circulo(self):
        cx, cy = self.area.center
        r = min(self.area.width, self.area.height) / 2 - self.radio - 70
        posiciones = [None] * self.n
        for pos, i in enumerate(self.orden):
            ang = -math.pi / 2 + 2 * math.pi * pos / max(self.n, 1)
            posiciones[i] = [cx + r * math.cos(ang), cy + r * math.sin(ang)]
        return posiciones

    def nodo_en(self, pos):
        for i in reversed(range(self.n)):
            x, y = self.posiciones[i]
            if (pos[0] - x) ** 2 + (pos[1] - y) ** 2 <= (self.radio + 4) ** 2:
                return i
        return None

    def dibujar(self, pantalla, f_chica, hover):
        vecinos = set()
        if hover is not None:
            for i, j, _, _ in self.candidatas:
                if i == hover:
                    vecinos.add(j)
                elif j == hover:
                    vecinos.add(i)

        if self.mostrar_tenues:        # 1) aristas candidatas (tenues; las del nodo bajo el cursor se resaltan)
            for i, j, peso, _ in self.candidatas:
                destacada = hover in (i, j)
                color = color_peso(peso) if destacada else ARISTA_TENUE
                pygame.draw.line(pantalla, color, self.posiciones[i], self.posiciones[j],
                                 2 if destacada else 1)
                if destacada:
                    etiqueta(pantalla, f_chica, f"{peso:.1f}",
                             punto_medio(self.posiciones[i], self.posiciones[j]), color)

        # 2) aristas del árbol mínimo (gruesas)
        for c in self.elegidas:
            pygame.draw.line(pantalla, color_peso(c.peso),
                             self.posiciones[c.origen], self.posiciones[c.destino], 4)

        # 3) nodos
        centro = self.area.center
        for i, cancion in enumerate(self.canciones):
            x, y = self.posiciones[i]
            r = self.radio
            color = self.generos[cancion.get("genero") or "desconocido"]
            if i == hover:
                pygame.draw.circle(pantalla, TEXTO, (x, y), r + 5, 2)
            elif i in vecinos:
                pygame.draw.circle(pantalla, TEXTO_SUAVE, (x, y), r + 4, 1)
            pygame.draw.circle(pantalla, color, (x, y), r)
            pygame.draw.circle(pantalla, FONDO, (x, y), r, 2)
            num = f_chica.render(str(self.numero_dfs[i]), True, (15, 15, 20))
            pantalla.blit(num, num.get_rect(center=(x, y)))
            if self.n <= 12 or i == hover:
                titulo = recortar(cancion.get("titulo", "?"), f_chica, 150)
                txt = f_chica.render(titulo, True, TEXTO)
                dx, dy = x - centro[0], y - centro[1]  # el título se coloca hacia afuera del círculo
                norm = math.hypot(dx, dy) or 1
                ux, uy = dx / norm, dy / norm
                tx = x + ux * (r + 8 + txt.get_width() / 2 * abs(ux))
                ty = y + uy * (r + 8 + txt.get_height() / 2 * max(abs(uy), 0.6))
                rect = txt.get_rect(center=(tx, ty))
                rect.clamp_ip(self.area)
                pantalla.blit(txt, rect)
        for c in self.elegidas:
            etiqueta(pantalla, f_chica, f"{c.peso:.1f}",
                     punto_medio(self.posiciones[c.origen], self.posiciones[c.destino]),
                     color_peso(c.peso), fondo=True)


def dibujar_panel(pantalla, fuentes, escena, hover, pool_total):
    f_chica, f_media, f_grande = fuentes
    x0 = ANCHO - PANEL
    pygame.draw.rect(pantalla, PANEL_FONDO, (x0, 0, PANEL, ALTO))
    x, y = x0 + 20, 18
    ancho = PANEL - 40
    def linea(texto, fuente=f_media, color=TEXTO):
        nonlocal y
        pantalla.blit(fuente.render(recortar(texto, fuente, ancho), True, color), (x, y))
        y += fuente.get_linesize() + 3
    linea("Grafo", f_grande)
    y += 4
    linea(f"Nodos (canciones): {escena.n} de {pool_total}")
    linea(f"Aristas elegidas:  {len(escena.elegidas)}   (n - 1)")
    linea(f"Peso total del árbol: {escena.total:.1f}")
    if escena.ver_playlist:
        linea("\nOrden de reproduccion", f_grande)
        y += 8
        for i in escena.orden[escena.inicio_lista:escena.inicio_lista + 10]:
            cancion = escena.canciones[i]
            linea(f"{escena.numero_dfs[i]}. {cancion.get('titulo') or '?'}",
                  f_media, (86, 156, 255) if i == hover else TEXTO)
            detalle = cancion.get("artista") or "Artista desconocido"
            if len(escena.grupos) > 1:
                detalle = f"Grupo {escena.grupo_dfs[i]} · {detalle}"
            linea(detalle, f_chica, TEXTO_SUAVE)
            y += 6
    else:
        # leyenda de géneros
        linea("Color del nodo = género", f_chica, TEXTO_SUAVE)
        for genero, color in escena.generos.items():
            pygame.draw.circle(pantalla, color, (x + 7, y + 8), 6)
            pantalla.blit(f_chica.render(genero, True, TEXTO), (x + 22, y))
            y += f_chica.get_linesize() + 1
        y += 6
        # leyenda de pesos
        linea("Color de arista = peso", f_chica, TEXTO_SUAVE)
        for k in range(ancho):
            pygame.draw.line(pantalla, color_peso(100 * k / ancho), (x + k, y), (x + k, y + 8))
        y += 12
        pantalla.blit(f_chica.render("0 parecidas", True, TEXTO_SUAVE), (x, y))
        d = f_chica.render("100 distintas", True, TEXTO_SUAVE)
        pantalla.blit(d, (x + ancho - d.get_width(), y))
        y += 26

        # detalle de la canción bajo el cursor
        pygame.draw.line(pantalla, ARISTA_TENUE, (x, y), (x + ancho, y))
        y += 10
        if hover is None:
            linea("Pasa el cursor sobre un nodo", f_chica, TEXTO_SUAVE)
        else:
            c = escena.canciones[hover]
            linea(f"{escena.numero_dfs[hover]}. {c.get('titulo', '?')}")
            linea(c.get("artista") or "Artista desconocido", f_chica, TEXTO_SUAVE)
            linea(f"género = {c.get('genero') or 'desconocido'}", f_chica)
            for campo in ("bpm", "energia", "densidad", "brillo", "valencia"):
                v = c.get(campo)
                texto = "desconocido" if v is None else (f"{v:.0f}" if campo == "bpm" else f"{v:.2f}")
                linea(f"{campo} = {texto}", f_chica)
            y += 4
            linea("Conectada en el árbol con:", f_chica, TEXTO_SUAVE)
            for cn in escena.elegidas:
                if hover in (cn.origen, cn.destino):
                    otro = cn.destino if cn.origen == hover else cn.origen
                    linea(f"  #{escena.numero_dfs[otro]}  (peso {cn.peso:.1f})", f_chica)

    textos = (("",) if escena.ver_playlist else ()) + CONTROLES
    y = ALTO - 20 - f_chica.get_linesize() * len(textos)
    pygame.draw.line(pantalla, ARISTA_TENUE, (x, y - 8), (x + ancho, y - 8))
    for t in textos:
        pantalla.blit(f_chica.render(t, True, TEXTO_SUAVE), (x, y))
        y += f_chica.get_linesize()

def cargar_fuentes():
    nombre = pygame.font.match_font("helveticaneue,helvetica,arial,segoeui,dejavusans,liberationsans")
    return pygame.font.Font(nombre, 14), pygame.font.Font(nombre, 17), pygame.font.Font(nombre, 24)

def mostrar_grafo(pool, cantidad=None):
    pygame.init()
    pygame.display.set_caption("Grafo de favoritos")
    pantalla = pygame.display.set_mode((ANCHO, ALTO))
    reloj = pygame.time.Clock()
    fuentes = cargar_fuentes()
    area = pygame.Rect(CONTROLES_ANCHO, 0, ANCHO - PANEL - CONTROLES_ANCHO, ALTO)
    n = min(len(pool), max(1, cantidad if cantidad is not None else len(pool)))
    preferencias = Preferencias(pool, n)
    indices = preferencias.seleccionar(pool)
    escena = Escena([pool[i] for i in indices], len(indices), area)
    valores_anteriores = preferencias.valores()
    arrastrando = None
    corriendo = True
    estado_anterior = None

    while corriendo:
        reloj.tick(30)
        for ev in pygame.event.get():
            preferencias.evento(ev)
            if ev.type in (pygame.WINDOWEXPOSED, pygame.WINDOWRESTORED):
                estado_anterior = None
            if ev.type == pygame.QUIT:
                corriendo = False
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    corriendo = False
                elif ev.key == pygame.K_p:
                    escena.ver_playlist = not escena.ver_playlist
                elif ev.key == pygame.K_e:
                    escena.mostrar_tenues = not escena.mostrar_tenues
            elif ev.type == pygame.MOUSEWHEEL:
                if escena.ver_playlist and pygame.mouse.get_pos()[0] >= ANCHO - PANEL:
                    escena.inicio_lista = max(0, min(max(0, escena.n - 7), escena.inicio_lista - ev.y))
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                arrastrando = escena.nodo_en(ev.pos) if area.collidepoint(ev.pos) else None
            elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
                arrastrando = None
            elif ev.type == pygame.MOUSEMOTION and arrastrando is not None:
                escena.posiciones[arrastrando] = [
                    max(area.left + 20, min(area.right - 20, ev.pos[0])),
                    max(area.top + 20, min(area.bottom - 20, ev.pos[1]))]

        valores = preferencias.valores()
        if valores != valores_anteriores:
            nuevos = preferencias.seleccionar(pool)
            if nuevos != indices:
                nueva = Escena([pool[i] for i in nuevos], len(nuevos), area)
                nueva.ver_playlist = escena.ver_playlist
                nueva.mostrar_tenues = escena.mostrar_tenues
                escena, indices = nueva, nuevos
                arrastrando = None
            valores_anteriores = valores
        hover = arrastrando if arrastrando is not None else escena.nodo_en(pygame.mouse.get_pos())
        estado = (id(escena), hover, escena.ver_playlist, escena.mostrar_tenues,
                  escena.inicio_lista, tuple(map(tuple, escena.posiciones)), valores)
        if estado == estado_anterior:
            continue
        estado_anterior = estado
        pantalla.fill(FONDO)
        escena.dibujar(pantalla, fuentes[0], hover)
        if not indices:
            texto = fuentes[1].render("No hay musica con este filtro", True, TEXTO)
            pantalla.blit(texto, texto.get_rect(center=area.center))
        dibujar_panel(pantalla, fuentes, escena, hover, len(pool))
        preferencias.dibujar(pantalla, fuentes, len(pool), len(indices))
        pygame.display.flip()

    pygame.quit()

def lanzar_grafo(canciones, cantidad):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(canciones, f, ensure_ascii=False)
        ruta = f.name
    carpeta = os.path.dirname(os.path.abspath(__file__))
    return subprocess.Popen(
        [sys.executable, os.path.abspath(__file__), "--json", ruta, "--n", str(cantidad)],
        cwd=carpeta)

def principal():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", help="archivo JSON con canciones ya clasificadas")
    ap.add_argument("--audios", type=Path, help="carpeta de audios locales para completar características")
    ap.add_argument("--n", type=int, help="cuántas canciones dibujar")
    args = ap.parse_args()

    if args.n is not None and args.n < 1:
        ap.error("--n debe ser mayor que cero")
    if args.audios and not args.audios.is_dir():
        ap.error("--audios debe indicar una carpeta existente")
    if args.audios and args.json:
        ap.error("--audios se utiliza al cargar la biblioteca de Spotify")

    if args.json:
        with open(args.json, encoding="utf-8") as archivo:
            pool = json.load(archivo)
    else:
        from requests.exceptions import RequestException
        from spotipy.exceptions import SpotifyException, SpotifyOauthError
        print("-Cargando canciones-", flush=True)
        pool = []
        try:
            for cancion in biblioteca(args.audios):
                pool.append(cancion)
        except (SpotifyException, SpotifyOauthError, RequestException, OSError) as error:
            print(f"Error: ({type(error).__name__}). "
                  "No hay Intenet", file=sys.stderr)
            if not pool:
                return 1
            print(f"Carga parcial: {len(pool)} canciones.", flush=True)
    if not pool:
        print("No hay canciones")
        return 0
    print(f"Carga terminada: {len(pool)} canciones.", flush=True)
    mostrar_grafo(pool, args.n)
    return 0

if __name__ == "__main__":
    sys.exit(principal())