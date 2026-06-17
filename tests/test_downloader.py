""" test of the installer download feature """
import logging
import os

import pytest

from osia.installer.downloader import download_installer

LOGGER = logging.getLogger(__name__)
INSTALLER_BINARY = "openshift-install"


def test_discovery_of_already_present_installer(create_dummy_installer, installer_version, installer_arch, caplog):
    """ Create file named openshift-install and check that download_installer will reuse it """
    dest_directory, v, _ = create_dummy_installer

    source = "prod"

    with caplog.at_level(logging.INFO):
        download_installer(installer_version, installer_arch, dest_directory, source)

    assert f"Found installer at {v}" in caplog.text


def test_download_wrong_source(tmp_path):
    """ Unsupported source should rise error"""
    installer_version = "4.19.0"

    installer_arch = "amd64"

    d = tmp_path / "installers"
    d.mkdir()
    dest_directory = d

    source = "willExplode"

    with pytest.raises(Exception, match=f"Error for source profile {source}"):
        download_installer(installer_version, installer_arch, dest_directory, source)


def test_download_4190(tmp_path):
    """ download from a prod source """
    installer_version = "4.19.0"

    installer_arch = "amd64"

    d = tmp_path / "installers"
    d.mkdir()
    dest_directory = d

    source = "prod"

    download_installer(installer_version, installer_arch, dest_directory, source)

    assert os.path.exists(d / installer_version / INSTALLER_BINARY)
    assert os.access(d / installer_version / INSTALLER_BINARY, os.X_OK)


def test_download_candidate_420(tmp_path):
    """ download from a prev source """
    installer_version_on_site = "candidate-4.20"
    installer_version = "4.20.0-ec.6"

    installer_arch = "amd64"

    d = tmp_path / "installers"
    d.mkdir()
    dest_directory = d

    source = "prev"

    download_installer(installer_version_on_site, installer_arch, dest_directory, source)

    assert os.path.exists(d / installer_version / INSTALLER_BINARY)
    assert os.access(d / installer_version / INSTALLER_BINARY, os.X_OK)


@pytest.mark.xfail
def test_download_devel(tmp_path):
    """ download from devel source fails due to missing DNS entry """
    installer_version = "4.21.0"

    installer_arch = "amd64"

    d = tmp_path / "installers"
    d.mkdir()
    dest_directory = d

    source = "devel"

    # with pytest.raises(requests.exceptions.ConnectionError):
    download_installer(installer_version, installer_arch, dest_directory, source)

    assert os.path.exists(d / installer_version / INSTALLER_BINARY)
    assert os.access(d / installer_version / INSTALLER_BINARY, os.X_OK)
