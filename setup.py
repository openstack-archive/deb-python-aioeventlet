# Release procedure:
#  - (fill changelog, FIXME: no changelog yet)
#  - (run unit tests, FIXME: no test yet)
#  - update the version in setup.py to X.Y
#  - (set release date in the changelog, FIXME: no changelog yet)
#  - check that "python setup.py sdist" contains all files tracked by
#    the SCM (Mercurial), or update MANIFEST.in
#  - hg ci
#  - hg tag X.Y
#  - hg push
#  - python setup.py sdist bdist_wheel register upload
#  - increment version in setup.py
#  - hg ci && hg push

import os
import sys
try:
    from setuptools import setup, Extension
    SETUPTOOLS = True
except ImportError:
    SETUPTOOLS = False
    # Use distutils.core as a fallback.
    # We won't be able to build the Wheel file on Windows.
    from distutils.core import setup, Extension

requirements = ['eventlet']
if sys.version_info >= (3, 4):
    # Python 3.4 and newer: asyncio is now part of the stdlib
    pass
elif (3, 3) <= sys.version_info < (3, 4):
    # Python 3.3: use Tulip
    requirements.append('asyncio>=0.4.1')
else:
    # Python 2.6-3.2: use Trollius
    requirements.append('trollius>=1.0')

with open("README") as fp:
    long_description = fp.read()

install_options = {
    "name": "aiogreen",
    "version": "0.1",
    "license": "Apache License 2.0",
    "author": 'Victor Stinner',
    "author_email": 'victor.stinner@gmail.com',

    "description": "asyncio event loop scheduling callbacks in eventlet.",
    "long_description": long_description,
    "url": "https://bitbucket.org/haypo/aiogreen/",

    "classifiers": [
        "Programming Language :: Python",
        #"Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
    ],

    "py_modules": ["aiogreen"],
    #"test_suite": "runtests.runtests",
}
if SETUPTOOLS:
    install_options['install_requires'] = requirements

setup(**install_options)
