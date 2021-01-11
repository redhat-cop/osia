#!/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 Osia authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
    version="0.2.0-alpha2",
    description="OpenShift infra automation",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://redhat-cop.github.io/osia/",
    author="Miroslav Jaros",
    author_email="mirek@mijaros.cz",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    keywords="OpenShift OpenStack AWS automation",  # Optional
    packages=find_packages(exclude=["contrib", "docs", "tests"]),
    package_data={"": ["*.jinja2"]},
    entry_points={"console_scripts": ["osia = osia.cli:main_cli"]},
    include_package_data=True,
    python_requires=">=3.6",
    install_requires=[
        "appdirs==1.4.4",
        "beautifulsoup4==4.9.3",
        "boto3==1.16.50",
        "botocore==1.19.50",
        "certifi==2020.12.5",
        "cffi==1.14.4",
        "chardet==4.0.0; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3, 3.4'",
        "coloredlogs==15.0",
        "cryptography==3.3.1; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3, 3.4, 3.5'",
        "decorator==4.4.2",
        "dogpile.cache==1.1.1; python_version >= '3.6'",
        "dynaconf[yaml]==3.1.2",
        "gitdb==4.0.5; python_version >= '3.4'",
        "gitpython==3.1.12",
        "humanfriendly==9.1; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3, 3.4'",
        "idna==2.10; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3'",
        "iso8601==0.1.13",
        "jinja2==2.11.2",
        "jmespath==0.10.0; python_version >= '2.6' and python_version not in '3.0, 3.1, 3.2, 3.3'",
        "jsonpatch==1.28; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3, 3.4'",
        "jsonpointer==2.0; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3'",
        "keystoneauth1==4.3.0; python_version >= '3.6'",
        "markupsafe==1.1.1; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3'",
        "munch==2.5.0",
        "netifaces==0.10.9",
        "openstacksdk==0.52.0",
        "os-service-types==1.7.0",
        "pbr==5.5.1; python_version >= '2.6'",
        "pycparser==2.20; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3'",
        "python-dateutil==2.8.1; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3'",
        "pyyaml==5.3.1",
        "requests==2.25.1; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3, 3.4'",
        "requestsexceptions==1.4.0",
        "ruamel.yaml==0.16.12",
        "s3transfer==0.3.3",
        "six==1.15.0; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3'",
        "smmap==3.0.4; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3'",
        "soupsieve==2.1; python_version >= '3.0'",
        "stevedore==3.3.0; python_version >= '3.6'",
        "urllib3==1.26.2; python_version != '3.4'",
    ],
    extras_require={"dev": []},
    dependency_links=[],
    project_urls={
        "Bug Reports": "https://github.com/redhat-cop/osia/issues",
        "Source": "https://github.com/redhat-cop/osia",
    },
)
