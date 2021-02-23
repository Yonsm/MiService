#!/usr/bin/env python

from setuptools import setup

setup(
    name='miservice',
    version='1.0.0',
    author='Yonsm',
    author_email='Yonsm@qq.com',
    url='https://github.com/Yonsm/MiService',
    description='XiaoMi Service API for mi.com',
    packages=['miservice'],
    scripts=['miservice.py'],
	python_requires='>=3.6',
    install_requires=['aiohttp'],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
