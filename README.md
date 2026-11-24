# Simulador del taller Gene Haas de IQS para el SocialTech Challenge 2027

Simulador en Gazebo del taller Gene Haas de IQS, con el robot Tracer2 listo para usar desde ROS 2. Incluye la sala de máquinas, la sala de células y el robot con LiDAR 2D, IMU y odometría.

El simulador no incluye mapeo, localización ni navegación: cada equipo los aporta con su propio software.

## Requisitos

- Ubuntu 24.04. En Windows, podéis instalarlo en una máquina virtual de VirtualBox.
- ROS 2 Jazzy, siguiendo la guía oficial: <https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html>.

Con ROS 2 Jazzy instalado, añadid las dependencias del simulador:

```bash
sudo apt update
sudo apt install git python3-colcon-common-extensions ros-jazzy-desktop ros-jazzy-ros-gz ros-jazzy-xacro ros-jazzy-teleop-twist-keyboard
```

## Clonar, compilar y arrancar

```bash
git clone https://github.com/alexllambrichcastells/socialtech-gene-haas-sim.git
cd socialtech-gene-haas-sim/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
ros2 launch gene_haas_bringup gene_haas_tracer2.launch.py
```

Al iniciar la simulación, el Tracer2 aparece en el punto 1, la salida del circuito, en la sala de células, orientado hacia la puerta de cristal.

## Más información

En [`ros2_ws/README.md`](ros2_ws/README.md) encontraréis los tópicos del robot, la teleoperación por teclado y los ajustes para VirtualBox.

## Recursos de terceros

- El Tracer2 se ha adaptado del simulador [SocialTech-Gazebo](https://github.com/SocialTech-Challenge/SocialTech-Gazebo), con licencia BSD.
- Las mallas de las máquinas Haas y de las células SMC son modelos CAD de sus fabricantes.
- El logotipo del cartel es una marca registrada de Haas Automation.
