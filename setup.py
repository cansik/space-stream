from pathlib import Path

from setuptools import setup, find_packages

NAME = 'space-stream'

required_packages = find_packages()

with open('requirements.txt') as f:
    required = f.read().splitlines()

# read readme
current_dir = Path(__file__).parent
long_description = (current_dir / "README.md").read_text()

setup(
    name=NAME,
    version='0.1.4',
    packages=required_packages,
    entry_points={
        'console_scripts': [
            'space-stream = spacestream.__main__:main',
        ],
    },
    url='https://github.com/cansik/space-stream',
    license='MIT License',
    author='Florian Bruggisser',
    author_email='github@broox.ch',
    description='Send RGB-D images over spout / syphon with visiongraph.',
    long_description=long_description,
    long_description_content_type="text/markdown",
    install_requires=required,
)
