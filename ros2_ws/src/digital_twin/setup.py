from setuptools import find_packages, setup

package_name = 'digital_twin'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name, ['burger_sim.yaml']),
        ('share/' + package_name, ['burger_real.yaml']),
        ('share/' + package_name + '/launch', ['launch/nav2_sim.launch.py']),
        ('share/' + package_name + '/launch', ['launch/nav2_real.launch.py']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='inkyungil',
    maintainer_email='propose101@gmail.com',
    description='Frontier-based autonomous exploration node',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'frontier_explorer = digital_twin.frontier_explorer:main',
        ],
    },
)
