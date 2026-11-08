import argparse
import json
import math
import os
import random
import subprocess
import sys
import tempfile
import pygame

from pathlib import Path
from itertools import combinations
from recorrido import recorrido_profundidad

ANCHO, ALTO = 1200, 760
PANEL = 340         
FONDO = (18, 20, 28)
PANEL_FONDO = (26, 29, 40)
TEXTO = (232, 234, 240)
TEXTO_SUAVE = (140, 146, 165)
ARISTA_TENUE = (60, 66, 88)
PALETA_GENEROS = [(86, 156, 255), 
                 (255, 120, 110),
                 (110, 220, 160),
                 (255, 205, 90),
                 (190, 130, 255),
                 (120, 210, 230),
                 (255, 150, 200),
                 (170, 170, 170)]


# 1. Datos: construir el grafo con TU código existente
def construir_grafo(canciones):
    """Devuelve (candidatas, elegidas).
    candidatas: todas las aristas con peso calculable, como (i, j, peso, cobertura)
    elegidas:   las aristas del árbol mínimo que devuelve tu kruskal()
    """
    from algortimo import kruskal
    from clasificador import arista

    candidatas = []
    for i, j in combinations(range(len(canciones)), 2):
        peso, cobertura = arista(canciones[i], canciones[j])
        if peso is not None:  # mismo criterio que usa kruskal()
            candidatas.append((i, j, peso, cobertura))

    elegidas = kruskal(canciones) if len(canciones) > 1 else []
    return candidatas, elegidas


def generar_demo(n, semilla=7):
    """Canciones inventadas con el mismo formato que produce clasificador.clasificar()."""
    azar = random.Random(semilla)
    generos = ["rock", "hard rock", "pop", "jazz", "classical"]
    palabras = ["Luz", "Mar", "Noche", "Lluvia", "Norte", "Fuego", "Sombra", "Viento",
                "Ciudad", "Sueño", "Eco", "Tierra", "Cristal", "Neón", "Ruta"]
    artistas = ["Mar Abierto", "Norte", "Luna Azul", "Casa Vieja", "Delta", "Aurora"]
    canciones = []
    for i in range(n):
        canciones.append({
            "titulo": f"{azar.choice(palabras)} {azar.choice(palabras).lower()} {i + 1}",
            "artista": azar.choice(artistas),
            "genero": azar.choice(generos),
            "bpm": round(azar.uniform(65, 170), 1),
            "energia": round(azar.random(), 3),
            "densidad": round(azar.random(), 3),
            "brillo": round(azar.random(), 3),
            "valencia": round(azar.random(), 3),
        })
    return canciones

#Dibujo del GRAFO
def color_peso(peso):
    """Verde (peso bajo = parecidas) -> amarillo -> rojo (peso alto)."""
    t = max(0.0, min(1.0, peso / 100.0))
    if t < 0.5:
        a, b, u = (70, 220, 140), (250, 210, 80), t / 0.5
    else:
        a, b, u = (250, 210, 80), (240, 80, 80), (t - 0.5) / 0.5
    return tuple(int(a[k] + (b[k] - a[k]) * u) for k in range(3))

def suavizar(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)

def recortar(texto, fuente, ancho_max):
    if fuente.size(texto)[0] <= ancho_max:
        return texto
    while texto and fuente.size(texto + "…")[0] > ancho_max:
        texto = texto[:-1]
    return texto + "…"


