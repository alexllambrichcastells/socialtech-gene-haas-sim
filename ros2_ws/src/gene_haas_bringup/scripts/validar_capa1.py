#!/usr/bin/env python3
"""Validación del simulador (Tracer2 en Gene Haas): LiDAR con distancias reales y movimiento coherente con /odom.

Con la simulación en marcha y el robot en el pasillo, en (-4.0, -0.2) mirando al este (NO es la pose por defecto del launch):
    ros2 launch gene_haas_bringup gene_haas_tracer2.launch.py x:=-4.0 y:=-0.2 yaw:=0.0
    ros2 run gene_haas_bringup validar_capa1.py
Si el robot no está en esa pose, el script lo indica y termina sin validar.

Comprueba:
  1. /scan, /odom, /imu y las TF publican.
  2. LiDAR: distancias a paredes conocidas del sótano desde la pose inicial (este, norte, sur) con tolerancia de 0.10 m,
     y que no devuelve el alcance mínimo en todos los rayos (fallo típico de gpu_lidar con la GPU virtual).
  3. Avance: 0.3 m/s durante 3 s simulados. El desplazamiento de /odom coincide con la pose real de Gazebo (gz model -p)
     y la lectura frontal del LiDAR disminuye lo mismo que avanza el robot.
  4. Giro: 0.5 rad/s durante 2 s simulados. El giro de /odom coincide con el de Gazebo.
Termina con código 0 si todo pasa.
"""
import math
import re
import subprocess
import sys
import time

import rclpy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Imu, LaserScan
from tf2_msgs.msg import TFMessage

POSE_INICIAL = (-4.0, -0.2, 0.0)
LIDAR_EN_BASE = (0.2125, 0.0)
# Paredes interiores del sótano (malla Sotano.dae): este de la sala principal x = 3.8715, norte y = 4.915, sur y = -4.70.
DISTANCIAS_ESPERADAS = {0.0: 3.8715 - (POSE_INICIAL[0] + LIDAR_EN_BASE[0]),
                        90.0: 4.915 - POSE_INICIAL[1],
                        -90.0: POSE_INICIAL[1] + 4.70}
TOLERANCIA = 0.10


def pose_gazebo(nombre, mundo='gene_haas'):
    """Pose real (x, y, yaw) del modelo en Gazebo, leída del topic de poses dinámicas del servidor.
    (gz model -p pide el estado completo del mundo y con el escenario cargado puede agotar el tiempo de espera.)"""
    out = subprocess.run(['gz', 'topic', '-e', '-t', f'/world/{mundo}/dynamic_pose/info', '-n', '1'],
                         capture_output=True, text=True, timeout=20).stdout
    bloque = out.split(f'name: "{nombre}"', 1)[1].split('}\npose {', 1)[0]
    v = {k: float(x) for k, x in re.findall(r'\b([xyzw]): (\S+)', bloque.split('orientation', 1)[0])}
    q = {k: float(x) for k, x in re.findall(r'\b([xyzw]): (\S+)', bloque.split('orientation', 1)[1])}
    return v['x'], v['y'], math.atan2(2 * (q['w'] * q['z'] + q['x'] * q['y']), 1 - 2 * (q['y'] ** 2 + q['z'] ** 2))


def yaw_de(q):
    return math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))


def dif_ang(a, b):
    return math.atan2(math.sin(a - b), math.cos(a - b))


