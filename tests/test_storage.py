"""Tests for the git persistence layer, focused on the push retry logic."""
# pylint: disable=protected-access
from unittest import mock

import pytest
from git import GitCommandError
from git.remote import PushInfo

from osia.installer import storage
from osia.installer.storage import PersistenceException


def _push_info(flags):
    """Create a fake PushInfo carrying the given flags."""
    info = mock.MagicMock()
    info.flags = flags
    return info


def _make_repo():
    """Return a mocked Repo and the mocked remote it exposes via
    ``rep.remotes[name]``."""
    rep = mock.MagicMock()
    remote_handle = rep.remotes.__getitem__.return_value
    return rep, remote_handle


def _tracking_ref():
    """Return a mocked tracking-branch reference."""
    ref = mock.MagicMock()
    ref.remote_name = "origin"
    ref.remote_head = "master"
    return ref


@pytest.fixture(autouse=True)
def _no_sleep():
    """Avoid real backoff delays during the tests."""
    with mock.patch.object(storage.time, "sleep") as sleep:
        yield sleep


@pytest.mark.parametrize("flags", [
    PushInfo.ERROR,
    PushInfo.REJECTED,
    PushInfo.REMOTE_REJECTED,
    PushInfo.REMOTE_FAILURE,
])
def test_push_rejected_detects_error_flags(flags):
    """Any error/rejection flag is reported as a rejection."""
    assert storage._push_rejected([_push_info(flags)]) is True


@pytest.mark.parametrize("flags", [
    PushInfo.UP_TO_DATE,
    PushInfo.FAST_FORWARD,
    PushInfo.NEW_HEAD,
])
def test_push_rejected_accepts_successful_flags(flags):
    """Successful push outcomes are not treated as rejections."""
    assert storage._push_rejected([_push_info(flags)]) is False


def test_push_succeeds_first_attempt():
    """A clean push does not trigger a fetch or rebase."""
    rep, remote_handle = _make_repo()
    remote_handle.push.return_value = [_push_info(PushInfo.FAST_FORWARD)]

    storage._push_with_retry(rep, _tracking_ref())

    remote_handle.push.assert_called_once()
    remote_handle.fetch.assert_not_called()
    rep.git.rebase.assert_not_called()


def test_push_recovers_after_rejection(_no_sleep):
    """A rejected push is retried after fetch + rebase + backoff, then succeeds."""
    rep, remote_handle = _make_repo()
    remote_handle.push.side_effect = [
        [_push_info(PushInfo.REJECTED)],
        [_push_info(PushInfo.FAST_FORWARD)],
    ]

    storage._push_with_retry(rep, _tracking_ref())

    assert remote_handle.push.call_count == 2
    remote_handle.fetch.assert_called_once()
    rep.git.rebase.assert_called_once_with("origin/master")
    _no_sleep.assert_called_once_with(storage.PUSH_BACKOFF)


def test_push_backoff_is_exponential(_no_sleep):
    """The delay between retries grows exponentially."""
    rep, remote_handle = _make_repo()
    remote_handle.push.return_value = [_push_info(PushInfo.REJECTED)]

    with pytest.raises(PersistenceException):
        storage._push_with_retry(rep, _tracking_ref())

    # Backoff happens between attempts only (not after the last one).
    assert [c.args[0] for c in _no_sleep.call_args_list] == [
        storage.PUSH_BACKOFF * 2 ** i for i in range(storage.PUSH_RETRIES - 1)
    ]


def test_push_raises_after_exhausting_retries():
    """Persistent rejection raises PersistenceException after all retries and
    preserves the local changes on a backup branch."""
    rep, remote_handle = _make_repo()
    remote_handle.push.return_value = [_push_info(PushInfo.REJECTED)]

    with pytest.raises(PersistenceException,
                       match=f"after {storage.PUSH_RETRIES} attempts"):
        storage._push_with_retry(rep, _tracking_ref())

    # One push per attempt plus one backup-branch push.
    assert remote_handle.push.call_count == storage.PUSH_RETRIES + 1
    backup_refspec = remote_handle.push.call_args.args[0]
    assert backup_refspec.startswith("HEAD:refs/heads/master-osia-backup-")


def test_push_aborts_rebase_on_conflict():
    """A rebase conflict aborts the rebase, preserves changes on a backup
    branch, and raises PersistenceException."""
    rep, remote_handle = _make_repo()
    remote_handle.push.return_value = [_push_info(PushInfo.REJECTED)]
    rep.git.rebase.side_effect = [GitCommandError("git rebase", 1), None]

    with pytest.raises(PersistenceException, match="due to conflicts"):
        storage._push_with_retry(rep, _tracking_ref())

    rep.git.rebase.assert_any_call("--abort")
    backup_refspec = remote_handle.push.call_args.args[0]
    assert backup_refspec.startswith("HEAD:refs/heads/master-osia-backup-")


def test_backup_branch_push_failure_is_logged(caplog):
    """When the backup push itself fails, it is logged and the original
    PersistenceException is still raised."""
    rep, remote_handle = _make_repo()
    remote_handle.push.side_effect = (
        [[_push_info(PushInfo.REJECTED)]] * storage.PUSH_RETRIES
        + [GitCommandError("git push", 1)]
    )

    with pytest.raises(PersistenceException,
                       match=f"after {storage.PUSH_RETRIES} attempts"):
        storage._push_with_retry(rep, _tracking_ref())

    assert "Failed to push local changes to backup branch" in caplog.text
