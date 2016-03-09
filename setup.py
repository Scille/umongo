#!/usr/bin/env python
# -*- coding: utf-8 -*-


try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = [
    "marshmallow>=2.6.0",
    "pymongo>=3.2.0"  # needed for bson module
]

test_requirements = [
    "txmongo",
    "motor>=0.6.0"
]

setup(
    name='umongo',
    version='0.2.2',
    description="Small but efficient MongoDB ODM",
    long_description=readme + '\n\n' + history,
    author="Emmanuel Leblond",
    author_email='emmanuel.leblond@gmail.com',
    url='https://github.com/touilleMan/umongo',
    packages=[
        'umongo'
    ],
    package_dir={'umongo': 'umongo'},
    include_package_data=True,
    install_requires=requirements,
    license="ISCL",
    zip_safe=False,
    keywords='umongo',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
    test_suite='tests',
    tests_require=test_requirements
)