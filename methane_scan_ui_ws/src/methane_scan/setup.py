from setuptools import find_packages, setup

package_name = 'methane_scan'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/launch.py']),
    ],
    install_requires=['setuptools', 'PyQtWebEngine', 'python-dotenv'],
    include_package_data=True, 
    package_data={
        'methane_scan': [
            'resources/*',
            'qresources_rc.py',
            '.env',
            'views/*.qss',
            'views/pages/*.qss',
            'views/web/*'
        ]
    },
    zip_safe=True,
    maintainer='aromsan',
    maintainer_email='alerosan16@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
    	'console_scripts': [
        	'methane_scan_node = methane_scan.methane_scan_node:main',
        	'mqtt_ros_bridge_node = methane_scan.mqtt_ros_bridge_node:main',
    	],
   },
)
