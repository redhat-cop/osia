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
from sys import platform
from tempfile import NamedTemporaryFile
from pathlib import Path
from typing import Tuple, Optional

import logging
import re
import stat
import tarfile
import time
import requests

from bs4 import BeautifulSoup


PROD_ROOT = "http://mirror.openshift.com/pub/openshift-v4/clients/ocp/"
BUILD_ROOT = "https://openshift-release-artifacts.svc.ci.openshift.org/"
PREVIEW_ROOT = "http://mirror.openshift.com/pub/openshift-v4/clients/ocp-dev-preview/"

VERSION_RE = re.compile(r"^openshift-install-(?P<platform>\w+)-(?P<version>.*)\.tar\.gz")
EXTRACTION_RE = re.compile(r'.*Extracting tools for .*, may take up to a minute.*')


def _current_platform():
    if platform == "linux":
        return platform
    if platform == "darwin":
        return "mac"
    raise Exception(f"Unrecognized platform {platform}")


def get_url(directory: str) -> Tuple[Optional[str], Optional[str]]:
    """Searches the http directory and returns both url to installer
    and version.
    """
    lst = requests.get(directory, allow_redirects=True)
    tree = BeautifulSoup(lst.content, 'html.parser')
    links = tree.find_all('a')
    installer, version = None, None
    for k in links:
        match = VERSION_RE.match(k.get('href'))
        if match and match.group('platform') == _current_platform():
            installer = lst.url + k.get('href')
            version = match.group('version')
    return installer, version


def get_devel_url(version: str) -> str:
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
    return get_url(req.url)


def get_prev_url(version):
    """Returns installer url from dev-preview sources"""
    return get_url(PREVIEW_ROOT + version)


def get_prod_url(version):
    """Returns installer url from production sources"""
    return get_url(PROD_ROOT + version)


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


def get_installer(tar_url: str, target: str) -> str:
    """Download and extract the installer into the target"""
    result = None
    logging.info('Starting the download of installer')
    req = requests.get(tar_url, stream=True, allow_redirects=True)
    buf = NamedTemporaryFile()
    for block in req.iter_content(chunk_size=4096):
        buf.write(block)
    buf.flush()
    logging.debug('Download finished, starting extraction')
    result = _extract_tar(buf, target)
    buf.close()

    logging.info('Installer extracted to %s', result.as_posix())
    return result.as_posix()


def download_installer(installer_version: str, dest_directory: str, source: str) -> str:
    """Starts search and extraction of installer"""
    logging.debug("Getting version %s, storing to directory %s and devel is %r",
                  installer_version, dest_directory, source)

    downloader = None
    if source == "prod":
        downloader = get_prod_url
    elif source == "prev":
        downloader = get_prev_url
    elif source == "devel":
        downloader = get_devel_url
    else:
        raise Exception("Error for source profile " + source)

    url, version = downloader(installer_version)
    root = Path(dest_directory).joinpath(version)

    if root.exists() and root.joinpath('openshift-install').exists():
        logging.info('Found installer at %s', root.as_posix())
        return root.joinpath('openshift-install').as_posix()
    root.mkdir(parents=True)
    return get_installer(url, root.as_posix())
