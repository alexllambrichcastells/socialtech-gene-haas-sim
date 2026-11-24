#!/usr/bin/env python3
"""Genera modelos/gene_haas_env_grueso/model.sdf: el sótano de Gene Haas con paredes gruesas y ventanas altas y estrechas.

    python3 herramientas/generar_gene_haas_env_grueso.py

Método (reversible y sin tocar el interior):
  - Se reutiliza SIN MODIFICAR la malla original model://gene_haas_env/meshes/Sotano.dae (visual + collision): suelo, pilares
    y caras interiores de las paredes quedan exactamente donde estaban.
  - Se añaden cajas con visual y collision idénticas:
      * relleno_ventana_*: cierra la parte baja de cada ventana de la pared sur (z 1.00 -> VENTANA_Z0) en la cáscara de 1 cm.
      * recrecido_*: cajas pegadas a la cara EXTERIOR de cada pared del contorno, hacia fuera, hasta un grosor total ESPESOR,
        dejando los mismos huecos de ventanas (ya estrechadas), puertas y pasos. Las esquinas exteriores (convexas) se cierran
        alargando las cajas; en las esquinas interiores las cajas se solapan por fuera del edificio.
  - El tabique de vidrio y su puerta son modelos aparte y no se tocan.
  - suelo_exterior: plano en z = 0 (1 cm bajo el suelo interior): visual finito alrededor del edificio y collision infinita,
    para que el robot no caiga al vacío si sale por las puertas o el paso de la sala de células.
Revertir: en mundo/gene_haas.sdf, volver a <uri>model://gene_haas_env</uri>.

Todas las coordenadas salen de las caras de Sotano.dae (paredes de 1 cm, 2.70 m de alto). Medidas nuevas APROXIMADAS.
"""
import math
from pathlib import Path

ESPESOR = 0.25            # grosor total aproximado de las paredes exteriores (m); la malla ya aporta 0.01 m
ALTO = 2.70               # altura de las paredes en Sotano.dae
CASCARA = 0.01            # grosor de la cáscara de la malla original
VENTANA_Z0, VENTANA_Z1 = 2.10, 2.50   # ventanas altas y estrechas (antes z 1.00 - 2.50); aproximado
VENTANA_Z0_ORIG = 1.00
COLOR = "0.92 0.92 0.92 1"
SUELO_EXT_MARGEN = 4.0    # suelo exterior alrededor del edificio (m)
COLOR_SUELO_EXT = "0.55 0.56 0.58 1"
# Los rellenos de ventana quedan en la cara INTERIOR, junto a la malla original (que se ve casi blanca, sin sombreado apreciable):
# se les da emisión para que se vean como la pared y no como un hueco oscuro.
MATERIAL_RELLENO = "<ambient>1 1 1 1</ambient><diffuse>1 1 1 1</diffuse><emissive>0.62 0.62 0.62 1</emissive>"

T = ESPESOR - CASCARA     # recrecido hacia fuera de la cara exterior actual

# Contorno EXTERIOR (cara exterior de la cáscara de 1 cm), en sentido antihorario: el interior queda a la izquierda.
# Huecos por tramo: (desde, hasta) medidos a lo largo del tramo desde su vértice inicial, y (z0, z1).
VENTANAS_SUR_X = [(-11.218, -8.893), (-7.018, -4.693), (-2.818, -0.493), (1.382, 3.707)]
CONTORNO = [
    # nombre,                    inicio,               fin,                 huecos [(x_ini, x_fin, z0, z1)] en coordenada del eje del tramo
    ("pared_sur_sala_maquinas", (-11.8185, -4.710), (3.882, -4.710),   [(a, b, VENTANA_Z0, VENTANA_Z1) for a, b in VENTANAS_SUR_X]),
    ("pared_este_sala_maquinas", (3.882, -4.710),   (3.882, -0.348),   []),
    ("pared_sur_sala_celulas",  (3.882, -0.348),    (7.918, -0.348),   [(6.969, 7.769, 0.0, 2.0)]),     # puerta
    ("pared_escalon_celulas",   (7.918, -0.348),    (7.918, -4.925),   []),
    ("pared_sur2_sala_celulas", (7.918, -4.925),    (11.818, -4.925),  [(8.519, 9.318, 0.0, 2.0)]),     # puerta
    ("pared_este_tramo_sur",    (11.818, -4.925),   (11.818, -4.250),  []),
    ("entrante_sur",            (11.818, -4.250),   (9.869, -4.250),   []),
    ("entrante_oeste",          (9.869, -4.250),    (9.869, -1.550),   []),
    ("entrante_norte",          (9.869, -1.550),    (11.818, -1.550),  []),
    ("pared_este_sala_celulas", (11.818, -1.550),   (11.818, 4.925),   [(-1.550, 1.750, 0.0, 2.2),      # paso ancho
                                                                         (3.225, 4.025, 0.0, 2.0)]),     # puerta
    ("pared_norte",             (11.818, 4.925),    (-11.1185, 4.925), []),
    ("pared_oeste_diagonal",    (-11.1185, 4.925),  (-11.8185, -4.710), []),
]


