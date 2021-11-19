#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

from setuptools import find_packages, setup

include = [
    'transforms',
    'transforms.*',
]

requires = [
    'apache_beam[gcp]',
    'argparse',
    'astropy',
    # 'base64', builtin
    'fastavro',
    'google-cloud-core>=1.4.1',
    'google-cloud-dataflow',
    'google-cloud-datastore>=1.15',
    'google-cloud-logging',
    'google-cloud-storage==1.38.0',
    'iminuit==1.4.9',
    # 'io', builtin
    # 'json', builtin
    'matplotlib',
    'numpy',
    'pandas',
    'pgb-broker-utils',
    'sncosmo==2.2.0',
    # 'tempfile', builtin
    'workflow',
]

setup(
    name='value_added',
    version='0.0.1',
    url='https://github.com/mwvgroup/Pitt-Google-Broker',
    author='Troy Raen',
    author_email='troy.raen@pitt.edu',
    install_requires=requires,
    packages=find_packages(include=include),
)
