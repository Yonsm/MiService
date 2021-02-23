#!/usr/bin/env python3

import os
import sys

if len(sys.argv) == 1:
    os.system('rm -rf dist/*')
    os.system('%s sdist' % sys.argv[0])
    os.system('twine upload dist/*')
    exit(0)


from pathlib import Path
from setuptools import setup

setup(
    name='miservice',
    version='1.0.2',
    author='Yonsm',
    author_email='Yonsm@qq.com',
    url='https://github.com/Yonsm/MiService',
    description='XiaoMi Cloud Service',
    long_description=Path('README.md').read_text(),
    long_description_content_type='text/markdown',
    packages=['miservice'],
    scripts=['micli.py'],
    python_requires='>=3.6',
    install_requires=['aiohttp'],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent"
    ]
)
