from setuptools import setup, find_packages
import os
from glob import glob

package_name = 'voice_asr_service'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='IB-Robot Team',
    maintainer_email='dev@example.com',
    description='Voice ASR Service for IB-Robot using sherpa-onnx',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'voice_asr_node = voice_asr_service.voice_asr_node:main',
        ],
    },
)