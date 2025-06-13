import os
import tempfile

import pytest

from tracksuite.deploy import GitDeployment
from tracksuite.init import setup_remote
from tracksuite.revert import GitRevert


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

    reverter = GitRevert(
        target_repo,
        host="localhost",
        user=current_user,
    )

    return deployer, reverter


def test_deploy_default(git_deployment):
    deployer, reverter = git_deployment
    staging_dir = deployer.staging_dir

    os.mkdir(staging_dir)
    with open(os.path.join(staging_dir, "dummy1.txt"), "w") as f:
        f.write("dummy content 1")
    deployer.pull_remotes()
    deployer.diff_staging()
    deployer.deploy("This is my change 1")

    with open(os.path.join(staging_dir, "dummy2.txt"), "w") as f:
        f.write("dummy content 2")
    deployer.pull_remotes()
    deployer.diff_staging()
    deployer.deploy("This is my change 2")

    reverter.pull_remotes()

    hash_init = reverter.check_repos()
    reverter.revert(1, "Revert to first commit")
    reverter.check_state_remote(hash_init, "target")
    reverter.push_to_remotes()

    deployer.pull_remotes()
    latest_commit = deployer.repo.head.commit
    assert "Revert to first commit" in latest_commit.message
    assert not os.path.exists(os.path.join(deployer.target_dir, "dummy2.txt"))
