from codecs import open
from os import path
from typing import List

from setuptools import find_packages, setup


def get_long_description() -> str:
    here = path.abspath(path.dirname(__file__))

    with open(path.join(here, "README.md"), encoding="utf-8") as f:
        long_description = f.read()
    return long_description


def get_requirements() -> List[str]:
    here = path.abspath(path.dirname(__file__))

    with open(path.join(here, "requirements.txt"), encoding="utf-8") as f:
        requirements = f.read().splitlines()
    return requirements


setup(
    name="ttimer",
    packages=find_packages(),
    version="0.0.1",
    license="MIT",
    install_requires=get_requirements(),
    author="nyanp",
    author_email="Noumi.Taiga@gmail.com",
    url="https://github.com/nyanp/ttimer",
    description="ttimer - tree timer",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    keywords="timer profiler",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
)
