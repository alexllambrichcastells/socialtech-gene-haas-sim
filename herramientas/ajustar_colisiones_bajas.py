#!/usr/bin/env python3
"""Ajusta las collision de las máquinas y del mobiliario con malla para que, a la altura del robot, coincidan con lo visible.

    python3 herramientas/ajustar_colisiones_bajas.py

Problema que corrige: cada malla tenía como collision su caja envolvente completa (de 0 a la altura total). A la altura
del Tracer2 (chasis hasta 0.175 m; LiDAR a 0.20 m) varias máquinas son más estrechas que esa caja, así que el robot chocaba
con caras que el LiDAR no ve (hasta 0.56 m de "obstáculo invisible" en el pasillo).

Solución:
  * Máquinas y almacén de barras: dos cajas.
      - collision_baja  (z 0 - Z_CORTE): caja envolvente de la geometría VISIBLE entre Z_SUELO y Z_CORTE.
      - collision_alta  (z Z_CORTE - altura total): la caja envolvente completa de antes.
    El robot (≤ 0.24 m de alto) solo puede tocar la caja baja; personas y objetos altos siguen chocando con la alta.
  * Mesas de 0.70 x 1.70 m (01_02_Bancos_LEPI): 4 patas + tablero, igual que la geometría visible.
Las cajas nuevas están siempre contenidas en las antiguas: no se crean solapes nuevos.
"""
import glob
import re
from pathlib import Path

import numpy as np

Z_SUELO, Z_CORTE = 0.03, 0.30
RAIZ = Path(__file__).resolve().parent.parent
MAQUINAS = ["gene_haas_fresadora_vf2", "gene_haas_puesto_2_torno_st10", "gene_haas_fresadora_umc500", "gene_haas_fresadora_cm1",
            "gene_haas_fresadora_smm", "gene_haas_torno_st20y", "gene_haas_puesto_3_metrologia", "gene_haas_almacen_barras"]


def leer_malla(modelo):
    f = glob.glob(str(RAIZ / 'modelos' / modelo / 'meshes' / '*.dae'))[0]
    t = open(f).read()
    pos = np.array(re.search(r'<float_array id="positions-array"[^>]*>([^<]*)', t).group(1).split(), dtype=np.float32).reshape(-1, 3)
    tm = re.search(r'<triangles[^>]*>(.*?)<p>([^<]*)</p>', t, re.S)
    st = len(re.findall(r'offset=', tm.group(1)))
    tri = np.array(tm.group(2).split(), dtype=np.int64)[::st].reshape(-1, 3)
    return pos, tri


def envolvente_franja(pos, tri):
    """Caja envolvente (x, y) de la geometría visible entre Z_SUELO y Z_CORTE (muestreo denso de los triángulos)."""
    A, B, C = pos[tri[:, 0]], pos[tri[:, 1]], pos[tri[:, 2]]
    zmin = np.minimum(np.minimum(A[:, 2], B[:, 2]), C[:, 2]); zmax = np.maximum(np.maximum(A[:, 2], B[:, 2]), C[:, 2])
    s = (zmax >= Z_SUELO) & (zmin <= Z_CORTE); A, B, C = A[s], B[s], C[s]
    pts = []
    for u in np.linspace(0, 1, 9):
        for w in np.linspace(0, 1 - u, max(2, int((1 - u) * 8) + 1)):
            Q = A * u + B * w + C * (1 - u - w)
            pts.append(Q[(Q[:, 2] >= Z_SUELO) & (Q[:, 2] <= Z_CORTE)])
    P = np.vstack(pts)
    return P[:, 0].min(), P[:, 0].max(), P[:, 1].min(), P[:, 1].max()


def caja(nombre, cx, cy, cz, sx, sy, sz):
    return (f'      <collision name="{nombre}">\n        <pose>{cx:.4f} {cy:.4f} {cz:.4f} 0 0 0</pose>\n'
            f'        <geometry>\n          <box>\n            <size>{sx:.4f} {sy:.4f} {sz:.4f}</size>\n          </box>\n        </geometry>\n'
            f'      </collision>\n')


def sustituir_collision(modelo, bloque, nota):
    f = RAIZ / 'modelos' / modelo / 'model.sdf'
    s = f.read_text()
    s2, n = re.subn(r'      <collision name="(?:collision|collision_baja|collision_alta|collision_pata_\d|collision_tablero)">.*?</collision>\n',
                    '', s, flags=re.S)
    assert n >= 1, modelo
    i = s2.index('      <visual name=')
    s2 = s2[:i] + f'      <!-- {nota} (herramientas/ajustar_colisiones_bajas.py) -->\n' + bloque + s2[i:]
    s2 = re.sub(r'      <!-- [^\n]*\(herramientas/ajustar_colisiones_bajas.py\) -->\n(?=      <!-- )', '', s2)
    f.write_text(s2)


def main():
    for m in MAQUINAS:
        pos, tri = leer_malla(m)
        mn, mx = pos.min(0), pos.max(0)
        x0, x1, y0, y1 = envolvente_franja(pos, tri)
        H = float(mx[2])
        bloque = (caja('collision_baja', (x0 + x1) / 2, (y0 + y1) / 2, Z_CORTE / 2, x1 - x0, y1 - y0, Z_CORTE) +
                  caja('collision_alta', (mn[0] + mx[0]) / 2, (mn[1] + mx[1]) / 2, (Z_CORTE + H) / 2, mx[0] - mn[0], mx[1] - mn[1], H - Z_CORTE))
        sustituir_collision(m, bloque, f'Collision: baja (z 0-{Z_CORTE}) ajustada a lo visible a la altura del robot; alta = caja envolvente')
        print(f'{m:34s} baja x[{x0:+.3f},{x1:+.3f}] y[{y0:+.3f},{y1:+.3f}]  (envolvente x[{mn[0]:+.3f},{mx[0]:+.3f}] y[{mn[1]:+.3f},{mx[1]:+.3f}], H {H:.3f})')
    # mesas LEPI: patas (0.08 x 0.08 m en las esquinas, z 0-0.75) + tablero (z 0.75-0.83), medidas de la propia malla
    pos, _ = leer_malla('gene_haas_puesto_1_mesas')
    assert abs(pos[:, 2].max() - 0.83) < 1e-3
    bloque = ''.join(caja(f'collision_pata_{k}', sx * 0.31, sy * 0.64, 0.375, 0.08, 0.08, 0.75)
                     for k, (sx, sy) in enumerate(((1, 1), (1, -1), (-1, 1), (-1, -1)), 1))
    bloque += caja('collision_tablero', 0, 0, 0.79, 0.70, 1.70, 0.08)
    sustituir_collision('gene_haas_puesto_1_mesas', bloque, 'Collision: 4 patas + tablero, igual que la geometría visible')
    print('gene_haas_puesto_1_mesas           4 patas (x +-0.27..0.35, y +-0.60..0.68, z 0-0.75) + tablero (z 0.75-0.83)')


if __name__ == '__main__':
    main()
