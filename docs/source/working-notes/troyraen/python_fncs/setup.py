#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""A module for Pitt-Google Broker utilities.

Example setup.py: https://github.com/pypa/sampleproject/blob/main/setup.py

This file is part of the pgb_utils software package.

The pgb_utils package is free software: you can redistribute it and/or
modify it under the terms of the GNU General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

The pgb_utils package is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
Public License for more details.

You should have received a copy of the GNU General Public License
along with pgb_utils.  If not, see <http://www.gnu.org/licenses/>.
"""

from setuptools import setup, find_packages
import pathlib


# here = pathlib.Path(__file__).parent.resolve()
# long_description = (here / 'README.md').read_text(encoding='utf-8')

# with open('requirements.txt') as f:
#     requirements = f.read().splitlines()

setup(
    name="troys_python_fncs",  # Required
    version="0.1.0",  # Required
    description="Tools to interact with Pitt-Google Broker data products and services.",
    # long_description=long_description,
    # long_description_content_type='text/markdown',
    url="https://github.com/mwvgroup/Pitt-Google-Broker/troy",
    author="Troy Raen",
    author_email="troy.raen@pitt.edu",
    packages=find_packages(),  # Required
    # install_requires=requirements,
    # https://setuptools.readthedocs.io/en/latest/userguide/dependency_management.html#optional-dependencies
    # extras_require={
    #         "beam":  ["apache_beam[gcp]"],
    #     },
    # python_requires='>=3.6, <4',
    # If there are data files included in your packages that need to be
    # installed, specify them here.
    # package_data={  # Optional
    #     'sample': ['package_data.dat'],
    # },
)
