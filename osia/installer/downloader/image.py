"""Module implements logic for rhcos image download"""
from __future__ import annotations

import gzip
import json
import logging
import re
import subprocess
from pathlib import Path
from shutil import copyfileobj
from subprocess import PIPE, Popen
from tempfile import _TemporaryFileWrapper

import requests

from .utils import get_data

GITHUB_URL = "https://raw.githubusercontent.com/openshift/installer/{commit}/data/data/rhcos.json"


class CoreOsException(Exception):
    """CoreOsException represents error while executing installer in older version
    """
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, *kwargs)


def _get_coreos_json(installer: str) -> tuple[str, str]:
    json_data = {}
    with Popen([installer, "coreos", "print-stream-json"], stdout=PIPE,
               stderr=subprocess.DEVNULL, universal_newlines=True) as proc:
        proc.wait()
        if proc.returncode != 0:
            raise CoreOsException("Installer doesn't support coreos subcommand")
        if proc.stdout is None:
            raise CoreOsException("Installer didn't output any data")
        json_data = json.loads(proc.stdout.read())
    json_part = json_data["architectures"]["x86_64"]["artifacts"]["openstack"]
    release_str = json_part["release"]
    json_part = json_part["formats"]["qcow2.gz"]
    return json_part.get("disk", json_part)["location"], release_str


def get_commit(installer: str) -> tuple[str, str]:
    """Function extracts source commit from installer,
    in order to find associated rhcos image"""
    version_str = ""
    commit_regex = re.compile(r"^.*commit (?P<commit>\w*)$", re.MULTILINE)
    with Popen([installer, "version"], stdout=PIPE, universal_newlines=True) as proc:
        if proc.stdout is None:
            raise OSError("Could not get installer version")
        version_str = proc.stdout.read()
    commits = commit_regex.findall(version_str)
    logging.info("Found commits by running installer %s", commits)
    return commits[0]


def _get_old_url(installer: str) -> tuple[str, str]:
    commit = get_commit(installer)
    gh_data_link = GITHUB_URL.format(commit=commit)
    rhcos_json = requests.get(gh_data_link, allow_redirects=True)
    rhcos_data = json.loads(rhcos_json.content)
    return rhcos_data['baseURI'] + rhcos_data['images']['openstack']['path'], rhcos_data['buildid']


def get_url(installer: str) -> tuple[str, str]:
    """Function builds url to rhcos image and version of
    rhcos iamge."""
    url, version = None, None
    try:
        url, version = _get_coreos_json(installer)
    except CoreOsException as ex:
        logging.debug(ex)
        url, version = _get_old_url(installer)
    return url, version


def _extract_gzip(buff: _TemporaryFileWrapper[bytes], target: str) -> Path:
    result = None
    with gzip.open(buff.name) as zip_file:
        result = Path(target)
        with result.open("wb") as output:
            copyfileobj(zip_file, output)
    return result


def download_image(image_url: str, image_file: str):
    """Main entrypoint for image download, function
    extracts url to rhcos image, downloads and extracts it
    to specified target"""
    directory = Path(image_file).parent
    # Check if the directory exists
    if not directory.exists():
        # If the directory does not exist, create it
        directory.mkdir(parents=True)
        logging.debug("Creating %s directory for download images", directory)
    else:
        logging.debug("Directory %s for images already exists", directory)
    res_file = get_data(image_url, image_file, _extract_gzip)
    return res_file


def download_rhcos_image(images_dir: str, url: str, version: str) -> str:
    """ Download rhcos image """
    image_path = Path(images_dir).joinpath(f"rhcos-{version}.qcow2")
    image_file = None
    if image_path.exists():
        logging.info("Found image at %s", image_path.name)
        image_file = image_path.as_posix()
        return image_file

    logging.info("Starting download of image %s", url)
    image_file = download_image(url, image_path.as_posix())

    return image_path.as_posix()
