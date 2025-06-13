import os
import tempfile

import git
import pytest

from tracksuite.deploy import GitDeployment
from tracksuite.init import setup_remote


@pytest.fixture
def git_deployment():
    temp_dir = tempfile.TemporaryDirectory().name
    staging_dir = os.path.join(temp_dir, "staging")
    target_repo = os.path.join(temp_dir, "target")
    current_user = os.getenv("USER")
    setup_remote(
        host="localhost",
        user=current_user,
        target_dir=target_repo,
    )

    deployer = GitDeployment(
        host="localhost",
        user=current_user,
        staging_dir=staging_dir,
        target_repo=target_repo,
    )

    return deployer


@pytest.fixture
def git_deployment_with_backup():
    temp_dir = tempfile.TemporaryDirectory().name
    staging_dir = os.path.join(temp_dir, "staging")
    target_repo = os.path.join(temp_dir, "target")
    backup_path = os.path.join(temp_dir, "backup.git")
    git.Repo.init(backup_path, bare=True)
    current_user = os.getenv("USER")
    setup_remote(
        host="localhost",
        user=current_user,
        target_dir=target_repo,
        remote=backup_path,
    )

    deployer = GitDeployment(
        host="localhost",
        user=current_user,
        staging_dir=staging_dir,
        target_repo=target_repo,
        backup_repo=backup_path,
    )

    return deployer


def test_git_deployment_constructor(git_deployment):
    assert git_deployment.host == "localhost"
    assert git_deployment.user == os.getenv("USER")
    print(git_deployment.target_dir)
    assert os.path.exists(git_deployment.target_dir)


def test_git_deployment_constructor_with_backup(git_deployment_with_backup):
    assert git_deployment_with_backup.host == "localhost"
    assert git_deployment_with_backup.user == os.getenv("USER")
    print(git_deployment_with_backup.target_dir)
    assert os.path.exists(git_deployment_with_backup.target_dir)
    assert os.path.exists(git_deployment_with_backup.backup_repo)


def test_deploy_default(git_deployment):
    deployer = git_deployment
    staging_dir = deployer.staging_dir

    os.mkdir(staging_dir)
    with open(os.path.join(staging_dir, "dummy.txt"), "w") as f:
        f.write("dummy content")

    deployer.pull_remotes()
    deployer.diff_staging()
    deployer.deploy()

    with open(os.path.join(deployer.target_dir, "dummy.txt"), "r") as f:
        assert f.read() == "dummy content"

    repo = git.Repo(deployer.target_dir)
    commit_history = repo.iter_commits()
    all_commits = [commit for commit in commit_history]
    assert f"deployed by {deployer.user}" in all_commits[0].message


def test_deploy_message(git_deployment):
    deployer = git_deployment
    staging_dir = deployer.staging_dir

    os.mkdir(staging_dir)
    with open(os.path.join(staging_dir, "dummy.txt"), "w") as f:
        f.write("dummy content")

    deployer.pull_remotes()
    deployer.diff_staging()
    deployer.deploy("This is my change")

    with open(os.path.join(deployer.target_dir, "dummy.txt"), "r") as f:
        assert f.read() == "dummy content"

    repo = git.Repo(deployer.target_dir)
    commit_history = repo.iter_commits()
    all_commits = [commit for commit in commit_history]
    assert "This is my change" in all_commits[0].message


def test_deploy_with_backup(git_deployment_with_backup):
    deployer = git_deployment_with_backup
    staging_dir = deployer.staging_dir

    os.mkdir(staging_dir)
    with open(os.path.join(staging_dir, "dummy.txt"), "w") as f:
        f.write("dummy content")

    deployer.pull_remotes()
    deployer.diff_staging()
    deployer.deploy("This is my change")

    with open(os.path.join(deployer.target_dir, "dummy.txt"), "r") as f:
        assert f.read() == "dummy content"

    repo = git.Repo(deployer.target_repo)
    commit_history = repo.iter_commits()
    all_commits = [commit for commit in commit_history]
    assert "This is my change" in all_commits[0].message


def test_deploy_files(git_deployment):
    deployer = git_deployment
    staging_dir = deployer.staging_dir

    os.mkdir(staging_dir)
    for file in ["file1.txt", "file2.txt", "file3.txt"]:
        with open(os.path.join(deployer.staging_dir, file), "w") as f:
            f.write("dummy content")

    deployer.pull_remotes()
    deployer.diff_staging()
    deployer.deploy(files=["file1.txt", "file2.txt"])

    assert os.path.exists(os.path.join(deployer.target_dir, "file1.txt"))
    assert os.path.exists(os.path.join(deployer.target_dir, "file2.txt"))
    assert not os.path.exists(os.path.join(deployer.target_dir, "file3.txt"))
