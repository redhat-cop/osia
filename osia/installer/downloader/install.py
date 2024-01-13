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
"""Module responsible for download of openshift-install binary"""
from shutil import copyfileobj
from tempfile import NamedTemporaryFile
from pathlib import Path
from typing import Tuple, Optional
import platform

import logging
import re
import stat
import tarfile
import time
import requests

from bs4 import BeautifulSoup
from .utils import get_data


PROD_ROOT = "http://mirror.openshift.com/pub/openshift-v4/{}/clients/ocp/"
BUILD_ROOT = "https://openshift-release-artifacts.svc.ci.openshift.org/"
PREVIEW_ROOT = "http://mirror.openshift.com/pub/openshift-v4/{}/clients/ocp-dev-preview/"

VERSION_RE = re.compile(r"^openshift-install-(?P<platform>\w+)"
                        r"(-(?P<architecture>\w+))?-(?P<version>\d+.*)\.tar\.gz")
EXTRACTION_RE = re.compile(r'.*Extracting tools for .*, may take up to a minute.*')


def _current_platform():
    if platform.system() == "Linux" and platform.machine() == "x86_64":
        return "linux", "amd64"
    if platform.system() == "Linux" and platform.machine() == "arm64":
        return "linux", "arm64"
    if platform.system() == "Darwin" and platform.machine() == "arm64":
        return "mac", "arm64"
    if platform.system() == "Darwin" and platform.machine() == "x86_64":
        return "mac", "amd64"
    raise Exception(f"Unrecognized platform {platform.system()} {platform.machine()}")


def get_url(directory: str, arch: str) -> Tuple[Optional[str], Optional[str]]:
    """Searches the http directory and returns both url to installer
    and version.
    """
    lst = requests.get(directory, allow_redirects=True)
    tree = BeautifulSoup(lst.content, 'html.parser')
    links = tree.find_all('a')
    installer, version = None, None
    os_name, local_arch = _current_platform()
    for k in links:
        match = VERSION_RE.match(k.get('href'))
        if match and match.group('platform') == os_name:
            if (local_arch == match.group('architecture')) \
                    or (local_arch == arch and not match.group('architecture')):
                installer = lst.url + k.get('href')
                version = match.group('version')
                break
    return installer, version


def get_devel_url(version: str, arch: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Searches developement sources and returns url to installer
    """
    req = requests.get(BUILD_ROOT + version, allow_redirects=True)
    ast = BeautifulSoup(req.content, 'html.parser')
    logging.info('Checking stage repository for installer')
    while len(ast.find_all('p')) != 0 and EXTRACTION_RE.match(next(ast.find_all('p')[0].children)):
        logging.debug('The installer was not extracted yet, waiting for 10s')
        time.sleep(10)
        req = requests.get(BUILD_ROOT + version, allow_redirects=True)
        ast = BeautifulSoup(req.content, 'html.parser')
    logging.debug('Installer found on page, continuing')
    return get_url(req.url, arch)


def get_prev_url(version: str, arch: str) -> Tuple[Optional[str], Optional[str]]:
    """Returns installer url from dev-preview sources"""
    return get_url(PREVIEW_ROOT.format(arch) + version, arch)


def get_prod_url(version: str, arch: str) -> Tuple[Optional[str], Optional[str]]:
    """Returns installer url from production sources"""
    return get_url(PROD_ROOT.format(arch) + version, arch)


def _get_storage_path(version: str, install_base: str) -> str:
    path = Path(install_base)
    spec_path = path.joinpath(version)
    if not spec_path.exists():
        spec_path.mkdir()
    return spec_path.as_posix()


def _extract_tar(buffer: NamedTemporaryFile, target: str) -> Path:
    result = None
    with tarfile.open(buffer.name) as tar:
        inst_info = None
        for i in tar.getmembers():
            if i.name == 'openshift-install':
                inst_info = i
        if inst_info is None:
            raise Exception("error")
        stream = tar.extractfile(inst_info)
        result = Path(target).joinpath('openshift-install')
        with result.open('wb') as output:
            copyfileobj(stream, output)
        result.chmod(result.stat().st_mode | stat.S_IXUSR)
    return result


def get_installer(tar_url: str, target: str):
    """Download and extract the installer into the target"""
    return get_data(tar_url, target, _extract_tar)


def download_installer(installer_version: str,
                       installer_arch: str,
                       dest_directory: str,
                       source: str) -> str:
    """Starts search and extraction of installer"""
    logging.debug("Getting version %s of %s, storing to directory %s and devel is %r",
                  installer_version, installer_arch, dest_directory, source)

    downloader = None
    if source == "prod":
        downloader = get_prod_url
    elif source == "prev":
        downloader = get_prev_url
    elif source == "devel":
        downloader = get_devel_url
    else:
        raise Exception("Error for source profile " + source)

    url, version = downloader(installer_version, installer_arch)
    root = Path(dest_directory).joinpath(version)

    if root.exists() and root.joinpath('openshift-install').exists():
        logging.info('Found installer at %s', root.as_posix())
        return root.joinpath('openshift-install').as_posix()
    root.mkdir(parents=True)
    return get_installer(url, root.as_posix())
