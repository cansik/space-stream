import distutils
import platform
import sys
import zipfile
from pathlib import Path
from typing import Union

from setuptools import setup, find_packages

NAME = "space-stream"
MODULE_NAME = "spacestream"

required_packages = find_packages()

with open("requirements.txt") as f:
    required = f.read().splitlines()

# read readme
current_dir = Path(__file__).parent
long_description = (current_dir / "README.md").read_text()


def zip_dir(dir: Union[Path, str], filename: Union[Path, str]):
    """Zip the provided directory without navigating to that directory using `pathlib` module"""

    # Convert to Path object
    dir = Path(dir)

    with zipfile.ZipFile(filename, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for entry in dir.rglob("*"):
            zip_file.write(entry, entry.relative_to(dir))


class Distribution(distutils.cmd.Command):
    description = "Distribute with pyinstaller"
    user_options = [
        ("zip", None, "Create a zip package"),
        ("macos-universal2", None, "Create MacOS universal2 package")
    ]

    def run(self) -> None:
        import PyInstaller.__main__

        # fix open3d resources folder
        import open3d
        o3d_root = Path(open3d.__file__).parent
        o3d_resources_src = o3d_root.joinpath("resources")
        o3d_resources_dest = "open3d/resources"

        # create arguments
        delimiter = ";" if sys.platform.startswith("win") else ":"
        arguments = [
            f"{MODULE_NAME}/__main__.py",
            "--name", NAME,
            "--add-data", f"{o3d_resources_src}{delimiter}{o3d_resources_dest}",
            "--clean",
            "-y"
        ]

        system_name = sys.platform
        system_arch = platform.machine()

        # correct system name
        if system_name.startswith("linux"):
            system_name = "linux"
        elif system_name.startswith("darwin"):
            system_name = "macosx"
        elif system_name.startswith("win"):
            system_name = "windows"

        if sys.platform == "darwin" and self.macos_universal2:
            print("building universal binary")
            arguments.append("--target-arch")
            arguments.append("universal2")

        PyInstaller.__main__.run(arguments)

        if self.zip:
            print("creating zip file...")
            build_system_info = f"{system_name}-{system_arch}".lower()
            zip_dir(f"dist/{NAME}", f"dist/{NAME}-{build_system_info}.zip")

    def initialize_options(self) -> None:
        self.zip = False
        self.macos_universal2 = False

    def finalize_options(self) -> None:
        pass


setup(
    name=NAME,
    version='0.1.7',
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
    cmdclass={
        "distribute": Distribution,
    },
)
