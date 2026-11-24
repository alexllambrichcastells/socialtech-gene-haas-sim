"""Escenario Gene Haas en Gazebo Harmonic: servidor y GUI como procesos separados.

    ros2 launch gene_haas_bringup gene_haas_mundo.launch.py
    ros2 launch gene_haas_bringup gene_haas_mundo.launch.py gui:=false            # solo servidor
    ros2 launch gene_haas_bringup gene_haas_mundo.launch.py servidor_software:=false

- Servidor (física + sensores): con LIBGL_ALWAYS_SOFTWARE=1 (llvmpipe). En esta máquina virtual la GPU
  (VMware SVGA3D) hace que el sensor gpu_lidar devuelva el alcance mínimo en todos los rayos; con render por
  software mide distancias reales.
- GUI: con la GPU normal (más fluida con las mallas pesadas del escenario).
- El mundo se carga sin modificar desde <escenario>/mundo/gene_haas.sdf y los modelos desde <escenario>/modelos.
  <escenario> se localiza solo (subiendo desde este archivo hasta encontrar mundo/gene_haas.sdf; funciona con
  `colcon build --symlink-install`) o con la variable GENE_HAAS_DIR o el argumento escenario:=<ruta>.
- Cerrar el servidor cierra todo el launch.
"""
import os
from pathlib import Path

from launch import LaunchDescription
from launch.actions import (AppendEnvironmentVariable, DeclareLaunchArgument, EmitEvent, ExecuteProcess,
                            LogInfo, OpaqueFunction, RegisterEventHandler)
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.substitutions import LaunchConfiguration

MUNDO_REL = Path('mundo') / 'gene_haas.sdf'


def buscar_escenario():
    """Carpeta raíz del proyecto (la que contiene mundo/gene_haas.sdf)."""
    if os.environ.get('GENE_HAAS_DIR'):
        return os.environ['GENE_HAAS_DIR']
    for base in (Path(__file__).resolve(), Path.cwd().resolve()):
        for p in (base, *base.parents):
            if (p / MUNDO_REL).is_file():
                return str(p)
    return ''


def lanzar(context):
    escenario = Path(LaunchConfiguration('escenario').perform(context)).expanduser()
    mundo = escenario / MUNDO_REL
    if not mundo.is_file():
        raise RuntimeError(f'No encuentro {mundo}. Indica escenario:=<carpeta del proyecto> o exporta GENE_HAAS_DIR.')
    software = LaunchConfiguration('servidor_software').perform(context) == 'true'
    verbosidad = LaunchConfiguration('verbosidad').perform(context)

    servidor = ExecuteProcess(
        cmd=['gz', 'sim', '-s', '-r', '-v', verbosidad, str(mundo)],
        additional_env={'LIBGL_ALWAYS_SOFTWARE': '1'} if software else {},
        name='gz_servidor', output='screen')
    gui = ExecuteProcess(
        cmd=['gz', 'sim', '-g', '--render-engine', LaunchConfiguration('motor_gui'), '-v', verbosidad],
        name='gz_gui', output='screen', condition=IfCondition(LaunchConfiguration('gui')))
    return [
        LogInfo(msg=f'Gene Haas: {mundo} | servidor con render por software: {software}'),
        AppendEnvironmentVariable('GZ_SIM_RESOURCE_PATH', str(escenario / 'modelos')),
        servidor, gui,
        RegisterEventHandler(OnProcessExit(target_action=servidor, on_exit=[EmitEvent(event=Shutdown(reason='servidor de Gazebo cerrado'))])),
    ]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('escenario', default_value=buscar_escenario(),
                              description='Carpeta del proyecto que contiene mundo/ y modelos/'),
        DeclareLaunchArgument('gui', default_value='true', choices=['true', 'false'], description='Abrir la ventana de Gazebo'),
        DeclareLaunchArgument('servidor_software', default_value='true', choices=['true', 'false'],
                              description='Servidor con LIBGL_ALWAYS_SOFTWARE=1 (necesario para el LiDAR en esta VM)'),
        DeclareLaunchArgument('motor_gui', default_value='ogre', choices=['ogre', 'ogre2'], description='Motor de render de la GUI'),
        DeclareLaunchArgument('verbosidad', default_value='2', description='Verbosidad de gz sim (0-4)'),
        OpaqueFunction(function=lanzar),
    ])
