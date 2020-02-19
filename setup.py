#!/bin/env python3
"""A setuptools based setup module.
See:
https://packaging.python.org/guides/distributing-packages-using-setuptools/
https://github.com/pypa/sampleproject
Modified by Madoshakalaka@Github (dependency links added)
"""

from setuptools import setup, find_packages
from os import path
from io import open


here = path.abspath(path.dirname(__file__))

with open(path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="osia",
    version="0.1.4",
    description="OpenShift infra automation",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="fixme",
    author="Miroslav Jaros",
    author_email="mirek@mijaros.cz",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: Apache License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
    ],
    keywords="OpenShift OpenStack AWS automation",  # Optional
    packages=find_packages(exclude=["contrib", "docs", "tests"]),
    package_data={"": ["*.jinja2"]},
    entry_points={"console_scripts": ["osia = osia.cli:main_cli"]},
    include_package_data=True,
    python_requires=">=3.6",
    install_requires=[
        "appdirs==1.4.3",
        "beautifulsoup4==4.8.2",
        "boto3==1.12.2",
        "botocore==1.15.2",
        "certifi==2019.11.28",
        "cffi==1.14.0",
        "chardet==3.0.4",
        "click==7.0",
        "coloredlogs==14.0",
        "cryptography==2.8",
        "decorator==4.4.1",
        "docutils==0.15.2",
        "dogpile.cache==0.9.0",
        "dynaconf==2.2.2",
        "gitdb2==3.0.2",
        "gitpython==3.0.8",
        "humanfriendly==7.1.1",
        "idna==2.8",
        "iso8601==0.1.12",
        "jinja2==2.11.1",
        "jmespath==0.9.4",
        "jsonpatch==1.25",
        "jsonpointer==2.0",
        "keystoneauth1==3.18.0",
        "markupsafe==1.1.1",
        "munch==2.5.0",
        "netifaces==0.10.9",
        "openstacksdk==0.41.0",
        "os-service-types==1.7.0",
        "pbr==5.4.4",
        "pycparser==2.19",
        "python-box==3.4.6",
        "python-dateutil==2.8.1",
        "python-dotenv==0.10.3",
        "pyyaml==5.3",
        "requests==2.22.0",
        "requestsexceptions==1.4.0",
        "s3transfer==0.3.3",
        "six==1.14.0",
        "smmap2==2.0.5",
        "soupsieve==1.9.5",
        "stevedore==1.32.0",
        "toml==0.10.0",
        "urllib3==1.25.8; python_version != '3.4'",
    ],
    extras_require={"dev": []},
    dependency_links=[],
    project_urls={
        "Bug Reports": "https://github.com/redhat-cop/osia/issues",
        "Source": "https://github.com/redhat-cop/osia",
    },
)
