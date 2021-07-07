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
    "marshmallow>=3.10.0",
    "pymongo>=3.7.0",
]

setup(
    name='umongo',
    version='3.0.0',
    description="sync/async MongoDB ODM, yes.",
    long_description=readme + '\n\n' + history,
    author="Emmanuel Leblond, Jérôme Lafréchoux",
    author_email='jerome@jolimont.fr',
    url='https://github.com/touilleMan/umongo',
    packages=['umongo', 'umongo.frameworks'],
    include_package_data=True,
    package_data={
        'umongo': [
            "py.typed",
            "__init__.pyi",
            "abstract.pyi",
            "builder.pyi",
            "data_objects.pyi",
            "data_proxy.pyi",
            "document.pyi",
            "embedded_document.pyi",
            "exceptions.pyi",
            "expose_missing.pyi",
            "fields.pyi",
            "i18n.pyi",
            "indexes.pyi",
            "instance.pyi",
            "marshmallow_bonus.pyi",
            "mixin.pyi",
            "query_wrapper.pyi",
            "template.pyi",
            "validate.pyi",
            "frameworks/__init__.pyi",
            "frameworks/mongomock.pyi",
            "frameworks/motor_asyncio.pyi",
            "frameworks/pymongo.pyi",
            "frameworks/tools.pyi",
            "frameworks/txmongo.pyi",
        ]
    },
    python_requires='>=3.7',
    install_requires=requirements,
    extras_require={
        'motor': ['motor>=2.0,<3.0'],
        'txmongo': ['txmongo>=19.2.0'],
        'mongomock': ['mongomock'],
    },
    license="MIT",
    zip_safe=False,
    keywords='umongo mongodb pymongo txmongo motor mongomock asyncio twisted',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3 :: Only',
    ],
)
