#!/usr/bin/env python3
"""Genera modelos/gene_haas_env_grueso: el sótano de Gene Haas con paredes gruesas, ventanas altas y estrechas y la sala de
células cerrada por sus lados sur y este.

    python3 herramientas/generar_gene_haas_env_grueso.py

Método (la malla original model://gene_haas_env/meshes/Sotano.dae no se modifica):
  - meshes/Sotano_cerrado.dae se deriva de Sotano.dae:
      * se conservan tal cual las caras de las paredes de la sala de máquinas (sur y este), la pared norte y la pared oeste;
      * se quitan el anexo al sur de la sala de células (paredes, puertas y entrante) y las paredes sur y este de la sala de
        células, que tenían una puerta, un paso ancho y otra puerta;
      * la sala de células se cierra con dos paredes de 1 cm continuas, sin huecos, sobre las mismas caras interiores
        (sur y = -0.338, este x = 11.809), unidas a la pared este de la sala de máquinas y a la pared norte;
      * el suelo (z = 0.01) se triangula de nuevo con el contorno resultante, sin el anexo.
  - meshes/Pilares.dae: los tres pilares de la sala de máquinas, con los mismos triángulos de Sotano.dae (misma geometría y
    collision). Van en una malla aparte para que solo su visual sea rojo.
  - Cajas con visual y collision idénticas:
      * relleno_ventana_*: cierra la parte baja de cada ventana de la pared sur (z 1.00 -> VENTANA_Z0) en la cáscara de 1 cm.
      * recrecido_*: cajas pegadas a la cara EXTERIOR de cada pared del contorno, hacia fuera, hasta un grosor total ESPESOR,
        dejando los mismos huecos de ventanas (ya estrechadas). Las esquinas exteriores (convexas) se cierran alargando las
        cajas; en las esquinas interiores las cajas se solapan por fuera del edificio, salvo en el cerramiento de la sala de
        células, cuyas cajas se recortan para no duplicar volumen ni collision.
  - El tabique de vidrio y su puerta son modelos aparte y no se tocan.
  - suelo_exterior: plano en z = 0 (1 cm bajo el suelo interior): visual finito alrededor del edificio y collision infinita.
Revertir: en mundo/gene_haas.sdf, volver a <uri>model://gene_haas_env</uri> (malla original, sin cerramiento ni recrecidos).

Todas las coordenadas salen de las caras de Sotano.dae (paredes de 1 cm, 2.70 m de alto). Medidas nuevas APROXIMADAS.
"""
import math
import re
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
    #                                                                       y, opcional, (alargue_inicio, alargue_fin) fijos en m
    ("pared_sur_sala_maquinas", (-11.8185, -4.710), (3.882, -4.710),   [(a, b, VENTANA_Z0, VENTANA_Z1) for a, b in VENTANAS_SUR_X]),
    ("pared_este_sala_maquinas", (3.882, -4.710),   (3.882, -0.348),   []),
    # Cerramiento de la sala de células, sin huecos. Sur: empieza T más al este (la esquina interior ya la llena la pared este
    # de la sala de máquinas) y se alarga T en la esquina sureste. Este: sin alargar (las esquinas las cierran la sur y la norte).
    ("pared_sur_sala_celulas",  (3.882, -0.348),    (11.818, -0.348),  [], (-T, T)),
    ("pared_este_sala_celulas", (11.818, -0.348),   (11.818, 4.925),   [], (0.0, 0.0)),
    ("pared_norte",             (11.818, 4.925),    (-11.1185, 4.925), []),
    ("pared_oeste_diagonal",    (-11.1185, 4.925),  (-11.8185, -4.710), []),
]

