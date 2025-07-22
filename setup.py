#!/usr/bin/env python

from setuptools import setup, find_packages

readme = open("README.md").read()

setup(
    name="pats_bot",
    description="todo",
    author="Your Name",
    author_email="tbd@gmail.com",
    url="https://github.com/YourUser/PatsBot",
    packages=find_packages(include=["PatsBot"]),
    package_dir={"PatsBot": "PatsBot"},
    entry_points={
        "console_scripts": [
            "pats-bot=PatsBot.__main__:main",
        ],
    },
    python_requires=">=3.10.0",
    version="0.0.0",
    long_description=readme,
    include_package_data=True,
    install_requires=[
        "discord.py",
    ],
    license="MIT",
)