class Escena:
    """Un grafo concreto: n canciones -> n nodos, con su animación."""
    def __init__(self, pool, n, area):
        self.pool = pool
        self.n = max(0, min(n, len(pool)))
        n = self.n
        self.area = area                     # pygame.Rect donde vive el grafo
        self.canciones = pool[:n]
        self.candidatas, self.elegidas = construir_grafo(self.canciones)
        self.grupos = recorrido_profundidad(self.canciones, self.elegidas)
        self.orden = [i for grupo in self.grupos for i in grupo]
        self.numero_dfs = {i: posicion for posicion, i in enumerate(self.orden, 1)}
        self.grupo_dfs = {i: numero for numero, grupo in enumerate(self.grupos, 1) for i in grupo}
        self.ver_playlist = True
        self.inicio_lista = 0
        self.total = sum(c.peso for c in self.elegidas)
        self.conexo = len(self.elegidas) == max(0, n - 1)
        self.mostrar_tenues = True
        self.radio = int(max(11, min(26, 300 / max(n, 1))))
        self.generos = {}
        for c in self.canciones:
            g = c.get("genero") or "desconocido"
            self.generos.setdefault(g, PALETA_GENEROS[len(self.generos) % len(PALETA_GENEROS)])
        self.en_circulo = True
        self.posiciones = []
        self.circulo()
        self.reiniciar()

    # --- posiciones -------------------------------------------------------
    def circulo(self):
        cx, cy = self.area.center
        r = min(self.area.width, self.area.height) / 2 - self.radio - 70
        self.posiciones = [None] * self.n
        for posicion, i in enumerate(self.orden):
            ang = -math.pi / 2 + 2 * math.pi * posicion / max(self.n, 1)
            self.posiciones[i] = [cx + r * math.cos(ang), cy + r * math.sin(ang)]

    def fuerzas(self, iteraciones=400):
        """Acomoda los nodos para que las aristas del árbol sean más cortas
        cuanto menor sea su peso (canciones parecidas quedan cerca)."""
        if self.n <= 1:
            self.circulo()
            return
        azar = random.Random(1)
        cx, cy = self.area.center
        pos = [[cx + azar.uniform(-60, 60), cy + azar.uniform(-60, 60)] for _ in range(self.n)]
        k = math.sqrt(self.area.width * self.area.height / max(self.n, 1)) * 0.75
        maximo = max([c.peso for c in self.elegidas], default=1) or 1
        for it in range(iteraciones):
            paso = 25 * (1 - it / iteraciones) + 1
            mov = [[0.0, 0.0] for _ in range(self.n)]
            for i, j in combinations(range(self.n), 2):
                dx, dy = pos[i][0] - pos[j][0], pos[i][1] - pos[j][1]
                d = max(math.hypot(dx, dy), 0.01)
                f = k * k / d / 12
                mov[i][0] += dx / d * f; mov[i][1] += dy / d * f
                mov[j][0] -= dx / d * f; mov[j][1] -= dy / d * f
            for c in self.elegidas:
                i, j = c.origen, c.destino
                dx, dy = pos[j][0] - pos[i][0], pos[j][1] - pos[i][1]
                d = max(math.hypot(dx, dy), 0.01)
                ideal = k * (0.35 + 0.9 * c.peso / maximo)
                f = (d - ideal) * 0.25
                mov[i][0] += dx / d * f; mov[i][1] += dy / d * f
                mov[j][0] -= dx / d * f; mov[j][1] -= dy / d * f
            for i in range(self.n):
                m = math.hypot(*mov[i]) or 1
                lim = min(m, paso)
                pos[i][0] += mov[i][0] / m * lim
                pos[i][1] += mov[i][1] / m * lim
        # encajar en el área, dejando margen para los títulos
        margen = self.radio + 70
        xs, ys = [p[0] for p in pos], [p[1] for p in pos]
        ancho_g, alto_g = (max(xs) - min(xs)) or 1, (max(ys) - min(ys)) or 1
        esc = min((self.area.width - 2 * margen) / ancho_g, (self.area.height - 2 * margen) / alto_g)
        mx, my = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
        self.posiciones = [[cx + (p[0] - mx) * esc, cy + (p[1] - my) * esc] for p in pos]

    # --- animación --------------------------------------------------------
    def reiniciar(self):
        self.t = 0.0
        self.t_nodo = min(0.12, 1.4 / max(self.n, 1))                 # entre nodo y nodo
        self.t_arista = min(0.45, 3.5 / max(len(self.elegidas), 1))   # entre arista y arista
        self.inicio_aristas = self.t_nodo * self.n + 0.4

    def avanzar(self, dt):
        self.t += dt

    def progreso_nodo(self, i):
        return suavizar((self.t - (self.numero_dfs[i] - 1) * self.t_nodo) / 0.35)

    def progreso_arista(self, k):
        return suavizar((self.t - self.inicio_aristas - k * self.t_arista) / 0.45)

    # --- interacción ------------------------------------------------------
    def nodo_en(self, pos):
        for i in reversed(range(self.n)):
            x, y = self.posiciones[i]
            if (pos[0] - x) ** 2 + (pos[1] - y) ** 2 <= (self.radio + 4) ** 2:
                return i
        return None

    # --- dibujo -----------------------------------------------------------
    def dibujar(self, pantalla, fuentes, hover):
        f_chica, f_media, _ = fuentes
        vecinos = set()
        if hover is not None:
            for (i, j, _, _) in self.candidatas:
                if i == hover:
                    vecinos.add(j)
                elif j == hover:
                    vecinos.add(i)

        # 1) aristas candidatas (tenues)
        if self.mostrar_tenues:
            alpha = suavizar((self.t - self.inicio_aristas) / 0.6)
            for (i, j, peso, _) in self.candidatas:
                if self.progreso_nodo(i) < 1 or self.progreso_nodo(j) < 1:
                    continue
                destacada = hover in (i, j)
                if destacada:
                    color, ancho = color_peso(peso), 2
                else:
                    base = 0.25 + 0.75 * alpha
                    color = tuple(int(FONDO[k] + (ARISTA_TENUE[k] - FONDO[k]) * base) for k in range(3))
                    ancho = 1
                pygame.draw.line(pantalla, color, self.posiciones[i], self.posiciones[j], ancho)
                if destacada:
                    mx = (self.posiciones[i][0] + self.posiciones[j][0]) / 2
                    my = (self.posiciones[i][1] + self.posiciones[j][1]) / 2
                    etiqueta(pantalla, f_chica, f"{peso:.1f}", (mx, my), color)

        # 2) aristas del árbol mínimo (gruesas, animadas)
        for k, c in enumerate(self.elegidas):
            p = self.progreso_arista(k)
            if p <= 0:
                continue
            a, b = self.posiciones[c.origen], self.posiciones[c.destino]
            fin = (a[0] + (b[0] - a[0]) * p, a[1] + (b[1] - a[1]) * p)
            color = color_peso(c.peso)
            pygame.draw.line(pantalla, color, a, fin, 4)

        # 3) nodos
        for i, cancion in enumerate(self.canciones):
            p = self.progreso_nodo(i)
            if p <= 0:
                continue
            x, y = self.posiciones[i]
            r = max(2, int(self.radio * p))
            color = self.generos[cancion.get("genero") or "desconocido"]
            if i == hover:
                pygame.draw.circle(pantalla, TEXTO, (x, y), r + 5, 2)
            elif i in vecinos:
                pygame.draw.circle(pantalla, TEXTO_SUAVE, (x, y), r + 4, 1)
            pygame.draw.circle(pantalla, color, (x, y), r)
            pygame.draw.circle(pantalla, FONDO, (x, y), r, 2)
            if p > 0.8:
                num = f_chica.render(str(self.numero_dfs[i]), True, (15, 15, 20))
                pantalla.blit(num, num.get_rect(center=(x, y)))
                if self.n <= 12 or i == hover:
                    titulo = recortar(cancion.get("titulo", "?"), f_chica, 150)
                    txt = f_chica.render(titulo, True, TEXTO)
                    # el título se coloca hacia afuera del círculo
                    cx, cy = self.area.center
                    dx, dy = x - cx, y - cy
                    norm = math.hypot(dx, dy) or 1
                    ux, uy = dx / norm, dy / norm
                    tx = x + ux * (r + 8 + txt.get_width() / 2 * abs(ux))
                    ty = y + uy * (r + 8 + txt.get_height() / 2 * max(abs(uy), 0.6))
                    rect = txt.get_rect(center=(tx, ty))
                    rect.clamp_ip(self.area)
                    pantalla.blit(txt, rect)

        # 4) pesos de las aristas elegidas (encima de todo para que se lean)
        for k, c in enumerate(self.elegidas):
            if self.progreso_arista(k) >= 1:
                a, b = self.posiciones[c.origen], self.posiciones[c.destino]
                etiqueta(pantalla, f_chica, f"{c.peso:.1f}", ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2),
                         color_peso(c.peso), fondo=True)


