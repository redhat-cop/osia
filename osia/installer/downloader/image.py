"""Module implements logic for rhcos image download"""
from subprocess import Popen, PIPE
from shutil import copyfileobj
from pathlib import Path
from typing import Tuple
from tempfile import NamedTemporaryFile

import gzip
import re
import logging
import json

import requests
from .utils import get_data

GITHUB_URL = "https://raw.githubusercontent.com/openshift/installer/{commit}/data/data/rhcos.json"


def get_commit(installer: str) -> str:
    """Function extracts source commit from installer,
    in order to find associated rhcos image"""
    version_str = ""
    commit_regex = re.compile(r"^.*commit (?P<commit>\w*)$", re.MULTILINE)
    with Popen([installer, "version"], stdout=PIPE, universal_newlines=True) as proc:
        version_str = proc.stdout.read()
    commits = commit_regex.findall(version_str)
    logging.info("Found commits by running installer %s", commits)
    return commits[0]


def get_url(installer: str) -> Tuple[str, str]:
    """Function builds url to rhcos image and version of
    rhcos iamge."""
    commit = get_commit(installer)
    gh_data_link = GITHUB_URL.format(commit=commit)
    rhcos_json = requests.get(gh_data_link, allow_redirects=True)
    rhcos_data = json.loads(rhcos_json.content)
    return rhcos_data['baseURI'] + rhcos_data['images']['openstack']['path'], rhcos_data['buildid']


def _extract_gzip(buff: NamedTemporaryFile, target: str) -> Path:
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
    res_file = get_data(image_url, image_file, _extract_gzip)
    return res_file
