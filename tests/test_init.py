import os
import tempfile
from unittest.mock import patch

import git
import pytest

from tracksuite.init import LocalHostClient, SSHClient, setup_remote


@pytest.fixture
def ssh_client():
    return SSHClient("test_host", "test_user")


def side_effect_for_run_cmd(ssh_command):
    return ssh_command


@pytest.fixture
def mock_run_cmd_returns_input(mocker):
    with patch("tracksuite.init.run_cmd") as mock:
        mock.side_effect = side_effect_for_run_cmd
        yield mock


def test_ssh_client_exec(ssh_client, mock_run_cmd_returns_input):
    # Execute the method under test
    command_to_execute = ["echo Hello World"]
    result = ssh_client.exec(command_to_execute)

    # Assert that the mock was called with the expected command
    expected_ssh_command = f'ssh test_user@test_host "{command_to_execute[0]}; "'
    mock_run_cmd_returns_input.assert_called_with(expected_ssh_command)

    # Assert that the result is what our side_effect function returns
    assert (
        result == expected_ssh_command
    ), "The mock did not return the expected dynamic value"


class DummyReturnCode:
    def __init__(self, returncode):
        self.returncode = returncode


@pytest.fixture
def mock_run_cmd_returns_true(mocker):
    with patch("tracksuite.init.run_cmd") as mock:
        mock.return_value = DummyReturnCode(0)
        yield mock


def test_ssh_client_is_path(ssh_client, mock_run_cmd_returns_true):
    ssh_client = SSHClient("test_host", "test_user")

    # Execute the method under test
    result = ssh_client.is_path("/tmp")
    assert result is True


def test_localhost_client_different_user():
    with pytest.raises(Exception):
        LocalHostClient("localhost", "invalid_user")


def test_localhost_client_same_user():
    current_user = os.getenv("USER")
    LocalHostClient("localhost", current_user)


def test_localhost_client_exec():
    current_user = os.getenv("USER")
    localhost = LocalHostClient("localhost", current_user)
    command_to_execute = ["echo Hello World"]
    result = localhost.exec(command_to_execute)
    assert result.returncode == 0


def test_localhost_client_is_path():
    current_user = os.getenv("USER")
    localhost = LocalHostClient("localhost", current_user)

    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = os.path.join(temp_dir, "test_dir")
        localhost.exec(f"mkdir {test_dir}")
        localhost.is_path(test_dir)


def test_setup_remote():
    with tempfile.TemporaryDirectory() as temp_dir:
        remote_path = os.path.join(temp_dir, "remote")
        current_user = os.getenv("USER")
        setup_remote(
            host="localhost",
            user=current_user,
            target_dir=remote_path,
        )
        assert os.path.exists(remote_path)
        assert os.path.exists(os.path.join(remote_path, ".git"))
        assert os.path.exists(os.path.join(remote_path, "dummy.txt"))

        repo = git.Repo(remote_path)
        commit_history = repo.iter_commits()
        for commit in commit_history:
            print(commit.message)
            assert "first commit" in commit.message


def test_setup_remote_with_backup():
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_path = os.path.join(temp_dir, "my_repo.git")
        repo = git.Repo.init(repo_path, bare=True)

        remote_path = os.path.join(temp_dir, "remote")
        current_user = os.getenv("USER")
        setup_remote(
            host="localhost",
            user=current_user,
            target_dir=remote_path,
            remote=repo_path,
        )
        assert os.path.exists(remote_path)
        assert os.path.exists(os.path.join(remote_path, ".git"))
        assert os.path.exists(os.path.join(remote_path, "dummy.txt"))

        commit_history = repo.iter_commits()
        for commit in commit_history:
            assert "first commit" in commit.message
            print(commit.message)


def test_setup_remote_with_backup_fail():
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_path = os.path.join(temp_dir, "my_repo.git")
        repo = git.Repo.init(repo_path, bare=True)

        # Add a dummy commit
        repo.index.commit("Dummy commit 1")
        repo.index.commit("Dummy commit 2")
        commit_history = repo.iter_commits()
        for commit in commit_history:
            print(commit.message)

        remote_path = os.path.join(temp_dir, "remote")
        current_user = os.getenv("USER")
        with pytest.raises(Exception):
            setup_remote(
                host="localhost",
                user=current_user,
                target_dir=remote_path,
                remote=repo_path,
            )


def test_setup_remote_with_backup_force():
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_path = os.path.join(temp_dir, "my_repo.git")
        repo = git.Repo.init(repo_path, bare=True)

        # Add a dummy commit
        repo.index.commit("Dummy commit 1")
        repo.index.commit("Dummy commit 2")
        commit_history = repo.iter_commits()
        for commit in commit_history:
            print(commit.message)

        remote_path = os.path.join(temp_dir, "remote")
        current_user = os.getenv("USER")
        setup_remote(
            host="localhost",
            user=current_user,
            target_dir=remote_path,
            remote=repo_path,
            force=True,
        )
