"""Generator Lottie JSON (burst, rings, confetti, twinkle, scribble) dua palet. Output ke public/lottie."""
import json, math, os, random, sys

OUT = sys.argv[1]
FR = 30
PALETTES = {
    "a": {"main": "#FFC53D", "alt": "#F28C28", "light": "#FFF1C9"},   # sejarah: emas/oranye/krem
    "b": {"main": "#6FE7FF", "alt": "#8A5CFF", "light": "#FFFFFF"},   # antariksa: cyan/ungu/putih
}


def rgb(h):
    h = h.lstrip("#")
    return [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)] + [1]


def S(v):
    return {"a": 0, "k": v}


def ease(n):
    return {"i": {"x": [0.2] * n, "y": [1] * n}, "o": {"x": [0.3] * n, "y": [0] * n}}


def A(keys):
    """keys = [(frame, value), ...]; value skalar atau list."""
    out = []
    for idx, (t, v) in enumerate(keys):
        v = v if isinstance(v, list) else [v]
        kf = {"t": t, "s": v}
        if idx < len(keys) - 1:
            kf.update(ease(len(v)))
        out.append(kf)
    return {"a": 1, "k": out}


def tr(p=(0, 0), s=(100, 100), r=0, o=100):
    f = lambda x: x if isinstance(x, dict) else S(list(x) if isinstance(x, (tuple, list)) else x)
    return {"ty": "tr", "p": f(p), "a": S([0, 0]), "s": f(s), "r": f(r), "o": f(o), "sk": S(0), "sa": S(0)}


def fill(c):
    return {"ty": "fl", "c": S(rgb(c)), "o": S(100), "r": 1}


def stroke(c, w):
    return {"ty": "st", "c": S(rgb(c)), "o": S(100), "w": w if isinstance(w, dict) else S(w), "lc": 2, "lj": 2}


def ellipse(d):
    return {"ty": "el", "p": S([0, 0]), "s": S([d, d])}


def rect(w, h, r=0):
    return {"ty": "rc", "d": 1, "s": S([w, h]), "p": S([0, 0]), "r": S(r)}


def star(pts, outer, inner):
    return {"ty": "sr", "sy": 1, "d": 1, "pt": S(pts), "p": S([0, 0]), "r": S(0), "ir": S(inner), "is": S(0),
            "or": S(outer), "os": S(0)}


def group(items, transform):
    return {"ty": "gr", "it": items + [transform], "nm": "g"}


def layer(shapes, n, ind=1, w=1080, h=1080):
    return {"ddd": 0, "ind": ind, "ty": 4, "nm": f"l{ind}", "sr": 1,
            "ks": {"o": S(100), "r": S(0), "p": S([w / 2, h / 2, 0]), "a": S([0, 0, 0]), "s": S([100, 100, 100])},
            "ao": 0, "shapes": shapes, "ip": 0, "op": n, "st": 0, "bm": 0}


def comp(name, n, layers, w=1080, h=1080):
    return {"v": "5.7.0", "fr": FR, "ip": 0, "op": n, "w": w, "h": h, "nm": name, "ddd": 0, "assets": [], "layers": layers}


# ----------------------------------------------------------------------------
def burst(c):
    n, shapes = 30, []
    for i in range(16):
        ang = i * 360 / 16
        col = c["main"] if i % 2 == 0 else c["alt"]
        length = 130 if i % 2 == 0 else 80
        d = 2 + (i % 3)
        inner = group([rect(14, length, 7), fill(col)],
                      tr(p=A([(d, [0, -120]), (n - 4, [0, -430 - (i % 2) * 40])]), o=A([(d, 100), (n - 6, 100), (n - 1, 0)]),
                         s=A([(d, [100, 100]), (n - 2, [100, 40])])))
        shapes.append(group([inner], tr(r=ang)))
    core = group([star(8, 150, 60), fill(c["light"])],
                 tr(s=A([(0, [0, 0]), (5, [130, 130]), (16, [60, 60])]), o=A([(0, 100), (10, 100), (18, 0)]),
                    r=A([(0, 0), (18, 45)])))
    return comp("burst", n, [layer([core] + shapes, n)])


def rings(c):
    n, shapes = 36, []
    cols = [c["main"], c["alt"], c["light"]]
    for i in range(3):
        st = i * 5
        shapes.append(group([ellipse(700), stroke(cols[i], A([(st, 26), (n - 2, 3)]))],
                            tr(s=A([(st, [8, 8]), (n - 2, [100, 100])]), o=A([(st, 100), (st + 14, 90), (n - 1, 0)]))))
    return comp("rings", n, [layer(shapes, n)])