def etiqueta(pantalla, fuente, texto, centro, color, fondo=False):
    img = fuente.render(texto, True, color if not fondo else TEXTO)
    rect = img.get_rect(center=centro)
    if fondo:
        caja = rect.inflate(8, 4)
        pygame.draw.rect(pantalla, FONDO, caja, border_radius=5)
        pygame.draw.rect(pantalla, color, caja, 1, border_radius=5)
    pantalla.blit(img, rect)


def dibujar_panel(pantalla, fuentes, escena, hover, pool_total):
    f_chica, f_media, f_grande = fuentes
    x0 = ANCHO - PANEL
    pygame.draw.rect(pantalla, PANEL_FONDO, (x0, 0, PANEL, ALTO))
    x, y = x0 + 20, 18
    ancho = PANEL - 40

    def linea(texto, fuente=f_media, color=TEXTO, salto=None):
        nonlocal y
        pantalla.blit(fuente.render(recortar(texto, fuente, ancho), True, color), (x, y))
        y += salto or fuente.get_linesize() + 3

    linea("Grafo de la playlist", f_grande)
    y += 4
    linea(f"Nodos (canciones): {escena.n} de {pool_total}")
    linea(f"Aristas posibles:  {len(escena.candidatas)}")
    linea(f"Aristas elegidas:  {len(escena.elegidas)}   (n - 1)")
    linea(f"Peso total del árbol: {escena.total:.1f}", color=color_peso(escena.total / max(len(escena.elegidas), 1)))
    if escena.elegidas:
        linea(f"Peso promedio por arista: {escena.total / len(escena.elegidas):.1f}", f_chica, TEXTO_SUAVE)
    if not escena.conexo:
        linea("Aviso: faltan datos para conectar todo", f_chica, (255, 190, 90))
    y += 10

    if escena.ver_playlist:
        linea("Playlist · orden DFS", f_grande)
        linea("Números = posición en la playlist", f_chica, TEXTO_SUAVE)
        linea("Círculo: desde arriba, sentido horario", f_chica, TEXTO_SUAVE)
        y += 8
        for i in escena.orden[escena.inicio_lista:escena.inicio_lista + 7]:
            cancion = escena.canciones[i]
            color = TEXTO if i != hover else (86, 156, 255)
            linea(f"{escena.numero_dfs[i]}. {cancion.get('titulo') or '?'}", f_media, color)
            detalle = cancion.get("artista") or "Artista desconocido"
            if len(escena.grupos) > 1:
                detalle = f"Grupo {escena.grupo_dfs[i]} · {detalle}"
            linea(detalle, f_chica, TEXTO_SUAVE)
            y += 6
        y = ALTO - 152
        for texto in ("Rueda sobre el panel · desplazar lista",
                      "P · playlist / características",
                      "Arriba / abajo · cantidad de canciones",
                      "ESPACIO · repetir animación",
                      "E · mostrar / ocultar aristas",
                      "L · círculo / por pesos",
                      "Arrastra un nodo para moverlo", "ESC · salir"):
            linea(texto, f_chica, TEXTO_SUAVE, salto=17)
        return

    # leyenda de géneros
    linea("Color del nodo = género", f_chica, TEXTO_SUAVE)
    for genero, color in escena.generos.items():
        pygame.draw.circle(pantalla, color, (x + 7, y + 8), 6)
        pantalla.blit(f_chica.render(genero, True, TEXTO), (x + 22, y))
        y += f_chica.get_linesize() + 1
    y += 6
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
        linea(f"{escena.numero_dfs[hover]}. {c.get('titulo', '?')}", f_media)
        linea(c.get("artista") or "Artista desconocido", f_chica, TEXTO_SUAVE)
        linea(f"género = {c.get('genero') or 'desconocido'}", f_chica)
        for campo in ("bpm", "energia", "densidad", "brillo", "valencia"):
            v = c.get(campo)
            linea(f"{campo} = " + ("desconocido" if v is None else (f"{v:.0f}" if campo == "bpm" else f"{v:.2f}")), f_chica)
        enlaces = [(k, cn) for k, cn in enumerate(escena.elegidas) if hover in (cn.origen, cn.destino)]
        y += 4
        linea("Conectada en el árbol con:", f_chica, TEXTO_SUAVE)
        for _, cn in enlaces:
            otro = cn.destino if cn.origen == hover else cn.origen
            linea(f"  #{escena.numero_dfs[otro]}  (peso {cn.peso:.1f})", f_chica)

    # controles
    y = ALTO - 140
    pygame.draw.line(pantalla, ARISTA_TENUE, (x, y), (x + ancho, y))
    y += 8
    for t in ("P   playlist / características", "Arriba / abajo   cantidad de canciones", "ESPACIO   repetir animación",
              "E   mostrar / ocultar aristas", "L   alternar círculo / por pesos",
              "Arrastra un nodo para moverlo", "ESC   salir"):
        pantalla.blit(f_chica.render(t, True, TEXTO_SUAVE), (x, y))
        y += f_chica.get_linesize()