class Validador(Node):
    def __init__(self):
        super().__init__('validar_capa1', parameter_overrides=[Parameter('use_sim_time', value=True)])
        self.scan = self.odom = self.imu = None
        self.tf_vistos = set()
        self.create_subscription(LaserScan, '/scan', lambda m: setattr(self, 'scan', m), qos_profile_sensor_data)
        self.create_subscription(Odometry, '/odom', lambda m: setattr(self, 'odom', m), 10)
        self.create_subscription(Imu, '/imu', lambda m: setattr(self, 'imu', m), qos_profile_sensor_data)
        self.create_subscription(TFMessage, '/tf', self.cb_tf, 10)
        self.pub = self.create_publisher(Twist, '/cmd_vel', 10)

    def cb_tf(self, m):
        for t in m.transforms:
            self.tf_vistos.add(f'{t.header.frame_id}->{t.child_frame_id}')

    def esperar(self, seg):
        fin = time.time() + seg
        while time.time() < fin:
            rclpy.spin_once(self, timeout_sec=0.05)

    def esperar_datos(self, seg=30):
        fin = time.time() + seg
        while time.time() < fin and None in (self.scan, self.odom, self.imu):
            rclpy.spin_once(self, timeout_sec=0.1)
        return None not in (self.scan, self.odom, self.imu)

    def rango(self, grados):
        s = self.scan
        i = round((math.radians(grados) - s.angle_min) / s.angle_increment)
        vals = [v for v in s.ranges[max(0, i - 2):i + 3] if math.isfinite(v)]
        return sorted(vals)[len(vals) // 2] if vals else float('inf')

    def ahora(self):
        return self.get_clock().now().nanoseconds * 1e-9

    def mover(self, lineal, angular, seg):
        """Publica la velocidad durante `seg` segundos de TIEMPO SIMULADO (reloj /clock) y para."""
        t = Twist()
        t.linear.x, t.angular.z = lineal, angular
        inicio, limite_real = self.ahora(), time.time() + 20 * seg + 30
        while self.ahora() - inicio < seg and time.time() < limite_real:
            self.pub.publish(t)
            self.esperar(0.05)
        self.pub.publish(Twist())
        fin = self.ahora()
        while self.ahora() - fin < 1.0 and time.time() < limite_real:   # 1 s simulado para detenerse
            self.pub.publish(Twist())
            self.esperar(0.05)
        return self.ahora() - inicio


def main():
    rclpy.init()
    n = Validador()
    fallos = []

    def check(ok, msg):
        print(('  OK    ' if ok else '  FALLO ') + msg)
        if not ok:
            fallos.append(msg)

    print('1) Topics')
    check(n.esperar_datos(), '/scan, /odom e /imu publican')
    if fallos:
        sys.exit(1)
    gx, gy, gyaw = pose_gazebo('tracer2')
    if math.hypot(gx - POSE_INICIAL[0], gy - POSE_INICIAL[1]) > 0.10 or abs(dif_ang(gyaw, POSE_INICIAL[2])) > 0.05:
        print(f'  El robot está en ({gx:.2f}, {gy:.2f}, yaw {gyaw:.2f}) y esta validación necesita la pose del pasillo '
              f'{POSE_INICIAL}. Lanza con: x:=-4.0 y:=-0.2 yaw:=0.0')
        sys.exit(2)
    n.esperar(1.0)
    check('odom->base_link' in n.tf_vistos, f'TF odom->base_link en /tf ({len(n.tf_vistos)} transformaciones dinámicas vistas)')
    s = n.scan
    print(f'   scan: frame {s.header.frame_id}, {len(s.ranges)} rayos, {math.degrees(s.angle_min):.0f}..{math.degrees(s.angle_max):.0f} deg, '
          f'{s.range_min}-{s.range_max} m | imu frame {n.imu.header.frame_id}, az = {n.imu.linear_acceleration.z:.2f}')

    print('2) LiDAR en la pose inicial')
    finitos = [v for v in s.ranges if math.isfinite(v)]
    check(sum(v <= s.range_min + 0.01 for v in finitos) < 0.5 * len(s.ranges), 'no devuelve el alcance mínimo en la mayoría de rayos')
    for ang, esp in DISTANCIAS_ESPERADAS.items():
        med = n.rango(ang)
        check(abs(med - esp) <= TOLERANCIA, f'{ang:+.0f} deg: medido {med:.3f} m, esperado {esp:.3f} m (pared del sótano)')

    print('3) Avance 0.3 m/s x 3 s simulados (esperado ~0.9 m)')
    g0, o0, f0 = pose_gazebo('tracer2'), n.odom.pose.pose, n.rango(0.0)
    n.mover(0.3, 0.0, 3.0)
    g1, o1, f1 = pose_gazebo('tracer2'), n.odom.pose.pose, n.rango(0.0)
    d_g = math.hypot(g1[0] - g0[0], g1[1] - g0[1])
    d_o = math.hypot(o1.position.x - o0.position.x, o1.position.y - o0.position.y)
    print(f'   Gazebo: {d_g:.3f} m | /odom: {d_o:.3f} m | LiDAR frontal: {f0:.3f} -> {f1:.3f} m')
    check(0.75 <= d_g <= 1.0, f'el robot avanza lo ordenado en Gazebo ({d_g:.3f} m)')
    check(abs(d_o - d_g) <= 0.05, f'/odom coincide con Gazebo (diferencia {abs(d_o - d_g):.3f} m)')
    check(abs((f0 - f1) - d_g) <= TOLERANCIA, f'el LiDAR frontal disminuye lo avanzado ({f0 - f1:.3f} m)')

    print('4) Giro 0.5 rad/s x 2 s simulados (esperado ~57 deg)')
    g0, y0 = pose_gazebo('tracer2'), yaw_de(n.odom.pose.pose.orientation)
    n.mover(0.0, 0.5, 2.0)
    g1, y1 = pose_gazebo('tracer2'), yaw_de(n.odom.pose.pose.orientation)
    a_g, a_o = dif_ang(g1[2], g0[2]), dif_ang(y1, y0)
    print(f'   Gazebo: {math.degrees(a_g):.1f} deg | /odom: {math.degrees(a_o):.1f} deg')
    check(math.radians(45) <= a_g <= math.radians(65), f'el robot gira lo ordenado en Gazebo ({math.degrees(a_g):.1f} deg)')
    check(abs(dif_ang(a_o, a_g)) <= math.radians(3), f'giro de /odom coincide con Gazebo (diferencia {math.degrees(abs(dif_ang(a_o, a_g))):.1f} deg)')

    n.destroy_node()
    rclpy.shutdown()
    print('RESULTADO:', 'TODO OK' if not fallos else f'{len(fallos)} fallo(s)')
    sys.exit(1 if fallos else 0)


if __name__ == '__main__':
    main()