def coord_eje(p, d):
    """Coordenada de un punto a lo largo del eje principal del tramo (x si es horizontal, y si es vertical)."""
    return p[0] if abs(d[0]) >= abs(d[1]) else p[1]


def giro(d1, d2):
    return d1[0] * d2[1] - d1[1] * d2[0]          # > 0: giro a la izquierda (esquina convexa en un contorno antihorario)


def cajas():
    out = []
    n = len(CONTORNO)
    for i, (nombre, a, b, huecos) in enumerate(CONTORNO):
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy)
        u = (dx / L, dy / L)
        nfuera = (u[1], -u[0])                    # normal exterior (el interior está a la izquierda)
        prev_u = (lambda p: ((p[2][0] - p[1][0]) / math.hypot(p[2][0] - p[1][0], p[2][1] - p[1][1]),
                             (p[2][1] - p[1][1]) / math.hypot(p[2][0] - p[1][0], p[2][1] - p[1][1])))(CONTORNO[i - 1])
        sig = CONTORNO[(i + 1) % n]
        sig_u = ((sig[2][0] - sig[1][0]) / math.hypot(sig[2][0] - sig[1][0], sig[2][1] - sig[1][1]),
                 (sig[2][1] - sig[1][1]) / math.hypot(sig[2][0] - sig[1][0], sig[2][1] - sig[1][1]))
        ext_ini = T if giro(prev_u, u) > 0 else 0.0   # alargar en esquinas convexas para cerrarlas
        ext_fin = T if giro(u, sig_u) > 0 else 0.0
        # intervalos a lo largo del tramo (s en metros desde a), con sus huecos
        s_huecos = []
        for h0, h1, z0, z1 in huecos:
            c0, c1 = coord_eje(a, u), coord_eje(b, u)
            sgn = 1 if c1 > c0 else -1
            s0, s1 = sorted(((h0 - c0) * sgn / (abs(u[0]) if abs(u[0]) >= abs(u[1]) else abs(u[1])),
                             (h1 - c0) * sgn / (abs(u[0]) if abs(u[0]) >= abs(u[1]) else abs(u[1]))))
            s_huecos.append((s0, s1, z0, z1))
        s_huecos.sort()
        cortes = [(-ext_ini, None)]
        piezas = []                                 # (s0, s1, z0, z1)
        s = -ext_ini
        for s0, s1, z0, z1 in s_huecos:
            if s0 > s:
                piezas.append((s, s0, 0.0, ALTO))
            if z0 > 0:
                piezas.append((s0, s1, 0.0, z0))
            if z1 < ALTO:
                piezas.append((s0, s1, z1, ALTO))
            s = s1
        if L + ext_fin > s:
            piezas.append((s, L + ext_fin, 0.0, ALTO))
        yaw = math.atan2(u[1], u[0])
        for k, (s0, s1, z0, z1) in enumerate(piezas, 1):
            sm = (s0 + s1) / 2
            cx = a[0] + u[0] * sm + nfuera[0] * T / 2
            cy = a[1] + u[1] * sm + nfuera[1] * T / 2
            out.append((f"recrecido_{nombre}_{k}", (cx, cy, (z0 + z1) / 2, yaw), (s1 - s0, T, z1 - z0)))
    # rellenos de la parte baja de las ventanas en la cáscara de 1 cm (entre la cara interior y la exterior)
    for k, (x0, x1) in enumerate(VENTANAS_SUR_X, 1):
        out.append((f"relleno_ventana_{k}", ((x0 + x1) / 2, -4.705, (VENTANA_Z0_ORIG + VENTANA_Z0) / 2, 0.0),
                    (x1 - x0, CASCARA, VENTANA_Z0 - VENTANA_Z0_ORIG)))
    # suelo exterior (plano; ver main): la malla original solo tiene suelo dentro del edificio y la sala de células tiene puertas y un paso al
    # exterior; sin esto, el robot que sale cae al vacío. Cara superior en z = 0 (1 cm por debajo del suelo interior, sin
    # coincidir con él), con margen de SUELO_EXT_MARGEN m alrededor del edificio.
    x0, x1, y0, y1 = -11.8185 - SUELO_EXT_MARGEN, 11.818 + SUELO_EXT_MARGEN, -4.925 - SUELO_EXT_MARGEN, 4.925 + SUELO_EXT_MARGEN
    out.append(("suelo_exterior", ((x0 + x1) / 2, (y0 + y1) / 2, -0.01, 0.0), (x1 - x0, y1 - y0, 0.02)))
    return out


