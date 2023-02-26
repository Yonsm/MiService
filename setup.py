#!/usr/bin/env python3

import os
import sys

if len(sys.argv) == 1:
    os.system("%s sdist" % sys.argv[0])
    os.system("twine upload dist/*")
    os.system("rm -rf dist *.egg-info")
    exit(0)


from setuptools import setup

from miservice import MISERVICE_VERSION

setup(
    name="miservice",
    description="XiaoMi Cloud Service",
    version=MISERVICE_VERSION,
    license="MIT",
    author="Yonsm, yihong0618",
    author_email="Yonsm@qq.com, zouzou0208@gmail.com",
    url="https://github.com/yihong0618/MiService",
    packages=["miservice"],
    scripts=["micli.py"],
    python_requires=">=3.7",
    install_requires=["aiohttp"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    entry_points={
        "console_scripts": ["micli = miservice.cli:micli"],
    },
)
