import os
import tempfile

import git

from tracksuite import LOGGER as log


class GitRepositories:
    def __init__(
        self,
        host=None,
        user=None,
        target_repo=None,
        backup_repo=None,
        local_repo=None,
    ):
        """
        Class used to deploy suites through git.

        Parameters:
            host(str): The target host.
            user(str): The deploying user.
            target_repo(str): Path to the target repository on the target host.
            backup_repo(str): URL of the backup repository.
            local_repo(str): Path to the local repository.
        """

        self.deploy_user = os.getenv("USER")
        self.deploy_host = os.getenv("HOSTNAME")
        self.user = self.deploy_user if user is None else user
        self.host = self.deploy_host if host is None else host

        if local_repo is None:
            local_repo = tempfile.mkdtemp(prefix="suite_")
        self.local_dir = local_repo

        self.target_dir = target_repo

        # setup local repo
        # for test purpose with /tmp folders, stay local with localhost
        if self.host == "localhost":
            if self.user != os.getenv("USER"):
                raise ValueError("Local deployment must be done with the current user")
            self.target_repo = f"{target_repo}"
        else:
            self.target_repo = f"ssh://{self.user}@{self.host}:{target_repo}"

        try:
            log.info(f"    -> Loading local repo {local_repo}")
            self.repo = git.Repo(local_repo)
        except (git.exc.NoSuchPathError, git.exc.InvalidGitRepositoryError):
            log.info(f"    -> Cloning from {self.target_repo}")
            self.repo = git.Repo.clone_from(self.target_repo, local_repo)
            self.repo.remotes["origin"].rename("target")

        # get the name of the default branch
        self.default_branch = self.repo.active_branch.name

        # link with backup repo
        self.backup_repo = backup_repo
        if backup_repo and "backup" not in self.repo.remotes:
            log.info(f"    -> Creating backup remote {backup_repo}")
            self.repo.create_remote("backup", url=backup_repo)
            self.sync_remotes()

    def pull_remotes(self):
        """
        Git pull the remote repository to the local repository
        """
        remote_repo = self.repo.remotes["target"]
        remote_repo.pull()
        self.check_sync_local_remote("target")
        if self.backup_repo:
            self.sync_remotes()

    def push(self, remote):
        """
        Pushes the local state to the remote repository

        Parameters:
            remote(str): Name of the remote repository (typically "target").
        """
        remote_repo = self.repo.remotes[remote]
        try:
            remote_repo.push().raise_if_error()
        except git.exc.GitCommandError:
            raise git.exc.GitCommandError(
                f"Could not push changes to remote repository {remote}. "
                + "Check configuration and the state of the remote repository! "
                + "The remote repository might have uncommited changes."
            )

    def check_sync_remotes(self, remote1, remote2):
        """
        Check that two remote repositories have the same git hash.
        Raise exception if the git hashes don't match.

        Parameters:
            remote1(str): Name of the first remote repository (typically "target").
            remote2(str): Name of the second remote repository (typically "backup").

        Returns:
            The matching git hash.
        """
        remote_repo1 = self.repo.remotes[remote1]
        remote_repo2 = self.repo.remotes[remote2]
        remote_repo1.fetch()
        remote_repo2.fetch()
        hash1 = self.get_hash_remote(remote1)
        hash2 = self.get_hash_remote(remote2)
        if hash1 != hash2:
            log.info(f"Remote {remote1} hash {hash1}")
            log.info(f"Remote {remote2} hash {hash2}")
            raise Exception(
                f"Remote git repositories ({remote1} and {remote2}) not in sync!"
            )
        return hash1

    def get_hash_remote(self, remote):
        """
        Get the git hash of a remote repository on the default branch.

        Parameters:
            remote(str): Name of the remote repository (typically "target").

        Returns:
            The git hash of the default branch.
        """
        remote_branch = self.repo.remotes[remote].refs[self.default_branch]
        return remote_branch.commit.hexsha

    def check_sync_local_remote(self, remote):
        """
        Check that the local repository git hash is the same as the remote.
        Raise exception if the git hashes don't match.

        Parameters:
            remote(str): Name of the remote repository (typically "target").

        Returns:
            The matching git hash.
        """
        remote_repo = self.repo.remotes[remote]
        remote_repo.fetch()
        hash_target = self.get_hash_remote(remote)
        hash_local = self.repo.active_branch.commit.hexsha
        if hash_target != hash_local:
            log.info(f"Local hash {hash_local}")
            log.info(f"Target hash {hash_target}")
            raise Exception(
                f"Local ({self.local_dir}) and remote ({remote}) git repositories not in sync!"
            )
        return hash_local

    def sync_remotes(self):
        """
        Sync the remote repositories.
        Steps:
            - git fetch remote repositories and check they are in sync
            - git push to backup if needed
        """
        try:
            self.check_sync_local_remote("backup")
            self.check_sync_remotes("target", "backup")
        except Exception:
            log.info("WARNING! Backup repository outdated. Pushing update to backup")
            self.push("backup")

    def push_to_remotes(self):
        """
        Push the changes to the remote repository.
        """
        log.info(f"    -> Git push to {self.target_repo}")
        self.push("target")
        if self.backup_repo:
            log.info(f"    -> Git push to backup repository {self.backup_repo}")
            self.push("backup")

    def check_state_remote(self, hash, remote):
        hash_check = self.get_hash_remote(remote)
        if hash_check != hash:
            raise Exception(
                "Remote repositories have changed during deployment!\n \
                Please check the state of the remote repositories"
            )

    def check_repos(self):
        """
        Check if the repository is clean and if the local and remote repositories are in sync.
        Returns the hash of the initial state.
        """
        log.info("    -> Checking that git repos are in sync")
        # Check if the repository is clean
        if self.repo.is_dirty():
            raise Exception(
                "The repository has uncommitted changes. Stash or commit them before reverting."
            )

        hash_init = self.check_sync_local_remote("target")
        if self.backup_repo:
            self.check_sync_local_remote("backup")
            self.check_sync_remotes("target", "backup")

        return hash_init

    def commit(self, message=None, files=None):
        """
        Commits the current stage of the local repository.
        Throws exception if there is nothing to commit.
        Default commit message will be:
            "deployed by {user} from {host}:{staging_dir}"

        Parameters:
            message(str): optional git commit message to append to default message
        """
        if files is None:
            files = "--all"
        try:
            commit_message = f"deployed by {self.deploy_user} from {self.deploy_host}\n"
            if message:
                commit_message += message
            self.repo.git.add(files)
            diff = self.repo.index.diff(self.repo.commit())
            if diff:
                self.repo.index.commit(commit_message)
            else:
                return False
        except Exception as e:
            log.info("Commit failed!")
            raise e
        return True
