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
]

test_requirements = [
    "txmongo",
    "motor>=0.6.2"
]

setup(
    name='umongo',
    version='0.7.4',
    description="Small but efficient MongoDB ODM",
    long_description=readme + '\n\n' + history,
    author="Emmanuel Leblond",
    author_email='emmanuel.leblond@gmail.com',
    url='https://github.com/touilleMan/umongo',
    packages=['umongo', 'umongo.dal'],
    include_package_data=True,
    install_requires=requirements,
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
    test_suite='tests',
    tests_require=test_requirements
)
