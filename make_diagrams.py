#!/usr/bin/env python3
"""Generate flowchart diagrams as PNG files for the HTTP-server report."""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import os

OUT_DIR = "/home/wor7hless/http_service/diagrams"
os.makedirs(OUT_DIR, exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
FONT = "DejaVu Sans"
FONT_SIZE = 9
BOX_W = 3.2      # width  of regular box
BOX_H = 0.55     # height of regular box
DIAM_W = 3.4     # width  of diamond
DIAM_H = 0.65    # height of diamond
DX = 0           # horizontal shift  (all boxes centred on x=0)

C_START  = "#2E86AB"   # blue   – start/end rounded rect
C_PROC   = "#A8DADC"   # light  – process
C_DEC    = "#F4A261"   # orange – decision
C_IO     = "#E9C46A"   # yellow – I/O
C_ERR    = "#E76F51"   # red    – error/close
TXT_DARK = "#1D3557"
TXT_WHITE= "white"

def make_fig(rows, title, figsize=(5.5, None)):
    """rows is the approximate row count; returns fig, ax"""
    h = figsize[1] or max(rows * 0.85 + 1.0, 4)
    fig, ax = plt.subplots(figsize=(figsize[0], h))
    ax.set_xlim(-3.5, 3.5)
    ax.set_ylim(-rows * 0.85 - 0.5, 0.8)
    ax.axis('off')
    ax.set_title(title, fontsize=11, fontweight='bold', color=TXT_DARK,
                 fontfamily=FONT, pad=6)
    return fig, ax

def rounded_box(ax, cx, cy, w, h, text, color=C_PROC, text_color=TXT_DARK,
                fontsize=FONT_SIZE, rounded=True):
    style = "round,pad=0.08" if rounded else "square,pad=0.08"
    box = FancyBboxPatch((cx - w/2, cy - h/2), w, h,
                         boxstyle=style, linewidth=0.8,
                         edgecolor="#444", facecolor=color, zorder=3)
    ax.add_patch(box)
    ax.text(cx, cy, text, ha='center', va='center', fontsize=fontsize,
            color=text_color, fontfamily=FONT, zorder=4,
            wrap=True, multialignment='center')

def diamond(ax, cx, cy, w, h, text, color=C_DEC, text_color=TXT_DARK,
            fontsize=FONT_SIZE):
    xs = [cx, cx + w/2, cx, cx - w/2, cx]
    ys = [cy + h/2, cy, cy - h/2, cy, cy + h/2]
    ax.fill(xs, ys, color=color, zorder=3, edgecolor="#444", linewidth=0.8)
    ax.text(cx, cy, text, ha='center', va='center', fontsize=fontsize,
            color=text_color, fontfamily=FONT, zorder=4, multialignment='center')

def arrow(ax, x1, y1, x2, y2, label='', label_side='right'):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='->', color='#333', lw=1.0),
                zorder=2)
    if label:
        mx = (x1+x2)/2 + (0.18 if label_side=='right' else -0.18)
        my = (y1+y2)/2
        ax.text(mx, my, label, fontsize=7.5, color='#333',
                ha='left' if label_side=='right' else 'right',
                va='center', fontfamily=FONT)

def harrow(ax, x1, y, x2, label='', label_side='above'):
    """Horizontal arrow from (x1,y) to (x2,y)."""
    ax.annotate('', xy=(x2, y), xytext=(x1, y),
                arrowprops=dict(arrowstyle='->', color='#333', lw=1.0), zorder=2)
    if label:
        mx = (x1+x2)/2
        my = y + (0.12 if label_side=='above' else -0.15)
        ax.text(mx, my, label, fontsize=7.5, color='#333',
                ha='center', va='bottom' if label_side=='above' else 'top',
                fontfamily=FONT)

