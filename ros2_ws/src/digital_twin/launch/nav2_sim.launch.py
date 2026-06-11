"""
Custom Nav2 launch for TurtleBot3 Gazebo simulation (ROS2 Jazzy).

Excludes: route_server, docking_server (Jazzy-new, not in burger.yaml)
          velocity_smoother, collision_monitor (these create feedback loops
          or false-stop behavior in Gazebo simulation)

controller_server outputs TwistStamped directly to /cmd_vel.
The TurtleBot3 Jazzy ros_gz_bridge expects TwistStamped on /cmd_vel.
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, SetParameter
from launch_ros.descriptions import ParameterFile
from nav2_common.launch import RewrittenYaml


LIFECYCLE_NODES = [
    'controller_server',
    'smoother_server',
    'planner_server',
    'behavior_server',
    'bt_navigator',
    'waypoint_follower',
]


def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time')
    params_file  = LaunchConfiguration('params_file')
    autostart    = LaunchConfiguration('autostart')

    default_params = os.path.join(
        get_package_share_directory('digital_twin'),
        'burger_sim.yaml',
    )

    configured_params = ParameterFile(
        RewrittenYaml(
            source_file=params_file,
            root_key='',
            param_rewrites={'use_sim_time': use_sim_time, 'autostart': autostart},
            convert_types=True,
        ),
        allow_substs=True,
    )

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        DeclareLaunchArgument('params_file',  default_value=default_params),
        DeclareLaunchArgument('autostart',    default_value='true'),

        GroupAction([
            SetParameter('use_sim_time', use_sim_time),

            Node(package='nav2_controller',        executable='controller_server',  name='controller_server',  output='screen', parameters=[configured_params]),
            Node(package='nav2_smoother',          executable='smoother_server',    name='smoother_server',    output='screen', parameters=[configured_params]),
            Node(package='nav2_planner',           executable='planner_server',     name='planner_server',     output='screen', parameters=[configured_params]),
            Node(package='nav2_behaviors',         executable='behavior_server',    name='behavior_server',    output='screen', parameters=[configured_params]),
            Node(package='nav2_bt_navigator',      executable='bt_navigator',       name='bt_navigator',       output='screen', parameters=[configured_params]),
            Node(package='nav2_waypoint_follower', executable='waypoint_follower',  name='waypoint_follower',  output='screen', parameters=[configured_params]),

            Node(
                package='nav2_lifecycle_manager',
                executable='lifecycle_manager',
                name='lifecycle_manager_navigation',
                output='screen',
                parameters=[{'autostart': autostart, 'node_names': LIFECYCLE_NODES}],
            ),
        ]),
    ])
