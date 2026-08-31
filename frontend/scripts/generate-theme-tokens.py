"""
Genera los bloques de tokens de los temas de color (D-80) para `src/style.css`.

    python frontend/scripts/generate-theme-tokens.py

Existe porque **estos valores no se pueden elegir a ojo**, por dos razones que
se verifican acá y no en el navegador:

1. **Gamut.** El chroma máximo de sRGB depende del hue. A L=0.556 el violeta
   llega a 0.275 pero el naranja solo a 0.125 y el verde menta a 0.115. Reusar
   el 0.197 del violeta para todos hace que el navegador recorte el color a
   algo sucio que nadie eligió. `clamp_chroma` lo baja hasta que entra.

2. **Contraste.** `--primary-foreground` no puede ser blanco fijo: sobre salmón
   da 2.52 y sobre sol 2.66, ambos reprueban WCAG AA (4.5). `foreground` mide
   los dos candidatos y se queda con el que gana.

Imprime una tabla de verificación (color resultante, texto elegido, contraste y
si el chroma se recortó) y escribe el CSS por stdout para pegarlo en
`style.css`. Si algún par tema×modo baja de 4.5, sale marcado como BAJO.
"""
from __future__ import annotations

import math

#  (slug, etiqueta, hue, primario claro L/C, primario oscuro L/C)
THEMES = [
    ("violeta", "Violeta", 313.6, (0.556, 0.197), (0.650, 0.190)),
    ("carmesi", "Carmesí", 25.0, (0.556, 0.180), (0.650, 0.175)),
    ("sol", "Sol", 65.0, (0.700, 0.180), (0.780, 0.165)),
    ("verde", "Verde menta", 165.0, (0.620, 0.130), (0.720, 0.130)),
    ("salmon", "Salmón", 35.0, (0.720, 0.160), (0.780, 0.140)),
    #  Grafito no tiene color: chroma 0 en los dos modos. La inversión
    #  (negro en claro → blanco en oscuro) no es estética, es necesidad: un
    #  primario L=0.20 sobre el fondo oscuro da contraste 1.45, invisible.
    ("grafito", "Grafito", 0.0, (0.200, 0.000), (0.950, 0.000)),
]

#  Rampas calcadas de la escala violeta original, para que ningún tema invente
#  una progresión distinta. En oscuro el accent es neutro para todos.
LIGHT_RAMP = {
    "accent": (0.940, 0.030),
    "accent-foreground": (0.350, 0.150),
    "chart-2": (0.650, 0.150),
    "chart-3": (0.400, 0.120),
    "chart-4": (0.750, 0.080),
    "chart-5": (0.300, 0.060),
}
DARK_RAMP = {
    "chart-2": (0.750, 0.150),
    "chart-3": (0.550, 0.140),
    "chart-4": (0.850, 0.080),
    "chart-5": (0.450, 0.100),
}
DARK_NEUTRAL_ACCENT = [
    ("accent", "oklch(0.269 0 0)"),
    ("accent-foreground", "oklch(0.985 0 0)"),
    ("sidebar-accent", "oklch(0.269 0 0)"),
    ("sidebar-accent-foreground", "oklch(0.985 0 0)"),
]

WHITE_L, BLACK_L = 0.985, 0.145


def oklch_to_linear(L: float, C: float, H: float) -> tuple[float, float, float]:
    h = math.radians(H)
    a, b = C * math.cos(h), C * math.sin(h)
    l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    return (
        4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
        -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
        -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s,
    )


def in_gamut(rgb: tuple[float, float, float], tol: float = 0.001) -> bool:
    return all(-tol <= c <= 1 + tol for c in rgb)


def luminance(rgb: tuple[float, float, float]) -> float:
    r, g, b = (min(1.0, max(0.0, c)) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b) -> float:
    ya, yb = luminance(a), luminance(b)
    return (max(ya, yb) + 0.05) / (min(ya, yb) + 0.05)


def to_hex(rgb) -> str:
    def gamma(c: float) -> float:
        c = min(1.0, max(0.0, c))
        return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055
    return "#" + "".join(f"{round(gamma(c) * 255):02X}" for c in rgb)


def clamp_chroma(L: float, C: float, H: float) -> float:
    c = C
    while c > 0 and not in_gamut(oklch_to_linear(L, c, H)):
        c -= 0.005
    return round(max(c, 0.0), 3)


def best_foreground(L: float, C: float, H: float) -> tuple[float, float]:
    """Devuelve `(luminosidad del texto, contraste)` — blanco o negro."""
    rgb = oklch_to_linear(L, C, H)
    cw = contrast(rgb, oklch_to_linear(WHITE_L, 0, 0))
    cb = contrast(rgb, oklch_to_linear(BLACK_L, 0, 0))
    return (WHITE_L, cw) if cw >= cb else (BLACK_L, cb)


def color(L: float, C: float, H: float, *, neutral: bool) -> str:
    if neutral:
        return f"oklch({L:g} 0 0)"
    c = clamp_chroma(L, C, H)
    return f"oklch({L:g} {c:g} {H:g})" if c > 0 else f"oklch({L:g} 0 0)"


