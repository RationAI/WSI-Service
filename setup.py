import re

from setuptools import setup, find_packages


# load requirements
with open('requirements.txt') as f:
    install_requires = f.read().splitlines()
install_requires = [i.split('==')[0] for i in install_requires] # remove specific version

# load version
versionfile = open('wsi_service/version.py', "rt").read()
version_mo = re.search(r'^__version__ = [\'"]([^\'"]*)[\'"]', versionfile, re.M)
if version_mo:
    version = version_mo.group(1)
else:
    raise RuntimeError('Unable to find version in version file.')

setup (
    name='wsi_service',
    version=version,
    long_description=__doc__,
    packages=find_packages(),
    zip_safe=False,
    install_requires=install_requires
)