# ═════════════════════════════════════════════════════════════════════════════
# 1. Main server loop  (start_server)
# ═════════════════════════════════════════════════════════════════════════════
def diagram_server_loop():
    rows = 14
    fig, ax = make_fig(rows, "Рисунок 1 — Главный цикл сервера (start_server)", figsize=(5.5, 6.5))
    Y  = [i * -0.85 for i in range(rows+2)]

    cx = 0
    # 0 – Start
    rounded_box(ax, cx, Y[0], BOX_W, BOX_H, "НАЧАЛО", C_START, TXT_WHITE)
    arrow(ax, cx, Y[0]-BOX_H/2, cx, Y[1]+BOX_H/2)

    # 1 – socket()
    rounded_box(ax, cx, Y[1], BOX_W, BOX_H, "socket(AF_INET, SOCK_STREAM)")
    arrow(ax, cx, Y[1]-BOX_H/2, cx, Y[2]+DIAM_H/2)

    # 2 – socket ok?
    diamond(ax, cx, Y[2], DIAM_W, DIAM_H, "Ошибка?")
    arrow(ax, cx, Y[2]-DIAM_H/2, cx, Y[3]+BOX_H/2, "Нет")
    # error branch right
    ax.annotate('', xy=(2.8, Y[2]), xytext=(cx+DIAM_W/2, Y[2]),
                arrowprops=dict(arrowstyle='->', color='#333', lw=1.0))
    ax.text(cx+DIAM_W/2+0.08, Y[2]+0.1, "Да", fontsize=7.5, color='#333', fontfamily=FONT)
    rounded_box(ax, 3.0, Y[2], 0.8, BOX_H, "return -1", C_ERR, TXT_WHITE, fontsize=8)

    # 3 – setsockopt + bind + listen
    rounded_box(ax, cx, Y[3], BOX_W, BOX_H, "setsockopt / bind / listen")
    arrow(ax, cx, Y[3]-BOX_H/2, cx, Y[4]+BOX_H/2)

    # 4 – mkdir upload_dir
    rounded_box(ax, cx, Y[4], BOX_W, BOX_H, "mkdir(upload_dir) если не существует", fontsize=8)
    arrow(ax, cx, Y[4]-BOX_H/2, cx, Y[5]+BOX_H/2)

    # 5 – signal(SIGPIPE, SIG_IGN)
    rounded_box(ax, cx, Y[5], BOX_W, BOX_H, "signal(SIGPIPE, SIG_IGN)")
    arrow(ax, cx, Y[5]-BOX_H/2, cx, Y[6]+BOX_H/2)

    # 6 – ∞ loop label
    ax.text(cx - BOX_W/2 - 0.15, Y[6]+BOX_H/2+0.1, "∞",
            fontsize=13, color="#2E86AB", ha='right', va='bottom', fontfamily=FONT)
    # 6 – accept()
    rounded_box(ax, cx, Y[6], BOX_W, BOX_H, "accept() — ожидание соединения")
    arrow(ax, cx, Y[6]-BOX_H/2, cx, Y[7]+DIAM_H/2)

    # 7 – accept ok?
    diamond(ax, cx, Y[7], DIAM_W, DIAM_H, "cl < 0?")
    arrow(ax, cx, Y[7]-DIAM_H/2, cx, Y[8]+BOX_H/2, "Нет")
    ax.annotate('', xy=(-2.8, Y[7]), xytext=(cx-DIAM_W/2, Y[7]),
                arrowprops=dict(arrowstyle='->', color='#333', lw=1.0))
    ax.text(cx-DIAM_W/2-0.08, Y[7]+0.1, "Да", fontsize=7.5, color='#333',
            ha='right', fontfamily=FONT)
    rounded_box(ax, -3.0, Y[7], 0.8, BOX_H, "continue", C_ERR, TXT_WHITE, fontsize=8)

    # 8 – setтаймаут + getpeername
    rounded_box(ax, cx, Y[8], BOX_W, BOX_H, "SO_RCVTIMEO / SO_SNDTIMEO\ngetpeername → peer_ip", fontsize=8)
    arrow(ax, cx, Y[8]-BOX_H/2, cx, Y[9]+BOX_H/2)

    # 9 – recv headers
    rounded_box(ax, cx, Y[9], BOX_W, BOX_H, "recv() — чтение заголовков", C_IO)
    arrow(ax, cx, Y[9]-BOX_H/2, cx, Y[10]+BOX_H/2)

    # 10 – parse_http_headers
    rounded_box(ax, cx, Y[10], BOX_W, BOX_H, "parse_http_headers()")
    arrow(ax, cx, Y[10]-BOX_H/2, cx, Y[11]+BOX_H/2)

    # 11 – handle_request (sub-diagram reference)
    rounded_box(ax, cx, Y[11], BOX_W, BOX_H,
                "handle_request()\n(см. рис. 2)", C_PROC, TXT_DARK, fontsize=8)
    arrow(ax, cx, Y[11]-BOX_H/2, cx, Y[12]+BOX_H/2)

    # 12 – close(cl)
    rounded_box(ax, cx, Y[12], BOX_W, BOX_H, "close(cl)")
    # loop back arrow
    lx = cx - BOX_W/2 - 0.4
    ax.annotate('', xy=(lx, Y[6]+BOX_H/2),
                xytext=(lx, Y[12]-BOX_H/2),
                arrowprops=dict(arrowstyle='->', color='#2E86AB', lw=1.2,
                                connectionstyle="arc3,rad=0.0"))
    ax.plot([cx-BOX_W/2, lx], [Y[12]-BOX_H/2, Y[12]-BOX_H/2], color='#2E86AB', lw=1.2)
    ax.plot([lx, cx-BOX_W/2], [Y[6]+BOX_H/2, Y[6]+BOX_H/2], color='#2E86AB', lw=1.2)

    plt.tight_layout(pad=0.5)
    path = os.path.join(OUT_DIR, "diagram1_server_loop.png")
    fig.savefig(path, dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved: {path}")

# ═════════════════════════════════════════════════════════════════════════════
# 2. Request routing (handle_request)
# ═════════════════════════════════════════════════════════════════════════════
def diagram_request_routing():
    rows = 16
    fig, ax = make_fig(rows, "Рисунок 2 — Маршрутизация и обработка запроса", figsize=(5.5, 7.0))
    Y = [i * -0.82 for i in range(rows+2)]
    cx = 0

    rounded_box(ax, cx, Y[0], BOX_W, BOX_H, "НАЧАЛО: получен запрос", C_START, TXT_WHITE)
    arrow(ax, cx, Y[0]-BOX_H/2, cx, Y[1]+DIAM_H/2)

    diamond(ax, cx, Y[1], DIAM_W, DIAM_H, "method == GET?")
    # Yes branch left
    ax.annotate('', xy=(-2.5, Y[2]), xytext=(cx-DIAM_W/2, Y[1]),
                arrowprops=dict(arrowstyle='->', color='#333', lw=1.0))
    ax.text(cx-DIAM_W/2-0.08, Y[1]+0.08, "Да", fontsize=7.5, color='#333',
            ha='right', fontfamily=FONT)
    # No branch down
    arrow(ax, cx, Y[1]-DIAM_H/2, cx, Y[3]+DIAM_H/2, "Нет")

    # GET branch
    rounded_box(ax, -2.5, Y[2], 1.6, BOX_H, "path == / ?", C_DEC, TXT_DARK, fontsize=8.5)
    # send form
    rounded_box(ax, -2.5, Y[2]-0.85, 1.6, BOX_H, "200 + HTML-форма", C_IO, TXT_DARK, fontsize=8)
    ax.annotate('', xy=(-2.5, Y[2]-0.85+BOX_H/2), xytext=(-2.5, Y[2]-BOX_H/2),
                arrowprops=dict(arrowstyle='->', color='#333', lw=1.0))
    ax.text(-2.5-0.1, Y[2]-0.85/2-0.1, "Да", fontsize=7, color='#333', ha='right', fontfamily=FONT)
    rounded_box(ax, -2.5, Y[2]-0.85*2, 1.6, BOX_H, "404 Not Found", C_ERR, TXT_WHITE, fontsize=8)
    ax.annotate('', xy=(-2.5, Y[2]-0.85*2+BOX_H/2), xytext=(-2.5, Y[2]-BOX_H/2),
                arrowprops=dict(arrowstyle='->', color='#333', lw=1.0,
                                connectionstyle="arc3,rad=0.4"))
    ax.text(-2.5+0.35, Y[2]-0.85*1.3, "Нет", fontsize=7, color='#333', fontfamily=FONT)

    # POST chain
    diamond(ax, cx, Y[3], DIAM_W, DIAM_H, "method == POST\n& path == /upload?", fontsize=8.5)
    arrow(ax, cx, Y[3]-DIAM_H/2, cx, Y[4]+DIAM_H/2, "Да")
    ax.annotate('', xy=(2.8, Y[3]), xytext=(cx+DIAM_W/2, Y[3]),
                arrowprops=dict(arrowstyle='->', color='#333', lw=1.0))
    ax.text(cx+DIAM_W/2+0.08, Y[3]+0.1, "Нет", fontsize=7.5, color='#333', fontfamily=FONT)
    rounded_box(ax, 3.0, Y[3], 0.8, BOX_H, "404", C_ERR, TXT_WHITE, fontsize=8)

    # auth check
    diamond(ax, cx, Y[4], DIAM_W, DIAM_H, "auth_enabled\n& !check_auth()?", fontsize=8.5)
    arrow(ax, cx, Y[4]-DIAM_H/2, cx, Y[5]+BOX_H/2, "Нет")
    ax.annotate('', xy=(-2.8, Y[4]), xytext=(cx-DIAM_W/2, Y[4]),
                arrowprops=dict(arrowstyle='->', color='#333', lw=1.0))
    ax.text(cx-DIAM_W/2-0.08, Y[4]+0.1, "Да", fontsize=7.5, color='#333',
            ha='right', fontfamily=FONT)
    rounded_box(ax, -3.0, Y[4], 0.8, BOX_H, "401", C_ERR, TXT_WHITE, fontsize=8)

    # headers complete?
    rounded_box(ax, cx, Y[5], BOX_W, BOX_H, "Найти \\r\\n\\r\\n в буфере")
    arrow(ax, cx, Y[5]-BOX_H/2, cx, Y[6]+DIAM_H/2)

    diamond(ax, cx, Y[6], DIAM_W, DIAM_H, "Заголовки\nнеполные?", fontsize=8.5)
    arrow(ax, cx, Y[6]-DIAM_H/2, cx, Y[7]+BOX_H/2, "Нет")
    ax.annotate('', xy=(2.8, Y[6]), xytext=(cx+DIAM_W/2, Y[6]),
                arrowprops=dict(arrowstyle='->', color='#333', lw=1.0))
    ax.text(cx+DIAM_W/2+0.08, Y[6]+0.1, "Да", fontsize=7.5, color='#333', fontfamily=FONT)
    rounded_box(ax, 3.0, Y[6], 0.8, BOX_H, "400", C_ERR, TXT_WHITE, fontsize=8)

    # extract boundary
    rounded_box(ax, cx, Y[7], BOX_W, BOX_H, "extract_boundary(content_type)")
    arrow(ax, cx, Y[7]-BOX_H/2, cx, Y[8]+DIAM_H/2)

    diamond(ax, cx, Y[8], DIAM_W, DIAM_H, "boundary\nнайден?", fontsize=8.5)
    arrow(ax, cx, Y[8]-DIAM_H/2, cx, Y[9]+BOX_H/2, "Да")
    ax.annotate('', xy=(-2.8, Y[8]), xytext=(cx-DIAM_W/2, Y[8]),
                arrowprops=dict(arrowstyle='->', color='#333', lw=1.0))
    ax.text(cx-DIAM_W/2-0.08, Y[8]+0.1, "Нет", fontsize=7.5, color='#333',
            ha='right', fontfamily=FONT)
    rounded_box(ax, -3.0, Y[8], 0.8, BOX_H, "400", C_ERR, TXT_WHITE, fontsize=8)

    # fopen
    rounded_box(ax, cx, Y[9], BOX_W, BOX_H, "fopen(upload_dir/upload.bin, \"wb\")", fontsize=8)
    arrow(ax, cx, Y[9]-BOX_H/2, cx, Y[10]+BOX_H/2)

    # parse_multipart call
    rounded_box(ax, cx, Y[10], BOX_W, BOX_H, "parse_multipart()\n(см. рис. 3)", fontsize=8.5)
    arrow(ax, cx, Y[10]-BOX_H/2, cx, Y[11]+DIAM_H/2)

    diamond(ax, cx, Y[11], DIAM_W, DIAM_H, "Ошибка\nпарсинга?", fontsize=8.5)
    arrow(ax, cx, Y[11]-DIAM_H/2, cx, Y[12]+BOX_H/2, "Нет")
    ax.annotate('', xy=(2.8, Y[11]), xytext=(cx+DIAM_W/2, Y[11]),
                arrowprops=dict(arrowstyle='->', color='#333', lw=1.0))
    ax.text(cx+DIAM_W/2+0.08, Y[11]+0.1, "Да", fontsize=7.5, color='#333', fontfamily=FONT)
    rounded_box(ax, 3.0, Y[11], 0.8, BOX_H, "400\nunlink", C_ERR, TXT_WHITE, fontsize=7.5)

    # rename
    rounded_box(ax, cx, Y[12], BOX_W, BOX_H, "rename(upload.bin → filename)")
    arrow(ax, cx, Y[12]-BOX_H/2, cx, Y[13]+BOX_H/2)

    # 200 OK
    rounded_box(ax, cx, Y[13], BOX_W, BOX_H, "200 OK: «File uploaded: <name>»", C_IO)
    arrow(ax, cx, Y[13]-BOX_H/2, cx, Y[14]+BOX_H/2)

    rounded_box(ax, cx, Y[14], BOX_W, BOX_H, "КОНЕЦ", C_START, TXT_WHITE)

    plt.tight_layout(pad=0.5)
    path = os.path.join(OUT_DIR, "diagram2_request_routing.png")
    fig.savefig(path, dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved: {path}")

# ═════════════════════════════════════════════════════════════════════════════
# 3. parse_multipart
# ═════════════════════════════════════════════════════════════════════════════
def diagram_multipart():
    rows = 16
    fig, ax = make_fig(rows, "Рисунок 3 — Алгоритм parse_multipart()", figsize=(5.5, 6.8))
    Y = [i * -0.82 for i in range(rows+2)]
    cx = 0

    rounded_box(ax, cx, Y[0], BOX_W, BOX_H, "НАЧАЛО", C_START, TXT_WHITE)
    arrow(ax, cx, Y[0]-BOX_H/2, cx, Y[1]+DIAM_H/2)

    diamond(ax, cx, Y[1], DIAM_W, DIAM_H, "total == 0\nили > MAX_BODY_SIZE?", fontsize=8.5)
    arrow(ax, cx, Y[1]-DIAM_H/2, cx, Y[2]+BOX_H/2, "Нет")
    ax.annotate('', xy=(2.8, Y[1]), xytext=(cx+DIAM_W/2, Y[1]),
                arrowprops=dict(arrowstyle='->', color='#333', lw=1.0))
    ax.text(cx+DIAM_W/2+0.08, Y[1]+0.1, "Да", fontsize=7.5, color='#333', fontfamily=FONT)
    rounded_box(ax, 3.0, Y[1], 0.8, BOX_H, "return -1", C_ERR, TXT_WHITE, fontsize=7.5)

    rounded_box(ax, cx, Y[2], BOX_W, BOX_H, "malloc(total + 1)")
    arrow(ax, cx, Y[2]-BOX_H/2, cx, Y[3]+BOX_H/2)

    rounded_box(ax, cx, Y[3], BOX_W, BOX_H, "memcpy начальных байт из буфера\n(initial_data)", fontsize=8)
    arrow(ax, cx, Y[3]-BOX_H/2, cx, Y[4]+DIAM_H/2)

    # recv loop
    diamond(ax, cx, Y[4], DIAM_W, DIAM_H, "received < total?")
    arrow(ax, cx, Y[4]-DIAM_H/2, cx, Y[5]+BOX_H/2, "Нет")
    ax.annotate('', xy=(cx+DIAM_W/2+0.5, Y[4]), xytext=(cx+DIAM_W/2, Y[4]),
                arrowprops=dict(arrowstyle='->', color='#333', lw=1.0))
    ax.text(cx+DIAM_W/2+0.08, Y[4]+0.1, "Да", fontsize=7.5, color='#333', fontfamily=FONT)
    rounded_box(ax, cx+DIAM_W/2+1.1, Y[4], 0.9, BOX_H, "recv(fd)\nreceived += r", C_IO, fontsize=7.5)
    # loop arrow back
    lx2 = cx + DIAM_W/2 + 1.55
    ax.plot([lx2, lx2], [Y[4]-BOX_H/2, Y[4]-BOX_H/2-0.2], color='#333', lw=1.0)
    ax.plot([lx2, cx+DIAM_W/2], [Y[4]-BOX_H/2-0.2, Y[4]-BOX_H/2-0.2], color='#333', lw=1.0)
    ax.annotate('', xy=(cx+DIAM_W/2, Y[4]),
                xytext=(cx+DIAM_W/2, Y[4]-BOX_H/2-0.2),
                arrowprops=dict(arrowstyle='->', color='#333', lw=1.0))

    rounded_box(ax, cx, Y[5], BOX_W, BOX_H, "strstr(buf, \"--\" + boundary)")
    arrow(ax, cx, Y[5]-BOX_H/2, cx, Y[6]+DIAM_H/2)

    diamond(ax, cx, Y[6], DIAM_W, DIAM_H, "boundary\nнайден?", fontsize=8.5)
    arrow(ax, cx, Y[6]-DIAM_H/2, cx, Y[7]+BOX_H/2, "Да")
    ax.annotate('', xy=(-2.8, Y[6]), xytext=(cx-DIAM_W/2, Y[6]),
                arrowprops=dict(arrowstyle='->', color='#333', lw=1.0))
    ax.text(cx-DIAM_W/2-0.08, Y[6]+0.1, "Нет", fontsize=7.5, color='#333',
            ha='right', fontfamily=FONT)
    rounded_box(ax, -3.0, Y[6], 0.8, BOX_H, "free; -1", C_ERR, TXT_WHITE, fontsize=7.5)

    rounded_box(ax, cx, Y[7], BOX_W, BOX_H, "strstr(start, \"\\r\\n\\r\\n\") → header_end")
    arrow(ax, cx, Y[7]-BOX_H/2, cx, Y[8]+BOX_H/2)

    rounded_box(ax, cx, Y[8], BOX_W, BOX_H, "strstr(header, 'filename=\"') → извлечь имя", fontsize=8)
    arrow(ax, cx, Y[8]-BOX_H/2, cx, Y[9]+BOX_H/2)

    rounded_box(ax, cx, Y[9], BOX_W, BOX_H, "data_start = header_end + 4")
    arrow(ax, cx, Y[9]-BOX_H/2, cx, Y[10]+BOX_H/2)

    rounded_box(ax, cx, Y[10], BOX_W, BOX_H, "strstr(data_start, \"--\" + boundary)\n→ конец данных файла", fontsize=8)
    arrow(ax, cx, Y[10]-BOX_H/2, cx, Y[11]+BOX_H/2)

    rounded_box(ax, cx, Y[11], BOX_W, BOX_H, "Обрезать '\\r\\n' перед boundary")
    arrow(ax, cx, Y[11]-BOX_H/2, cx, Y[12]+BOX_H/2)

    rounded_box(ax, cx, Y[12], BOX_W, BOX_H, "fwrite(data_start, data_len, out)", C_IO)
    arrow(ax, cx, Y[12]-BOX_H/2, cx, Y[13]+BOX_H/2)

    rounded_box(ax, cx, Y[13], BOX_W, BOX_H, "free(buf)")
    arrow(ax, cx, Y[13]-BOX_H/2, cx, Y[14]+BOX_H/2)

    rounded_box(ax, cx, Y[14], BOX_W, BOX_H, "return 0  (успех)", C_START, TXT_WHITE)

    plt.tight_layout(pad=0.5)
    path = os.path.join(OUT_DIR, "diagram3_multipart.png")
    fig.savefig(path, dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved: {path}")

# ═════════════════════════════════════════════════════════════════════════════
# 4. check_auth / Base64 decode
# ═════════════════════════════════════════════════════════════════════════════
def diagram_auth():
    rows = 12
    fig, ax = make_fig(rows, "Рисунок 4 — Алгоритм check_auth() / декодирование Base64", figsize=(5.5, 5.5))
    Y = [i * -0.82 for i in range(rows+2)]
    cx = 0

    rounded_box(ax, cx, Y[0], BOX_W, BOX_H, "НАЧАЛО: получен заголовок Authorization", C_START, TXT_WHITE, fontsize=8)
    arrow(ax, cx, Y[0]-BOX_H/2, cx, Y[1]+DIAM_H/2)

    diamond(ax, cx, Y[1], DIAM_W, DIAM_H, "Начинается\nс \"Basic \"?", fontsize=8.5)
    arrow(ax, cx, Y[1]-DIAM_H/2, cx, Y[2]+BOX_H/2, "Да")
    ax.annotate('', xy=(2.8, Y[1]), xytext=(cx+DIAM_W/2, Y[1]),
                arrowprops=dict(arrowstyle='->', color='#333', lw=1.0))
    ax.text(cx+DIAM_W/2+0.08, Y[1]+0.1, "Нет", fontsize=7.5, color='#333', fontfamily=FONT)
    rounded_box(ax, 3.0, Y[1], 0.8, BOX_H, "return 0", C_ERR, TXT_WHITE, fontsize=7.5)

    rounded_box(ax, cx, Y[2], BOX_W, BOX_H, "Взять строку после \"Basic \"")
    arrow(ax, cx, Y[2]-BOX_H/2, cx, Y[3]+BOX_H/2)

    # b64 loop
    rounded_box(ax, cx, Y[3], BOX_W, BOX_H, "Base64-декодирование (b64()):", fontsize=8.5)
    arrow(ax, cx, Y[3]-BOX_H/2, cx, Y[4]+DIAM_H/2)

    diamond(ax, cx, Y[4], DIAM_W+0.2, DIAM_H, "Ещё символы\nв строке?", fontsize=8.5)
    ax.annotate('', xy=(cx+DIAM_W/2+0.6, Y[4]), xytext=(cx+DIAM_W/2+0.1, Y[4]),
                arrowprops=dict(arrowstyle='->', color='#333', lw=1.0))
    ax.text(cx+DIAM_W/2+0.12, Y[4]+0.1, "Да", fontsize=7.5, color='#333', fontfamily=FONT)
    rounded_box(ax, cx+DIAM_W/2+1.15, Y[4], 1.0, BOX_H,
                "idx(c)→6 бит\nakkum → байт", C_PROC, fontsize=7.5)
    lx3 = cx+DIAM_W/2+1.65
    ax.plot([lx3, lx3], [Y[4]-BOX_H/2, Y[4]-BOX_H/2-0.18], color='#333', lw=1.0)
    ax.plot([lx3, cx+DIAM_W/2+0.1], [Y[4]-BOX_H/2-0.18, Y[4]-BOX_H/2-0.18], color='#333', lw=1.0)
    ax.annotate('', xy=(cx+DIAM_W/2+0.1, Y[4]),
                xytext=(cx+DIAM_W/2+0.1, Y[4]-BOX_H/2-0.18),
                arrowprops=dict(arrowstyle='->', color='#333', lw=1.0))

    arrow(ax, cx, Y[4]-DIAM_H/2, cx, Y[5]+BOX_H/2, "Нет")

    rounded_box(ax, cx, Y[5], BOX_W, BOX_H, "Декодировано: \"username:password\"")
    arrow(ax, cx, Y[5]-BOX_H/2, cx, Y[6]+BOX_H/2)

    rounded_box(ax, cx, Y[6], BOX_W, BOX_H, "Собрать expected =\nconfig.username + \":\" + config.password", fontsize=8)
    arrow(ax, cx, Y[6]-BOX_H/2, cx, Y[7]+DIAM_H/2)

    diamond(ax, cx, Y[7], DIAM_W, DIAM_H, "strcmp\n(decoded, expected) == 0?", fontsize=8.5)
    arrow(ax, cx, Y[7]-DIAM_H/2, cx, Y[8]+BOX_H/2, "Да")
    ax.annotate('', xy=(2.8, Y[7]), xytext=(cx+DIAM_W/2, Y[7]),
                arrowprops=dict(arrowstyle='->', color='#333', lw=1.0))
    ax.text(cx+DIAM_W/2+0.08, Y[7]+0.1, "Нет", fontsize=7.5, color='#333', fontfamily=FONT)
    rounded_box(ax, 3.0, Y[7], 0.8, BOX_H, "return 0\n(отказ)", C_ERR, TXT_WHITE, fontsize=7.5)

    rounded_box(ax, cx, Y[8], BOX_W, BOX_H, "return 1  (аутентификация успешна)", C_START, TXT_WHITE, fontsize=8)

    plt.tight_layout(pad=0.5)
    path = os.path.join(OUT_DIR, "diagram4_auth.png")
    fig.savefig(path, dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved: {path}")

# ═════════════════════════════════════════════════════════════════════════════
# 5. load_config
# ═════════════════════════════════════════════════════════════════════════════
def diagram_config():
    rows = 12
    fig, ax = make_fig(rows, "Рисунок 5 — Алгоритм загрузки конфигурации (load_config)", figsize=(5.5, 5.5))
    Y = [i * -0.82 for i in range(rows+2)]
    cx = 0

    rounded_box(ax, cx, Y[0], BOX_W, BOX_H, "НАЧАЛО: load_config(path, cfg)", C_START, TXT_WHITE, fontsize=8)
    arrow(ax, cx, Y[0]-BOX_H/2, cx, Y[1]+BOX_H/2)

    rounded_box(ax, cx, Y[1], BOX_W, BOX_H, "default_config(cfg) — значения по умолчанию", fontsize=8)
    arrow(ax, cx, Y[1]-BOX_H/2, cx, Y[2]+DIAM_H/2)

    diamond(ax, cx, Y[2], DIAM_W, DIAM_H, "fopen(path) == NULL?")
    arrow(ax, cx, Y[2]-DIAM_H/2, cx, Y[3]+BOX_H/2, "Нет")
    ax.annotate('', xy=(2.8, Y[2]), xytext=(cx+DIAM_W/2, Y[2]),
                arrowprops=dict(arrowstyle='->', color='#333', lw=1.0))
    ax.text(cx+DIAM_W/2+0.08, Y[2]+0.1, "Да", fontsize=7.5, color='#333', fontfamily=FONT)
    rounded_box(ax, 3.0, Y[2], 0.9, BOX_H, "return -1\n(defaults)", C_ERR, TXT_WHITE, fontsize=7.5)

    diamond(ax, cx, Y[3], DIAM_W, DIAM_H, "fgets() → ещё\nстроки в файле?")
    arrow(ax, cx, Y[3]-DIAM_H/2, cx, Y[4]+BOX_H/2, "Да")
    # loop out
    ax.annotate('', xy=(-2.8, Y[3]), xytext=(cx-DIAM_W/2, Y[3]),
                arrowprops=dict(arrowstyle='->', color='#333', lw=1.0))
    ax.text(cx-DIAM_W/2-0.08, Y[3]+0.1, "Нет", fontsize=7.5, color='#333',
            ha='right', fontfamily=FONT)
    rounded_box(ax, -3.0, Y[3], 0.8, BOX_H, "→ конец\nцикла", C_PROC, fontsize=7.5)

    rounded_box(ax, cx, Y[4], BOX_W, BOX_H, "sscanf(line, \"%63[^=]=%255s\", key, val)", fontsize=8)
    arrow(ax, cx, Y[4]-BOX_H/2, cx, Y[5]+DIAM_H/2)

    diamond(ax, cx, Y[5], DIAM_W, DIAM_H, "Разобрано\nkey + value?", fontsize=8.5)
    # yes
    arrow(ax, cx, Y[5]-DIAM_H/2, cx, Y[6]+BOX_H/2, "Да")
    # no → back to fgets
    ax.annotate('', xy=(2.8, Y[5]), xytext=(cx+DIAM_W/2, Y[5]),
                arrowprops=dict(arrowstyle='->', color='#333', lw=1.0))
    ax.text(cx+DIAM_W/2+0.08, Y[5]+0.1, "Нет", fontsize=7.5, color='#333', fontfamily=FONT)
    ax.annotate('', xy=(cx+DIAM_W/2+0.5, Y[3]), xytext=(cx+DIAM_W/2+0.5, Y[5]),
                arrowprops=dict(arrowstyle='->', color='#333', lw=1.0))
    ax.plot([cx+DIAM_W/2, cx+DIAM_W/2+0.5], [Y[5], Y[5]], color='#333', lw=1.0)
    ax.plot([cx+DIAM_W/2, cx+DIAM_W/2+0.5], [Y[3], Y[3]], color='#333', lw=1.0)

    rounded_box(ax, cx, Y[6], BOX_W, BOX_H, "Присвоить cfg.<key> = value\n(address / port / upload_dir /\nusername / password / auth)", fontsize=7.5)
    # loop back arrow
    lx4 = cx - BOX_W/2 - 0.4
    ax.plot([cx-BOX_W/2, lx4], [Y[6]-BOX_H/2, Y[6]-BOX_H/2], color='#2E86AB', lw=1.2)
    ax.plot([lx4, lx4], [Y[6]-BOX_H/2, Y[3]+DIAM_H/2], color='#2E86AB', lw=1.2)
    ax.annotate('', xy=(cx-DIAM_W/2, Y[3]),
                xytext=(lx4, Y[3]),
                arrowprops=dict(arrowstyle='->', color='#2E86AB', lw=1.2))

    rounded_box(ax, cx, Y[8], BOX_W, BOX_H, "fclose(f)")
    arrow(ax, cx, Y[8]-BOX_H/2, cx, Y[9]+BOX_H/2)
    rounded_box(ax, cx, Y[9], BOX_W, BOX_H, "return 0  (успех)", C_START, TXT_WHITE)

    # connect "no more lines" → fclose
    ax.plot([-3.0, -3.0], [Y[3]-BOX_H/2, Y[8]], color='#333', lw=1.0, linestyle='--')
    ax.annotate('', xy=(cx-BOX_W/2, Y[8]),
                xytext=(-3.0, Y[8]),
                arrowprops=dict(arrowstyle='->', color='#333', lw=1.0))

    plt.tight_layout(pad=0.5)
    path = os.path.join(OUT_DIR, "diagram5_config.png")
    fig.savefig(path, dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved: {path}")

# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    diagram_server_loop()
    diagram_request_routing()
    diagram_multipart()
    diagram_auth()
    diagram_config()
    print("All diagrams generated.")
