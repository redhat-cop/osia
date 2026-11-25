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
"""Module implements logic for persistence layer of osia

Currently the only supported persistance is via git.
Module is responsible for maintenance of the git repository
and to store the generated artifacts by the `openshift-install
binary."""
import logging
import secrets
import time
from datetime import datetime, timezone

from git import Repo, GitCommandError
from git.remote import PushInfo


PUSH_RETRIES = 5
PUSH_BACKOFF = 2
PUSH_ERROR_FLAGS = (PushInfo.ERROR
                    | PushInfo.REJECTED
                    | PushInfo.REMOTE_REJECTED
                    | PushInfo.REMOTE_FAILURE)


class PersistenceException(Exception):
    """Raised when local changes cannot be persisted to the git remote."""


def _push_rejected(push_infos):
    """
    Returns True when any entry of a push result reports a
    rejection or error.
    """
    return any(info.flags & PUSH_ERROR_FLAGS for info in push_infos)


def _push_to_backup_branch(rep, remote_name, branch):
    """
    Pushes the current local HEAD to a new, uniquely named remote branch
    so the locally committed changes are not lost -- this matters in
    particular when `osia install` runs on an ephemeral node that is
    discarded afterwards. Admins can then inspect the branch and either
    resolve the conflict manually or clean up the cluster without merging
    it into the main branch.
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    suffix = secrets.token_hex(2)
    backup_branch = f"{branch}-osia-backup-{timestamp}-{suffix}"
    try:
        rep.remotes[remote_name].push(f"HEAD:refs/heads/{backup_branch}")
    except GitCommandError:
        logging.exception("Failed to push local changes to backup branch %s", backup_branch)
        return
    logging.warning(
        "Pushed local changes to backup branch %s/%s to avoid data loss",
        remote_name, backup_branch)


def _push_with_retry(rep, remote, retries=PUSH_RETRIES):
    """
    Pushes the current branch to its remote tracking branch.

    When a push is rejected -- typically because another osia instance
    pushed in parallel in the time between `check_repository` and this
    push -- the local branch is rebased on top of the updated remote
    branch and the push is retried, up to `retries` times, with an
    exponential backoff between attempts.

    If the push cannot succeed (rebase conflict or exhausted retries),
    the local commits are pushed to a dedicated backup branch to avoid
    data loss before a `PersistenceException` is raised.
    """
    remote_name = remote.remote_name
    branch = remote.remote_head
    for attempt in range(1, retries + 1):
        push_infos = rep.remotes[remote_name].push()
        if not _push_rejected(push_infos):
            return
        logging.warning(
            "Push to %s/%s rejected (attempt %d/%d), rebasing on remote and retrying",
            remote_name, branch, attempt, retries)
        rep.remotes[remote_name].fetch()
        try:
            rep.git.rebase(f"{remote_name}/{branch}")
        except GitCommandError as exception:
            rep.git.rebase("--abort")
            _push_to_backup_branch(rep, remote_name, branch)
            raise PersistenceException(
                f"Failed to rebase on {remote_name}/{branch} due to conflicts"
            ) from exception
        if attempt < retries:
            time.sleep(PUSH_BACKOFF * 2 ** (attempt - 1))
    _push_to_backup_branch(rep, remote_name, branch)
    raise PersistenceException(
        f"Failed to push changes to {remote_name}/{branch} after {retries} attempts")


def check_repository():
    """Function checks local repository if it is up2date with
    remote.
    In case when there is difference between upstream and
    local copy it tries to pull from remote.

    It returns the Repo object and remote associated with
    current tracking branch."""
    rep = Repo("./")
    remote = rep.active_branch.tracking_branch()
    if remote:
        fetches = rep.remotes[remote.remote_name].fetch()
        for fetch in fetches:
            if fetch.name == remote.name and fetch.commit != rep.commit():
                logging.warning("There are changes in remote repository, trying to pull")
                rep.remotes[remote.remote_name].pull()
    if rep.is_dirty():
        logging.warning("There are not committed changes in your repository, please fix this")

    return rep, remote


def write_changes(cluster_directory):
    """Function stages generated directory, which contains files
    generated by openshift-install function, creates commit,
    and pushes to the remote of tracking branch."""
    rep, remote = check_repository()
    rep.index.add(cluster_directory)
    logging.info("Commiting installer changes for cluster %s", cluster_directory)
    rep.index.commit(f"[OCP Installer] installation files for {cluster_directory} added")
    if remote:
        _push_with_retry(rep, remote)


def delete_directory(cluster_directory):
    """Function deletes commited directory both
    from local copy and from the remote repository."""
    rep, remote = check_repository()
    logging.info("Removing cluster directory from git repository %s", cluster_directory)
    rep.index.remove(cluster_directory, working_tree=True, r=True, f=True)
    rep.index.commit(f"[OCP Installer] removed installation files for {cluster_directory}")
    if remote:
        _push_with_retry(rep, remote)