# Cerramiento de la sala de células en la malla: esquinas de la cara interior (C, D, E) y exterior (C', D', E') de la cáscara de 1 cm.
# C/C' y E/E' coinciden con los extremos de la pared este de la sala de máquinas y de la pared norte de Sotano.dae.
CERR_INT = [(3.8715, -0.338), (11.8085, -0.338), (11.8085, 4.915)]
CERR_EXT = [(3.8815, -0.348), (11.8185, -0.348), (11.8185, 4.925)]
# Suelo: cara superior (z = 0.01) hasta las caras interiores de las paredes; cara inferior (z = 0) hasta las exteriores.
SUELO_INT = [(-11.8077, -4.700), (3.8715, -4.700), (3.8715, -0.338), (11.8085, -0.338), (11.8085, 4.915), (-11.1092, 4.915)]
SUELO_EXT = [(-11.8185, -4.710), (3.8815, -4.710), (3.8815, -0.348), (11.8185, -0.348), (11.8185, 4.925), (-11.1185, 4.925)]
SUELO_Z_INT, SUELO_Z_EXT = 0.01, 0.0
# Pilares de la sala de máquinas en Sotano.dae (x0, x1, y0, y1): 0.15 x 0.15 m, z 0.01 - 2.71.
PILARES = [(-8.4875, -8.3375, -1.469, -1.319), (-4.3305, -4.1805, -1.471, -1.321), (-0.2285, -0.0785, -1.461, -1.311)]
# Rojo industrial mate, solo para el visual de los pilares.
MATERIAL_PILAR = ("<ambient>0.55 0.07 0.06 1</ambient><diffuse>0.62 0.08 0.07 1</diffuse>"
                  "<specular>0.05 0.05 0.05 1</specular>")


def coord_eje(p, d):
    """Coordenada de un punto a lo largo del eje principal del tramo (x si es horizontal, y si es vertical)."""
    return p[0] if abs(d[0]) >= abs(d[1]) else p[1]


def giro(d1, d2):
    return d1[0] * d2[1] - d1[1] * d2[0]          # > 0: giro a la izquierda (esquina convexa en un contorno antihorario)


def cajas():
    out = []
    n = len(CONTORNO)
    for i, (nombre, a, b, huecos, *alargues) in enumerate(CONTORNO):
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
        if alargues:
            ext_ini, ext_fin = alargues[0]
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
    # suelo exterior (plano; ver main): la malla solo tiene suelo dentro del edificio. Cara superior en z = 0 (1 cm por debajo del suelo interior, sin
    # coincidir con él), con margen de SUELO_EXT_MARGEN m alrededor del edificio.
    x0, x1, y0, y1 = -11.8185 - SUELO_EXT_MARGEN, 11.818 + SUELO_EXT_MARGEN, -4.925 - SUELO_EXT_MARGEN, 4.925 + SUELO_EXT_MARGEN
    out.append(("suelo_exterior", ((x0 + x1) / 2, (y0 + y1) / 2, -0.01, 0.0), (x1 - x0, y1 - y0, 0.02)))
    return out


def leer_dae(ruta):
    """Triángulos de una malla DAE de una sola geometría (VERTEX + NORMAL): [((p0, p1, p2), normal)]."""
    texto = ruta.read_text()
    pos = list(map(float, re.search(r'positions-array" count="\d+">([^<]*)', texto).group(1).split()))
    nor = list(map(float, re.search(r'normals-array" count="\d+">([^<]*)', texto).group(1).split()))
    idx = list(map(int, re.search(r'<p>([^<]*)</p>', texto).group(1).split()))
    P = [tuple(pos[i:i + 3]) for i in range(0, len(pos), 3)]
    N = [tuple(nor[i:i + 3]) for i in range(0, len(nor), 3)]
    return [((P[idx[i]], P[idx[i + 2]], P[idx[i + 4]]), N[idx[i + 1]]) for i in range(0, len(idx), 6)]


def triangulo(a, b, c, n):
    """Triángulo con el orden de vértices antihorario visto desde la normal n."""
    u = [b[k] - a[k] for k in range(3)]
    v = [c[k] - a[k] for k in range(3)]
    cz = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
    return ((a, b, c) if sum(cz[k] * n[k] for k in range(3)) > 0 else (a, c, b)), n


def cuadrilatero(p, n):
    return [triangulo(p[0], p[1], p[2], n), triangulo(p[0], p[2], p[3], n)]


def poligono_suelo(contorno, z, n):
    # Contorno A B C D E F (sala de máquinas + sala de células): ABCF y CDEF son convexos.
    A, B, C, D, E, F = [(x, y, z) for x, y in contorno]
    return [triangulo(*t, n) for t in ((A, B, C), (A, C, F), (C, E, F), (C, D, E))]


def en_sala_celulas_o_anexo(p):
    """Vértice de las paredes sur/este de la sala de células o del anexo (todo lo que hay al este de la sala de máquinas,
    salvo la pared norte)."""
    return p[0] > 3.9 and p[1] < 4.9


