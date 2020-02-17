from shutil import copyfileobj
from sys import platform
from tempfile import NamedTemporaryFile
from pathlib import Path

import logging
import re
import stat
import tarfile
import time
import requests

from bs4 import BeautifulSoup


PROD_ROOT = "http://mirror.openshift.com/pub/openshift-v4/clients/ocp/"
BUILD_ROOT = "https://openshift-release-artifacts.svc.ci.openshift.org/"
VERSION_RE = re.compile(r"^openshift-install-(?P<platform>\w+)-(?P<version>.*)\.tar\.gz")
EXTRACTION_RE = re.compile(r'.*Extracting tools for .*, may take up to a minute.*')


def _current_platform():
    if platform == "linux":
        return platform
    elif platform == "darwin":
        return "mac"
    raise Exception(f"Unrecognized platform {platform}")


def get_url(directory):
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


def get_devel_url(version):
    req = requests.get(BUILD_ROOT + version, allow_redirects=True)
    sp = BeautifulSoup(req.content, 'html.parser')
    logging.info('Checking stage repository for installer')
    while len(sp.find_all('p')) != 0 and EXTRACTION_RE.match(next(sp.find_all('p')[0].children)):
        logging.debug('The installer was not extracted yet, waiting for 10s')
        time.sleep(10)
        req = requests.get(BUILD_ROOT + version, allow_redirects=True)
        sp = BeautifulSoup(req.content, 'html.parser')
    logging.debug('Installer found on page, continuing')
    return get_url(req.url)


def get_prod_url(version):
    return get_url(PROD_ROOT + version)


def _get_storage_path(version, install_base):
    path = Path(install_base)
    spec_path = path.joinpath(version)
    if not spec_path.exists():
        spec_path.mkdir()
    return spec_path.as_posix()


def _extract_tar(buffer: NamedTemporaryFile, target: str, ):
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

    logging.info(f'Installer extracted to %s', result.as_posix())
    return result.as_posix()


def download_installer(installer_version: str, dest_directory: str, devel: bool):
    logging.debug("Getting version %s, storing to directory %s and devel is %r",
                  installer_version, dest_directory, devel)

    downloader = get_prod_url
    if devel:
        downloader = get_devel_url
    url, version = downloader(installer_version)
    root = Path(dest_directory).joinpath(version)

    if root.exists() and root.joinpath('openshift-install').exists():
        logging.info('Found installer at %s', root.as_posix())
        return root.joinpath('openshift-install').as_posix()
    root.mkdir()
    return get_installer(url, root.as_posix())
