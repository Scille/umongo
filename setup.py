#!/usr/bin/env python
# -*- coding: utf-8 -*-


try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


with open('README.rst', 'rb') as readme_file:
    readme = readme_file.read().decode('utf8')

with open('HISTORY.rst', 'rb') as history_file:
    history = history_file.read().decode('utf8')

requirements = [
    "marshmallow>=2.6.0",
    "python-dateutil>=2.5.0"
]

setup(
    name='umongo',
    version='0.12.0',
    description="sync/async MongoDB ODM, yes.",
    long_description=readme + '\n\n' + history,
    author="Emmanuel Leblond",
    author_email='emmanuel.leblond@gmail.com',
    url='https://github.com/touilleMan/umongo',
    packages=['umongo', 'umongo.frameworks'],
    include_package_data=True,
    install_requires=requirements,
    extras_require={
        'pymongo': ['pymongo>=3.2.1'],
        'motor': ['motor >= 0.7, < 1.0'],
        'txmongo': ['txmongo>=16.0.1'],
        'mongomock': ['mongomock', 'pymongo']  # pymongo needed for bson module
    },
    license="MIT",
    zip_safe=False,
    keywords='umongo mongodb pymongo txmongo motor mongomock asyncio twisted',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
)