def es_pilar(tri):
    """Cara de un pilar: sus tres vértices en la huella del MISMO pilar (no las del suelo que unen dos pilares)."""
    return any(all(x0 - 1e-3 <= p[0] <= x1 + 1e-3 and y0 - 1e-3 <= p[1] <= y1 + 1e-3 for p in tri[0]) and
               not es_suelo(tri) for x0, x1, y0, y1 in PILARES)


def es_suelo(tri):
    (pts, n) = tri
    return abs(n[2]) > 0.9 and all(abs(p[2] - SUELO_Z_INT) < 1e-4 or abs(p[2] - SUELO_Z_EXT) < 1e-4 for p in pts)


def malla_cerrada(tris_originales):
    """Sotano.dae sin el anexo ni las paredes sur/este de la sala de células, con el cerramiento continuo y el suelo nuevo."""
    tris = [t for t in tris_originales
            if not es_suelo(t) and not es_pilar(t) and not any(en_sala_celulas_o_anexo(p) for p in t[0])]
    (cx, cy), (dx, dy), (ex, ey) = CERR_INT
    (cx2, cy2), (dx2, dy2), (ex2, ey2) = CERR_EXT
    zi, ze = SUELO_Z_INT, SUELO_Z_EXT
    tris += cuadrilatero([(cx, cy, zi), (dx, dy, zi), (dx, dy, ALTO), (cx, cy, ALTO)], (0, 1, 0))           # sur, cara interior
    tris += cuadrilatero([(cx2, cy2, ze), (dx2, dy2, ze), (dx2, dy2, ALTO), (cx2, cy2, ALTO)], (0, -1, 0))   # sur, cara exterior
    tris += cuadrilatero([(dx, dy, zi), (ex, ey, zi), (ex, ey, ALTO), (dx, dy, ALTO)], (-1, 0, 0))          # este, cara interior
    tris += cuadrilatero([(dx2, dy2, ze), (ex2, ey2, ze), (ex2, ey2, ALTO), (dx2, dy2, ALTO)], (1, 0, 0))   # este, cara exterior
    tris += cuadrilatero([(cx, cy, ALTO), (dx, dy, ALTO), (dx2, dy2, ALTO), (cx2, cy2, ALTO)], (0, 0, 1))   # coronación sur
    tris += cuadrilatero([(dx, dy, ALTO), (ex, ey, ALTO), (ex2, ey2, ALTO), (dx2, dy2, ALTO)], (0, 0, 1))   # coronación este
    tris += poligono_suelo(SUELO_INT, zi, (0, 0, 1))
    tris += poligono_suelo(SUELO_EXT, ze, (0, 0, -1))
    # Las esquinas de arriba están redondeadas a 0.1 mm: se ajustan al vértice exacto de Sotano.dae (< 2 mm) para que las caras
    # nuevas compartan aristas con las conservadas, sin rendijas.
    originales = {p for pts, _ in tris_originales for p in pts}

    def ajustar(p):
        cerca = min(originales, key=lambda q: sum((p[k] - q[k]) ** 2 for k in range(3)))
        return cerca if max(abs(p[k] - cerca[k]) for k in range(3)) < 0.002 else p
    return [(tuple(ajustar(p) for p in pts), n) for pts, n in tris]


def escribir_dae(ruta, nombre, tris):
    vert, nor, idx = {}, {}, []
    for pts, n in tris:
        kn = tuple(round(c, 6) for c in n)
        nor.setdefault(kn, len(nor))
        for p in pts:
            kp = tuple(round(c, 6) for c in p)
            vert.setdefault(kp, len(vert))
            idx += [vert[kp], nor[kn]]
    fmt = lambda d: ' '.join(f'{c:.6g}' for k in d for c in k)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<COLLADA xmlns="http://www.collada.org/2005/11/COLLADASchema" version="1.4.1">\n'
        '<asset><contributor><authoring_tool>herramientas/generar_gene_haas_env_grueso.py (derivado de Sotano.dae)</authoring_tool>'
        '</contributor><unit name="meter" meter="1"/><up_axis>Z_UP</up_axis></asset>\n'
        f'<library_geometries><geometry id="mesh" name="{nombre}"><mesh>'
        f'<source id="positions"><float_array id="positions-array" count="{3 * len(vert)}">{fmt(vert)}</float_array>'
        f'<technique_common><accessor source="#positions-array" count="{len(vert)}" stride="3">'
        '<param name="X" type="float"/><param name="Y" type="float"/><param name="Z" type="float"/></accessor></technique_common></source>'
        f'<source id="normals"><float_array id="normals-array" count="{3 * len(nor)}">{fmt(nor)}</float_array>'
        f'<technique_common><accessor source="#normals-array" count="{len(nor)}" stride="3">'
        '<param name="X" type="float"/><param name="Y" type="float"/><param name="Z" type="float"/></accessor></technique_common></source>'
        '<vertices id="vertices"><input semantic="POSITION" source="#positions"/></vertices>'
        f'<triangles count="{len(tris)}"><input semantic="VERTEX" source="#vertices" offset="0"/>'
        f'<input semantic="NORMAL" source="#normals" offset="1"/><p>{" ".join(map(str, idx))}</p></triangles>'
        '</mesh></geometry></library_geometries>\n'
        f'<library_visual_scenes><visual_scene id="Scene" name="Scene"><node id="Model" name="{nombre}">'
        '<instance_geometry url="#mesh"/></node></visual_scene></library_visual_scenes>\n'
        '<scene><instance_visual_scene url="#Scene"/></scene>\n</COLLADA>\n')
    return len(tris)