def main():
    raiz = Path(__file__).resolve().parent.parent
    destino = raiz / 'modelos' / 'gene_haas_env_grueso'
    destino.mkdir(parents=True, exist_ok=True)
    L = ['<?xml version="1.0" ?>', '<sdf version="1.9">',
         '  <!-- GENERADO por herramientas/generar_gene_haas_env_grueso.py: no editar a mano, cambiar los parámetros del script.',
         f'       Sótano de Gene Haas con paredes de ~{ESPESOR:.2f} m (recrecidas hacia FUERA) y ventanas altas y estrechas',
         f'       (z {VENTANA_Z0:.2f}-{VENTANA_Z1:.2f} m, antes {VENTANA_Z0_ORIG:.2f}-{VENTANA_Z1:.2f}). Medidas APROXIMADAS.',
         '       La malla original Sotano.dae (modelo gene_haas_env) se reutiliza sin cambios: interior idéntico.',
         '       Revertir: en mundo/gene_haas.sdf usar <uri>model://gene_haas_env</uri>. -->',
         '  <model name="gene_haas_env_grueso">', '    <static>true</static>', '    <link name="sotano">',
         '      <collision name="sotano_collision">',
         '        <geometry><mesh><uri>model://gene_haas_env/meshes/Sotano.dae</uri></mesh></geometry>',
         '      </collision>',
         '      <visual name="sotano_visual">',
         '        <geometry><mesh><uri>model://gene_haas_env/meshes/Sotano.dae</uri></mesh></geometry>',
         '      </visual>']
    for nombre, (x, y, z, yaw), (sx, sy, sz) in cajas():
        pose = f'{x:.4f} {y:.4f} {z:.4f} 0 0 {yaw:.5f}'
        geo = f'<box><size>{sx:.4f} {sy:.4f} {sz:.4f}</size></box>'
        if nombre == 'suelo_exterior':
            # visual: losa finita alrededor del edificio; collision: PLANO INFINITO en z = 0 (no hay borde por el que caer)
            pose_plano = f'{x:.4f} {y:.4f} 0 0 0 0'
            L.append(f'      <visual name="{nombre}">\n        <pose>{pose_plano}</pose>\n'
                     f'        <geometry><plane><normal>0 0 1</normal><size>{sx:.4f} {sy:.4f}</size></plane></geometry>\n'
                     f'        <material><ambient>{COLOR_SUELO_EXT}</ambient><diffuse>{COLOR_SUELO_EXT}</diffuse></material>\n      </visual>')
            L.append(f'      <collision name="{nombre}_collision">\n        <pose>{pose_plano}</pose>\n'
                     f'        <geometry><plane><normal>0 0 1</normal><size>{sx:.4f} {sy:.4f}</size></plane></geometry>\n      </collision>')
            continue
        mat = (MATERIAL_RELLENO if nombre.startswith('relleno_ventana') else
               f'<ambient>{COLOR_SUELO_EXT}</ambient><diffuse>{COLOR_SUELO_EXT}</diffuse>' if nombre == 'suelo_exterior' else
               f'<ambient>{COLOR}</ambient><diffuse>{COLOR}</diffuse>')
        L.append(f'      <visual name="{nombre}">\n        <pose>{pose}</pose>\n        <geometry>{geo}</geometry>\n'
                 f'        <material>{mat}</material>\n      </visual>')
        L.append(f'      <collision name="{nombre}_collision">\n        <pose>{pose}</pose>\n        <geometry>{geo}</geometry>\n      </collision>')
    L += ['    </link>', '  </model>', '</sdf>']
    (destino / 'model.sdf').write_text('\n'.join(L) + '\n')
    (destino / 'model.config').write_text(
        '<?xml version="1.0" ?>\n<model>\n  <name>gene_haas_env_grueso</name>\n  <version>1.0</version>\n'
        '  <sdf version="1.9">model.sdf</sdf>\n'
        f'  <description>Sótano de Gene Haas con paredes exteriores de ~{ESPESOR:.2f} m (recrecidas hacia fuera, interior intacto) y '
        f'ventanas altas y estrechas (z {VENTANA_Z0:.2f}-{VENTANA_Z1:.2f} m). Reutiliza Sotano.dae de gene_haas_env sin cambios + cajas. '
        'Generado por herramientas/generar_gene_haas_env_grueso.py. Medidas APROXIMADAS.</description>\n</model>\n')
    print(f'{destino / "model.sdf"}: {len(cajas())} cajas')


if __name__ == '__main__':
    main()
