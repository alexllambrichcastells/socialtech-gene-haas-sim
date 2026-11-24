# ros2_ws — Tracer2 en Gene Haas: documentación técnica

Espacio de trabajo ROS 2 **separado del escenario**: el mundo `../mundo/gene_haas.sdf`, los modelos `../modelos/` y
`../config/` no se modifican. El robot se inserta dinámicamente al arrancar.

Incluye robot, sensores, puente ROS–Gazebo y teleoperación. **No incluye** mapa, localización, navegación ni SLAM: los añade cada equipo.

## Requisitos
Ubuntu 24.04 + ROS 2 **Jazzy** con `ros_gz` (Gazebo Harmonic), `robot_state_publisher`, `xacro`, `teleop_twist_keyboard`, `rviz2`
(todo incluido en `ros-jazzy-desktop` + `ros-jazzy-ros-gz`). No hace falta instalar nada más.

## Compilar
```bash
cd ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
```
`--symlink-install` permite que el launch encuentre solo la carpeta del proyecto (`mundo/`, `modelos/`). Si compilas sin él,
indica `escenario:=<ruta del proyecto>` o exporta `GENE_HAAS_DIR=<ruta del proyecto>`.

## Lanzar
```bash
# Terminal 1: escenario + robot + puente
ros2 launch gene_haas_bringup gene_haas_tracer2.launch.py            # rviz:=true para RViz2, gui:=false sin ventana
# Terminal 2: teleoperación por teclado (i = avanzar, , = retroceder, j/l = girar, k = parar)
source /opt/ros/jazzy/setup.bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
# Validación automática de LiDAR y odometría: necesita el robot en el pasillo (no en la pose por defecto)
ros2 launch gene_haas_bringup gene_haas_tracer2.launch.py x:=-4.0 y:=-0.2 yaw:=0.0   # terminal 1
ros2 run gene_haas_bringup validar_capa1.py                                          # terminal 2 (tras source install/setup.bash)
```

| Argumento | Por defecto | Qué hace |
|---|---|---|
| `gui` | `true` | Ventana de Gazebo (usa la GPU) |
| `servidor_software` | `true` | Servidor de Gazebo con `LIBGL_ALWAYS_SOFTWARE=1` (ver abajo) |
| `rviz` | `false` | RViz2 con modelo, TF, `/scan` y `/odom` |
| `x`, `y`, `yaw` | `5.6`, `0.85`, `3.14159` | Pose inicial (aproximada): sala de células, en el paso entre el bloque de mesas de entrada y la pared sur, mirando a la puerta del tabique |
| `lidar_hz` | `10` | Frecuencia del LiDAR (el Tracer2 original usaba 40) |

Por partes: `gene_haas_mundo.launch.py` (solo escenario) y `tracer2_spawn.launch.py` (robot + puente sobre un mundo ya abierto;
usado por separado conserva como pose por defecto el pasillo principal, (-4.0, -0.2) mirando al este).

### Pose inicial por defecto (aproximada)
`(x, y, yaw) = (5.6, 0.85, π)`: dentro de la sala de células, en el paso de 1.74 m entre el bloque de cuatro mesas de entrada y
la pared sur, unos 1.4 m antes de la abertura del tabique de vidrio y alineado con ella (abertura en y 0.29–1.49). Mirando al
oeste: al avanzar (`i` en teleop) cruza la puerta hacia la sala de máquinas. Márgenes aproximados: 0.27 m a las mesas, 0.90 m a
la pared sur y 0.32 m a la punta de la hoja abierta de la puerta. Cada equipo puede cambiarla con `x:=`, `y:=` y `yaw:=`.

## Por qué el servidor renderiza por software
En esta máquina virtual (GPU VMware SVGA3D) el sensor `gpu_lidar` de Gazebo devuelve el alcance mínimo (0.10 m) en todos
los rayos, con `ogre` y con `ogre2`, también en un mundo vacío. Con `LIBGL_ALWAYS_SOFTWARE=1` (llvmpipe) mide bien.
Solo el **servidor** (física + sensores) va por software; la **GUI** usa la GPU y sigue fluida.
Coste: cada lectura del LiDAR renderiza el escenario completo en CPU. Factor de tiempo real medido sin ventana:
**~0.45 con el LiDAR a 10 Hz** con el escenario completo y bastante menos a 40 Hz. En un equipo con GPU real: `servidor_software:=false`.

## Renderizado en máquinas virtuales (VirtualBox)
- Comprobado en VirtualBox con Ubuntu 24.04 (adaptador VMSVGA, aceleración 3D activada): el arranque por defecto funciona
  tal cual. El servidor ya renderiza por software (`servidor_software:=true` por defecto) y la ventana usa la GPU virtual.
- **El LiDAR marca 0.10 m en todos los rayos**: el servidor está usando la GPU. Comprueba que no se lanzó con
  `servidor_software:=false`.
- **La ventana de Gazebo sale negra o no abre**: lanza todo por software. La ventana irá más lenta, pero funciona:
  ```bash
  LIBGL_ALWAYS_SOFTWARE=1 ros2 launch gene_haas_bringup gene_haas_tracer2.launch.py
  ```
- **Con GPU real (sin máquina virtual)**: `servidor_software:=false` da más velocidad. Comprueba antes que `/scan` mide
  distancias reales (por ejemplo con `validar_capa1.py`).

## Paquetes
| Paquete | Contenido |
|---|---|
| `src/tracer2_description` | Tracer2 portado (xacro, mallas, sensores y sistemas de Harmonic, vista RViz2). Ver su README |
| `src/gene_haas_bringup` | Launch files, puente ROS–Gazebo (`config/puente_ros_gz.yaml`) y `scripts/validar_capa1.py` |

## Topics y frames
| Topic ROS 2 | Tipo | Sentido |
|---|---|---|
| `/cmd_vel` | `geometry_msgs/Twist` | ROS → Gazebo |
| `/odom` | `nav_msgs/Odometry` (`odom` → `base_link`) | Gazebo → ROS |
| `/tf` | `odom → base_link` (DiffDrive); el resto lo publica `robot_state_publisher` | Gazebo → ROS |
| `/joint_states` | ruedas y apoyos | Gazebo → ROS |
| `/scan` | `sensor_msgs/LaserScan`, frame `rslidar_link`, 720 rayos, ±90° | Gazebo → ROS |
| `/imu` | `sensor_msgs/Imu`, frame `imu_link` | Gazebo → ROS |
| `/clock` | tiempo simulado (todos los nodos con `use_sim_time`) | Gazebo → ROS |

Árbol TF: `odom → base_link → {base_footprint, rslidar_link, imu_link, rueda_*_Link, apoyo_*_Link}`.
El frame `map` (y `map → odom`) lo publica el SLAM o la localización de cada equipo.

## Validación (`validar_capa1.py`)
Desde la pose del pasillo (-4.0, -0.2) (lanzar con `x:=-4.0 y:=-0.2 yaw:=0.0`): el LiDAR mide las paredes del sótano a 0° (7.66 m), +90° (5.12 m) y −90° (4.50 m) con tolerancia de 0.10 m;
tras avanzar 0.3 m/s × 3 s y girar 0.5 rad/s × 2 s (tiempo simulado), `/odom` coincide con la pose real de Gazebo
y la lectura frontal del LiDAR disminuye lo avanzado.