def confetti(c):
    n, shapes = 60, []
    rnd = random.Random(7)
    cols = [c["main"], c["alt"], c["light"]]
    for i in range(34):
        a = rnd.uniform(0, math.tau)
        sp = rnd.uniform(150, 470)
        x1, y1 = math.cos(a) * sp, math.sin(a) * sp * 0.8 - 40
        y2 = y1 + rnd.uniform(230, 400)
        x2 = x1 * 1.15
        kind = i % 3
        body = [rect(rnd.randint(14, 26), rnd.randint(8, 14), 2)] if kind == 0 else (
            [ellipse(rnd.randint(12, 20))] if kind == 1 else [star(4, rnd.randint(14, 22), 5)])
        t0 = rnd.randint(0, 4)
        g = group(body + [fill(cols[i % 3])],
                  tr(p=A([(t0, [0, 0]), (t0 + 14, [x1, y1]), (n - 1, [x2, y2])]),
                     r=A([(t0, 0), (n - 1, rnd.choice([-1, 1]) * rnd.randint(300, 900))]),
                     s=A([(t0, [0, 0]), (t0 + 4, [100, 100]), (n - 1, [100, 100])]),
                     o=A([(t0, 100), (n - 14, 100), (n - 1, 0)])))
        shapes.append(g)
    return comp("confetti", n, [layer(shapes, n)])


def twinkle(c):
    n, shapes = 36, []
    spots = [(0, 0, 1.0, 0), (-190, -130, 0.45, 6), (210, -90, 0.55, 10), (150, 170, 0.35, 14), (-150, 150, 0.4, 3)]
    for i, (x, y, k, d) in enumerate(spots):
        sc = 100 * k
        shapes.append(group([star(4, 150, 18), fill(c["light"] if i % 2 == 0 else c["main"])],
                            tr(p=[x, y], s=A([(d, [0, 0]), (d + 9, [sc * 1.15] * 2), (d + 20, [sc * 0.9] * 2), (min(n - 1, d + 28), [0, 0])]),
                               r=A([(d, -30), (min(n - 1, d + 28), 60)]))))
    return comp("twinkle", n, [layer(shapes, n)])


def scribble(c):
    n, w, h = 30, 1080, 200
    verts = [[-440, 10], [-250, -22], [-60, 20], [130, -18], [320, 16], [440, -8]]
    n_v = len(verts)
    i_t, o_t = [], []
    for k in range(n_v):
        i_t.append([-60, 0] if k else [0, 0])
        o_t.append([60, 0] if k < n_v - 1 else [0, 0])
    path = {"ty": "sh", "ks": S({"i": i_t, "o": o_t, "v": verts, "c": False})}
    trim = {"ty": "tm", "s": S(0), "e": A([(1, 0), (16, 100)]), "o": S(0), "m": 1}
    g1 = group([path, trim, stroke(c["main"], 16)], tr())
    g2 = group([path, {"ty": "tm", "s": S(0), "e": A([(6, 0), (22, 100)]), "o": S(0), "m": 1}, stroke(c["alt"], 7)],
               tr(p=[0, 16]))
    return comp("scribble", n, [layer([g2, g1], n, w=w, h=h)], w=w, h=h)


def circle(c):
    """Lingkaran coretan tangan (2 goresan) yang digambar mengelilingi angka/kata."""
    n, w, h = 34, 900, 420
    def ring(col, wd, rot, scale, t0):
        return group([{"ty": "el", "p": S([0, 0]), "s": S([780, 300])},
                      {"ty": "tm", "s": A([(t0, 0), (t0 + 18, 8)]), "e": A([(t0, 0), (t0 + 18, 100)]), "o": S(rot), "m": 1},
                      stroke(col, wd)], tr(r=rot * 0.02 - 4, s=[scale, scale]))
    return comp("circle", n, [layer([ring(c["alt"], 7, 20, 100, 6), ring(c["main"], 12, 0, 100, 0)], n, w=w, h=h)], w=w, h=h)


def arrow(c):
    """Panah melengkung yang digambar lalu kepala panah muncul."""
    n, w, h = 30, 600, 420
    v = [[-230, 140], [-120, -60], [60, -130], [210, -90]]
    i_t = [[0, 0], [-60, 60], [-70, -10], [-50, -30]]
    o_t = [[40, -80], [60, -60], [60, 10], [0, 0]]
    path = {"ty": "sh", "ks": S({"i": i_t, "o": o_t, "v": v, "c": False})}
    body = group([path, {"ty": "tm", "s": S(0), "e": A([(0, 0), (14, 100)]), "o": S(0), "m": 1}, stroke(c["main"], 14)], tr())
    def wing(dx, dy):
        p = {"ty": "sh", "ks": S({"i": [[0, 0], [0, 0]], "o": [[0, 0], [0, 0]], "v": [[210, -90], [210 + dx, -90 + dy]], "c": False})}
        return group([p, {"ty": "tm", "s": S(0), "e": A([(12, 0), (19, 100)]), "o": S(0), "m": 1}, stroke(c["main"], 14)], tr())
    return comp("arrow", n, [layer([wing(-52, -6), wing(-14, 52), body], n, w=w, h=h)], w=w, h=h)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for pk, c in PALETTES.items():
        for name, fn in [("burst", burst), ("rings", rings), ("confetti", confetti), ("twinkle", twinkle), ("scribble", scribble), ("circle", circle), ("arrow", arrow)]:
            with open(os.path.join(OUT, f"{name}_{pk}.json"), "w") as f:
                json.dump(fn(c), f, separators=(",", ":"))
    print("ok", sorted(os.listdir(OUT)))