def main():
    raiz = Path(__file__).resolve().parent.parent
    destino = raiz / 'modelos' / 'gene_haas_env_grueso'
    destino.mkdir(parents=True, exist_ok=True)
    originales = leer_dae(raiz / 'modelos' / 'gene_haas_env' / 'meshes' / 'Sotano.dae')
    n_malla = escribir_dae(destino / 'meshes' / 'Sotano_cerrado.dae', 'Sotano_cerrado', malla_cerrada(originales))
    n_pilares = escribir_dae(destino / 'meshes' / 'Pilares.dae', 'Pilares', [t for t in originales if es_pilar(t)])
    L = ['<?xml version="1.0" ?>', '<sdf version="1.9">',
         '  <!-- GENERADO por herramientas/generar_gene_haas_env_grueso.py: no editar a mano, cambiar los parámetros del script.',
         f'       Sótano de Gene Haas con paredes de ~{ESPESOR:.2f} m (recrecidas hacia FUERA) y ventanas altas y estrechas',
         f'       (z {VENTANA_Z0:.2f}-{VENTANA_Z1:.2f} m, antes {VENTANA_Z0_ORIG:.2f}-{VENTANA_Z1:.2f}). Medidas APROXIMADAS.',
         '       meshes/Sotano_cerrado.dae: Sotano.dae (modelo gene_haas_env) sin el anexo al sur de la sala de células y con la sala',
         '       de células cerrada por paredes continuas al sur y al este. La sala de máquinas queda igual.',
         '       Revertir: en mundo/gene_haas.sdf usar <uri>model://gene_haas_env</uri>. -->',
         '  <model name="gene_haas_env_grueso">', '    <static>true</static>', '    <link name="sotano">',
         '      <collision name="sotano_collision">',
         '        <geometry><mesh><uri>model://gene_haas_env_grueso/meshes/Sotano_cerrado.dae</uri></mesh></geometry>',
         '      </collision>',
         '      <visual name="sotano_visual">',
         '        <geometry><mesh><uri>model://gene_haas_env_grueso/meshes/Sotano_cerrado.dae</uri></mesh></geometry>',
         '      </visual>',
         '      <!-- Pilares de la sala de máquinas: misma geometría que en Sotano.dae; visual rojo y collision sin cambios. -->',
         '      <collision name="pilares_collision">',
         '        <geometry><mesh><uri>model://gene_haas_env_grueso/meshes/Pilares.dae</uri></mesh></geometry>',
         '      </collision>',
         '      <visual name="pilares_visual">',
         '        <geometry><mesh><uri>model://gene_haas_env_grueso/meshes/Pilares.dae</uri></mesh></geometry>',
         f'        <material>{MATERIAL_PILAR}</material>',
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
        f'  <description>Sótano de Gene Haas con paredes exteriores de ~{ESPESOR:.2f} m (recrecidas hacia fuera), '
        f'ventanas altas y estrechas (z {VENTANA_Z0:.2f}-{VENTANA_Z1:.2f} m) y la sala de células cerrada al sur y al este. '
        'Malla derivada de Sotano.dae de gene_haas_env + cajas. '
        'Generado por herramientas/generar_gene_haas_env_grueso.py. Medidas APROXIMADAS.</description>\n</model>\n')
    print(f'{destino / "model.sdf"}: {len(cajas())} cajas; Sotano_cerrado.dae: {n_malla} triángulos; Pilares.dae: {n_pilares}')


if __name__ == '__main__':
    main()