def cargar_fuentes():
    nombre = pygame.font.match_font("helveticaneue,helvetica,arial,segoeui,dejavusans,liberationsans")
    return (pygame.font.Font(nombre, 14), pygame.font.Font(nombre, 17), pygame.font.Font(nombre, 24))


def mostrar_grafo(pool, cantidad=None, captura=None):
    """Abre la ventana. `pool` = canciones disponibles, `cantidad` = cuántas usar."""
    pygame.init()
    pygame.display.set_caption("Grafo de la playlist · Kruskal")
    pantalla = pygame.display.set_mode((ANCHO, ALTO))
    reloj = pygame.time.Clock()
    fuentes = cargar_fuentes()
    area = pygame.Rect(0, 0, ANCHO - PANEL, ALTO)

    n = min(len(pool), max(1, cantidad if cantidad is not None else len(pool)))
    escena = Escena(pool, n, area)
    arrastrando = None
    corriendo = True

    while corriendo:
        dt = reloj.tick(60) / 1000
        escena.avanzar(dt)
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                corriendo = False
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    corriendo = False
                elif ev.key in (pygame.K_UP, pygame.K_DOWN):
                    nuevo = min(len(pool), max(1, n + (1 if ev.key == pygame.K_UP else -1)))
                    if nuevo != n:                   # <- el grafo se rehace con el nuevo tamaño
                        arrastrando = None
                        n = nuevo
                        escena = Escena(pool, n, area)
                elif ev.key == pygame.K_p:
                    escena.ver_playlist = not escena.ver_playlist
                elif ev.key == pygame.K_SPACE:
                    escena.reiniciar()
                elif ev.key == pygame.K_e:
                    escena.mostrar_tenues = not escena.mostrar_tenues
                elif ev.key == pygame.K_l:
                    escena.en_circulo = not escena.en_circulo
                    escena.circulo() if escena.en_circulo else escena.fuerzas()
            elif ev.type == pygame.MOUSEWHEEL:
                if escena.ver_playlist and pygame.mouse.get_pos()[0] >= ANCHO - PANEL:
                    escena.inicio_lista = max(0, min(max(0, escena.n - 7),
                                                    escena.inicio_lista - ev.y))
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                arrastrando = escena.nodo_en(ev.pos)
            elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
                arrastrando = None
            elif ev.type == pygame.MOUSEMOTION and arrastrando is not None:
                escena.posiciones[arrastrando] = [
                    max(area.left + 20, min(area.right - 20, ev.pos[0])),
                    max(area.top + 20, min(area.bottom - 20, ev.pos[1]))]

        hover = arrastrando if arrastrando is not None else escena.nodo_en(pygame.mouse.get_pos())
        pantalla.fill(FONDO)
        escena.dibujar(pantalla, fuentes, hover)
        dibujar_panel(pantalla, fuentes, escena, hover, len(pool))
        pygame.display.flip()

        if captura and escena.t > 6:                 # solo para pruebas sin ventana
            pygame.image.save(pantalla, captura)
            break
    pygame.quit()


