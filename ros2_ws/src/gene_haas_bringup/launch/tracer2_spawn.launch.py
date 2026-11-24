"""Inserta el Tracer2 en un mundo de Gazebo ya en marcha y arranca su descripción y el puente ROS-Gazebo.

    ros2 launch gene_haas_bringup tracer2_spawn.launch.py
    ros2 launch gene_haas_bringup tracer2_spawn.launch.py x:=-4.0 y:=-0.2 yaw:=0.0 lidar_hz:=10

- robot_state_publisher publica /robot_description y las TF fijas y de las ruedas (a partir de /joint_states).
- ros_gz_sim create inserta el robot leyendo /robot_description (no se edita el mundo).
- ros_gz_bridge: /clock, /cmd_vel, /odom, /tf, /joint_states, /scan, /imu (config/puente_ros_gz.yaml).
Pose por defecto: pasillo principal de Gene Haas, mirando al este (+x).
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    xacro_robot = PathJoinSubstitution([FindPackageShare('tracer2_description'), 'urdf', 'tracer2.urdf.xacro'])
    puente = PathJoinSubstitution([FindPackageShare('gene_haas_bringup'), 'config', 'puente_ros_gz.yaml'])
    # Ruta entre comillas: Command separa la orden por espacios y las rutas con espacios llegaban a xacro partidas.
    descripcion = ParameterValue(
        Command([
            'xacro "', xacro_robot,
            '" lidar_hz:=', LaunchConfiguration('lidar_hz'),
        ]),
        value_type=str,
    )
    sim_time = {'use_sim_time': True}

    robot_state_publisher = Node(
        package='robot_state_publisher', executable='robot_state_publisher', name='robot_state_publisher', output='screen',
        parameters=[{'robot_description': descripcion}, sim_time])
    insertar = Node(
        package='ros_gz_sim', executable='create', name='insertar_tracer2', output='screen',
        arguments=['-world', LaunchConfiguration('mundo'), '-topic', 'robot_description', '-name', LaunchConfiguration('nombre'),
                   '-x', LaunchConfiguration('x'), '-y', LaunchConfiguration('y'), '-z', LaunchConfiguration('z'),
                   '-Y', LaunchConfiguration('yaw')])
    puente_ros_gz = Node(
        package='ros_gz_bridge', executable='parameter_bridge', name='puente_ros_gz', output='screen',
        parameters=[{'config_file': puente}, sim_time])

    return LaunchDescription([
        DeclareLaunchArgument('mundo', default_value='gene_haas', description='Nombre del mundo de Gazebo'),
        DeclareLaunchArgument('nombre', default_value='tracer2', description='Nombre del modelo en Gazebo'),
        DeclareLaunchArgument('x', default_value='-4.0'),
        DeclareLaunchArgument('y', default_value='-0.2'),
        DeclareLaunchArgument('z', default_value='0.02'),
        DeclareLaunchArgument('yaw', default_value='0.0'),
        DeclareLaunchArgument('lidar_hz', default_value='10', description='Frecuencia del LiDAR (Hz); 40 en el Tracer2 original'),
        robot_state_publisher, insertar, puente_ros_gz,
    ])
