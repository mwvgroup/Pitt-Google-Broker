# !/usr/bin/env python3
# -*- coding: UTF-8 -*-

from setuptools import find_packages, setup

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(name='pitt_broker',
      version='0.0.2',
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
