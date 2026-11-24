# tracer2_description

Descripción del **Tracer2** (AGV diferencial de SocialTech) para ROS 2 Jazzy + Gazebo Harmonic.

## Origen y licencia
Portado de [SocialTech-Gazebo](https://github.com/SocialTech-Challenge/SocialTech-Gazebo) (paquete ROS 1 Noetic / Gazebo Classic, licencia **BSD**):
`urdf/tracer2.xacro`, `lidar.xacro`, `imu.xacro`, `tracer2.gazebo` y las mallas `meshes/*.STL`
(copiadas sin modificar; solo las que usa el robot).

## Archivos
| Archivo | Contenido |
|---|---|
| `urdf/tracer2.urdf.xacro` | Robot completo: chasis, ruedas motrices, apoyos, `base_footprint` |
| `urdf/tracer2_sensores.xacro` | Enlaces del LiDAR (`rslidar_link`) y de la IMU (`imu_link`) |
| `urdf/tracer2_gazebo.xacro` | Sistemas y sensores de Gazebo Harmonic (DiffDrive, JointStatePublisher, IMU, `gpu_lidar`) y fricción |
| `meshes/*.STL` | Mallas visuales del original |
| `rviz/tracer2.rviz` | Vista de RViz2: modelo, TF, `/scan`, `/odom` |

## Cambios respecto al original
- Plugins `gazebo_ros` (Classic) → sistemas de Harmonic declarados **en el robot** (el mundo no se toca).
- Collision con primitivas (caja 0.685 x 0.57 x 0.145 m, cilindros de rueda r = 0.0625 m, esferas de apoyo r = 0.0295 m) en vez de las mallas STL.
- Mallas con `file://$(find tracer2_description)/...`: valen para Gazebo y RViz2.
- Apoyos sin fricción; IMU sin collision; sin cámara en esta capa.
- LiDAR a 10 Hz por defecto (`xacro tracer2.urdf.xacro lidar_hz:=40` para la frecuencia original): con render por software, 40 Hz baja mucho el factor de tiempo real.

## Datos clave
| | Valor |
|---|---|
| Separación de ruedas / radio | 0.335 m / 0.0625 m |
| LiDAR | `gpu_lidar`, 720 muestras, ±90°, 0.10–30 m, ruido σ = 0.01 m, en (0.2125, 0, 0.20); frecuencia `lidar_hz` (10 Hz por defecto, 40 en el original) |
| IMU | 100 Hz, en (0, 0, 0.15) |
| Frames | `odom → base_link → {base_footprint, rslidar_link, imu_link, ruedas, apoyos}` |
| Topics (Gazebo y ROS 2) | `cmd_vel`, `odom`, `tf`, `joint_states`, `scan`, `imu` |
