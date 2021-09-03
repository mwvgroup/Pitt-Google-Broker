#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""A module for Pitt-Google Broker utilities.
Example setup.py: https://github.com/pypa/sampleproject/blob/main/setup.py

This file is part of the pgb_broker_utils software package.

The pgb_broker_utils package is free software: you can redistribute it and/or
modify it under the terms of the GNU General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

The pgb_broker_utils package is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
Public License for more details.

You should have received a copy of the GNU General Public License
along with pgb_broker_utils.  If not, see <http://www.gnu.org/licenses/>."""

from setuptools import setup, find_packages
import pathlib


here = pathlib.Path(__file__).parent.resolve()
# Get the long description from the README file
long_description = (here / 'README.md').read_text(encoding='utf-8')

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(
    name='pgb_broker_utils',  # Required
    version='0.2.10',  # Required
    description='Tools used by the Pitt-Google astronomical alert broker.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering :: Astronomy',
        'Topic :: Scientific/Engineering :: Physics',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3 :: Only',
    ],
    keywords='astronomy, alert broker',

    url='https://github.com/mwvgroup/Pitt-Google-Broker',
    author='Troy Raen',
    author_email='troy.raen@pitt.edu',

    packages=find_packages(),  # Required

    # For an analysis of "install_requires" vs pip's requirements files see:
    # https://packaging.python.org/en/latest/requirements.html
    install_requires=requirements

    # python_requires='>=3.6, <4',

    # If there are data files included in your packages that need to be
    # installed, specify them here.
    # package_data={  # Optional
    #     'sample': ['package_data.dat'],
    # },
)
