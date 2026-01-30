from pathlib import Path

from setuptools import find_packages, setup

with Path("README.md").open() as fh:
    long_desc = fh.read()

setup(
    name="girdermedviewer-plugin",
    version="1.0.0",
    description=("Girder plugin that exposes file path in assetstores"),
    long_description=long_desc,
    author="Justine Antoine",
    author_email="justine.antoine@kitware.com",
    license="Apache Software License 2.0",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "License :: OSI Approved :: Apache Software License",
        "Topic :: Scientific/Engineering",
        "Intended Audience :: Science/Research",
        "Natural Language :: English",
        "Programming Language :: Python",
    ],
    install_requires=[],
    entry_points={
        "girder.plugin": ["girdermedviewer_plugin = girdermedviewer_filemodel:MedViewerPlugin"],
    },
    packages=find_packages(),
)
