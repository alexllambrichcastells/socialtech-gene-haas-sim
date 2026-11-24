"""Arranque completo: escenario Gene Haas + Tracer2 + puente ROS-Gazebo (+ RViz2 opcional).

    ros2 launch gene_haas_bringup gene_haas_tracer2.launch.py
    ros2 launch gene_haas_bringup gene_haas_tracer2.launch.py rviz:=true
    ros2 launch gene_haas_bringup gene_haas_tracer2.launch.py gui:=false        # sin ventana (pruebas)
    ros2 launch gene_haas_bringup gene_haas_tracer2.launch.py x:=-4.0 y:=-0.2 yaw:=0.0   # otra pose inicial (p. ej. la de validar_capa1.py)

Pose inicial por defecto (aproximada): (5.6, 0.85), yaw pi, en la sala de células mirando a la puerta del tabique.

Teleoperación por teclado, en OTRA terminal (necesita una consola interactiva, por eso no va dentro del launch):
    ros2 run teleop_twist_keyboard teleop_twist_keyboard

Sin navegación autónoma: ni mapa, ni localización, ni Nav2 (capas posteriores).
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    lanzadores = PathJoinSubstitution([FindPackageShare('gene_haas_bringup'), 'launch'])
    mundo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(PathJoinSubstitution([lanzadores, 'gene_haas_mundo.launch.py'])),
        launch_arguments={'gui': LaunchConfiguration('gui'),
                          'servidor_software': LaunchConfiguration('servidor_software')}.items())
    robot = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(PathJoinSubstitution([lanzadores, 'tracer2_spawn.launch.py'])),
        launch_arguments={'x': LaunchConfiguration('x'), 'y': LaunchConfiguration('y'), 'yaw': LaunchConfiguration('yaw'),
                          'lidar_hz': LaunchConfiguration('lidar_hz')}.items())
    rviz = Node(package='rviz2', executable='rviz2', name='rviz2', output='screen',
                arguments=['-d', PathJoinSubstitution([FindPackageShare('tracer2_description'), 'rviz', 'tracer2.rviz'])],
                parameters=[{'use_sim_time': True}], condition=IfCondition(LaunchConfiguration('rviz')))

    return LaunchDescription([
        DeclareLaunchArgument('gui', default_value='true', choices=['true', 'false'], description='Ventana de Gazebo (con GPU)'),
        DeclareLaunchArgument('servidor_software', default_value='true', choices=['true', 'false'],
                              description='Servidor con LIBGL_ALWAYS_SOFTWARE=1 (necesario para el LiDAR en esta VM)'),
        DeclareLaunchArgument('rviz', default_value='false', choices=['true', 'false'], description='RViz2 con modelo, TF, /scan y /odom'),
        # Pose inicial por defecto (APROXIMADA): sala de células, en el paso de 1.74 m entre el bloque de mesas de entrada y la
        # pared sur, ~1.4 m antes de la abertura del tabique y alineado con ella, mirando al oeste (al avanzar va hacia la sala de
        # máquinas). Márgenes: 0.27 m a las mesas, 0.90 m a la pared sur, 0.32 m a la punta de la hoja abierta de la puerta.
        DeclareLaunchArgument('x', default_value='5.6', description='Pose inicial x (m); por defecto: sala de células, antes de la puerta'),
        DeclareLaunchArgument('y', default_value='0.85', description='Pose inicial y (m)'),
        DeclareLaunchArgument('yaw', default_value='3.14159', description='Pose inicial yaw (rad); por defecto mirando a la puerta (oeste)'),
        DeclareLaunchArgument('lidar_hz', default_value='10', description='Frecuencia del LiDAR (Hz); 40 en el Tracer2 original'),
        mundo,
        # Esperar a que el servidor cree el mundo antes de insertar el robot (create reintenta, pero así el log es limpio).
        TimerAction(period=5.0, actions=[robot, rviz]),
    ])