def main() -> None:
    report, css = [], []
    report.append(f"{'tema':<12} {'modo':<7} {'color':<9} {'texto':<7} {'contraste':>10}  chroma")
    report.append("-" * 68)

    for slug, label, H, (light_L, light_C), (dark_L, dark_C) in THEMES:
        neutral = light_C == 0 and dark_C == 0

        for mode, (L, C) in (("claro", (light_L, light_C)), ("oscuro", (dark_L, dark_C))):
            real = clamp_chroma(L, C, H)
            _, ratio = best_foreground(L, real, H)
            flag = "OK" if ratio >= 4.5 else "BAJO"
            clip = f"{C:.3f}" if real == C else f"{C:.3f}->{real:.3f} (recortado)"
            fg = "blanco" if best_foreground(L, real, H)[0] == WHITE_L else "negro"
            report.append(
                f"{label:<12} {mode:<7} {to_hex(oklch_to_linear(L, real, H)):<9} "
                f"{fg:<7} {ratio:>7.2f} {flag}  {clip}"
            )

        # --- claro
        fg_l = f"oklch({best_foreground(light_L, clamp_chroma(light_L, light_C, H), H)[0]:g} 0 0)"
        primary_l = color(light_L, light_C, H, neutral=neutral)
        rows = [
            ("brand-hue", f"{H:g}"),
            ("brand-chroma", f"{clamp_chroma(light_L, light_C, H):g}"),
            ("primary", primary_l),
            ("primary-foreground", fg_l),
            ("ring", primary_l),
            ("accent", color(*LIGHT_RAMP["accent"], H, neutral=neutral)),
            ("accent-foreground", color(*LIGHT_RAMP["accent-foreground"], H, neutral=neutral)),
            #  Color del tema **como tinta sobre superficie clara** (íconos del
            #  sidebar). No puede ser `--primary`: sol, verde y salmón tienen
            #  primarios claros a propósito —llevan texto oscuro encima— y sobre
            #  un sidebar casi blanco dan 2.31, 2.90 y 2.20, bajo el mínimo de
            #  3.0 para íconos. A L=0.50 el peor caso sube a 4.82.
            #  Grafito conserva su primario (negro, 17.34): bajarlo a gris medio
            #  le quitaría justo lo que lo define.
            ("brand-icon", primary_l if neutral else color(0.50, light_C, H, neutral=False)),
            ("chart-1", primary_l),
            *[(k, color(*LIGHT_RAMP[k], H, neutral=neutral)) for k in
              ("chart-2", "chart-3", "chart-4", "chart-5")],
            ("sidebar-primary", primary_l),
            ("sidebar-primary-foreground", fg_l),
            ("sidebar-accent", color(*LIGHT_RAMP["accent"], H, neutral=neutral)),
            ("sidebar-accent-foreground",
             color(*LIGHT_RAMP["accent-foreground"], H, neutral=neutral)),
            ("sidebar-ring", primary_l),
        ]
        sel = ':root,\n[data-theme="violeta"]' if slug == "violeta" else f'[data-theme="{slug}"]'
        css.append(f"{sel} {{\n" + "\n".join(f"  --{k}: {v};" for k, v in rows) + "\n}\n")

        # --- oscuro
        fg_d = f"oklch({best_foreground(dark_L, clamp_chroma(dark_L, dark_C, H), H)[0]:g} 0 0)"
        primary_d = color(dark_L, dark_C, H, neutral=neutral)
        rows_d = [
            ("brand-chroma", f"{clamp_chroma(dark_L, dark_C, H):g}"),
            ("primary", primary_d),
            ("primary-foreground", fg_d),
            #  Van acá y no en el bloque `.dark` general: ese y `[data-theme=x]`
            #  tienen la misma especificidad, y los bloques claros van después
            #  en el archivo — el accent claro (casi blanco) le ganaría al
            #  oscuro y los hover quedarían encandilando sobre fondo negro.
            *DARK_NEUTRAL_ACCENT,
            ("ring", primary_d),
            #  En oscuro el primario ya es la tinta correcta: sobre el sidebar
            #  oscuro va de 5.07 (violeta) a 15.48 (grafito), todos holgados.
            ("brand-icon", primary_d),
            ("chart-1", primary_d),
            *[(k, color(*DARK_RAMP[k], H, neutral=neutral)) for k in
              ("chart-2", "chart-3", "chart-4", "chart-5")],
            ("sidebar-primary", primary_d),
            ("sidebar-primary-foreground", fg_d),
            ("sidebar-ring", primary_d),
        ]
        sel_d = ('.dark,\n.dark[data-theme="violeta"]' if slug == "violeta"
                 else f'.dark[data-theme="{slug}"]')
        css.append(f"{sel_d} {{\n" + "\n".join(f"  --{k}: {v};" for k, v in rows_d) + "\n}\n")

    print("\n".join(report))
    print()
    print("/* ---- pegar en src/style.css ---- */")
    #  Claros primero y oscuros después: el orden importa (ver comentario de
    #  DARK_NEUTRAL_ACCENT y el bloque de temas en style.css).
    print("\n".join(css[::2]))
    print("\n".join(css[1::2]))


if __name__ == "__main__":
    main()
