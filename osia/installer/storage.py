import logging
from git import Repo


def check_repository():
    rep = Repo("./")
    remote = rep.active_branch.tracking_branch()
    fetches = rep.remotes[remote.remote_name].fetch()
    for fetch in fetches:
        if fetch.name == remote.name and fetch.commit != rep.commit():
            logging.error("There are changes in remote repository, we won't be able to push in the end")
    if rep.is_dirty():
        logging.warning("There are not committed changes in your repository, please fix this")

    return rep, remote


def write_changes(cluster_directory):
    rep, remote = check_repository()
    rep.index.add(cluster_directory)
    logging.info("Commiting installer changes for cluster %s", cluster_directory)
    rep.index.commit(f"[OCP Installer] installation files for {cluster_directory} added")

    rep.remotes[remote.remote_name].push()


def delete_directory(cluster_directory):
    rep = Repo("./")
    remote = rep.active_branch.tracking_branch()

    logging.info("Removing cluster directory from git repository %s", cluster_directory)
    rep.index.remove(cluster_directory, working_tree=True, r=True, f=True)
    rep.index.commit(f"[OCP Installer] removed installation files for {cluster_directory}")
    rep.remotes[remote.remote_name].push()