# ---------------------------------------------------------------------------
# 3. Puente con la interfaz (customtkinter)
# ---------------------------------------------------------------------------
def lanzar_grafo(canciones, cantidad):
    """Abre la ventana de pygame en un proceso aparte.

    Se usa un proceso separado porque customtkinter (Tk) y pygame (SDL) quieren
    ser el "dueño" del bucle de eventos; en el mismo proceso se bloquean
    entre sí, sobre todo en macOS.
    """
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(canciones, f, ensure_ascii=False)
        ruta = f.name
    carpeta = os.path.dirname(os.path.abspath(__file__))
    return subprocess.Popen(
        [sys.executable, os.path.abspath(__file__), "--json", ruta, "--n", str(cantidad)],
        cwd=carpeta)


def principal():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    fuente = ap.add_mutually_exclusive_group()
    fuente.add_argument("--demo", type=int, metavar="N", help="usar N canciones de ejemplo")
    fuente.add_argument("--json", help="archivo JSON con canciones ya clasificadas")
    ap.add_argument("--audios", type=Path, help="carpeta de audios locales para completar características")
    ap.add_argument("--n", type=int, help="cuántas canciones dibujar")
    ap.add_argument("--captura", help="guarda una imagen y sale (pruebas)")
    args = ap.parse_args()

    if args.n is not None and args.n < 1:
        ap.error("--n debe ser mayor que cero")
    if args.demo is not None and args.demo < 1:
        ap.error("--demo debe ser mayor que cero")
    if args.audios and not args.audios.is_dir():
        ap.error("--audios debe indicar una carpeta existente")
    if args.audios and (args.demo is not None or args.json):
        ap.error("--audios se utiliza al cargar la biblioteca de Spotify")

    if args.json:
        with open(args.json, encoding="utf-8") as archivo:
            pool = json.load(archivo)
    elif args.demo is not None:
        pool = generar_demo(args.demo)
    else:
        from clasificador import biblioteca
        from spotipy.exceptions import SpotifyException, SpotifyOauthError
        from requests.exceptions import RequestException

        print("Cargando canciones de Spotify y sus características. Puede tardar varios minutos.", flush=True)
        pool = []
        try:
            for cancion in biblioteca(args.audios):
                pool.append(cancion)
                print(f"{len(pool)}. {cancion['titulo']} · {cancion['artista']}", flush=True)
        except (SpotifyException, SpotifyOauthError, RequestException, OSError) as error:
            print(f"No se pudo completar la carga ({type(error).__name__}). "
                  "Revisa la conexión y la autorización de Spotify.", file=sys.stderr)
            if not pool:
                return 1
            print(f"Se mostrarán las {len(pool)} canciones cargadas.", flush=True)

    if not pool:
        print("No hay canciones para mostrar. Agrega canciones a tu biblioteca de Spotify "
              "o utiliza un archivo JSON con canciones.")
        return 0

    mostrar_grafo(pool, args.n, args.captura)
    return 0


if __name__ == "__main__":
    sys.exit(principal())
