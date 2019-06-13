# !/usr/bin/env python3
# -*- coding: UTF-8 -*-

import re
from pathlib import Path

from setuptools import find_packages, setup

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

# Get package version
init_path = Path(__file__).resolve().parent / 'broker/__init__.py'
with open(init_path, 'r') as f:
    source = f.read()

versionRegExp = re.compile("__version__ = '(.*?)'")
__version__ = versionRegExp.findall(source)[0]

setup(name='pitt_broker',
      version=__version__,
      packages=find_packages(),
      keywords='LSST ZTF broker',
      description='A cloud based data broker for LSST and ZTF',
      classifiers=[
          'Development Status :: 4 - Beta',
          'Intended Audience :: Science/Research',
          'Natural Language :: English',
          'Operating System :: OS Independent',
          'Programming Language :: Python :: 3.7',
          'Topic :: Scientific/Engineering :: Astronomy'
      ],

      python_requires='>=3.7',
      install_requires=requirements,
      include_package_data=False)
