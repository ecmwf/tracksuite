import argparse
import os
import subprocess
from filecmp import dircmp

import git


class GitDeployment:
    def __init__(
        self,
        host=None,
        user=None,
        suite_dir=None,
        local_repo=None,
        target_repo=None,
        backup_repo=None,
    ):

        print("Creating deployer:")
        deploy_user = os.getenv("USER")
        deploy_host = os.getenv("HOSTNAME")
        self.user = deploy_user if user is None else user
        self.host = deploy_host if host is None else host

        self.suite_dir = suite_dir

        self.local_dir = local_repo
        self.target_dir = target_repo

        # setup local repo
        self.target_repo = f"ssh://{self.host}:{target_repo}"
        try:
            print(f"    -> Loading local repo {local_repo}")
            self.repo = git.Repo(local_repo)
        except (git.exc.NoSuchPathError, git.exc.InvalidGitRepositoryError):
            print(
                f"    -> Could not find git repo in {local_repo}, cloning from {self.target_repo}"
            )
            self.repo = git.Repo.clone_from(self.target_repo, local_repo, depth=1)

        # link with backup repo
        self.backup_repo = backup_repo
        if backup_repo and "backup" not in self.repo.remotes:
            print(f"    -> Creating backup remote {backup_repo}")
            self.repo.create_remote("backup", url=backup_repo)
            self.check_sync_remotes("origin", "backup")

    def get_hash_remote(self, remote):
        return self.repo.git.ls_remote("--heads", remote, "master").split("\t")[0]

    def check_sync_local_remote(self, remote):
        remote_repo = self.repo.remotes[remote]
        remote_repo.fetch()
        hash_target = self.get_hash_remote(remote)
        hash_local = self.repo.git.rev_parse("master")
        if hash_target != hash_local:
            print(f"Local hash {hash_local}")
            print(f"Target hash {hash_target}")
            raise Exception(
                f"Local ({self.local_dir}) and remote ({remote}) git repositories not in sync!"
            )

    def check_sync_remotes(self, remote1, remote2):
        remote_repo1 = self.repo.remotes[remote1]
        remote_repo2 = self.repo.remotes[remote2]
        remote_repo1.fetch()
        remote_repo2.fetch()
        hash1 = self.get_hash_remote(remote1)
        hash2 = self.get_hash_remote(remote2)
        if hash1 != hash2:
            print(f"Remote {remote1} hash {hash1}")
            print(f"Remote {remote2} hash {hash2}")
            raise Exception(
                f"Remote git repositories ({remote1} and {remote2}) not in sync!"
            )

    def commit(self, message):
        try:
            commit_message = (
                f"deployed by {self.user} from {self.host}:{self.suite_dir}\n"
            )
            if message:
                commit_message += message
            self.repo.git.add("--all")
            diff = self.repo.index.diff(self.repo.commit())
            if diff:
                self.repo.index.commit(commit_message)
            else:
                raise Exception("Nothing to commit")
        except Exception as e:
            print("Commit failed!")
            raise e

    def push(self, remote):
        remote_repo = self.repo.remotes[remote]
        try:
            remote_repo.push().raise_if_error()
        except git.exc.GitCommandError:
            raise git.exc.GitCommandError(
                f"Could not push changes to remote repository {remote}.\n"
                + "Check configuration and states of remote repository!"
            )

    def pull_target(self, remote):
        remote_repo = self.repo.remotes[remote]
        remote_repo.pull()

    def diff_staging(self):
        modified = []
        removed = []
        added = []

        def get_diff_files(dcmp, root=""):
            for name in dcmp.diff_files:
                path = os.path.join(root, name)
                modified.append(path)
            for name in dcmp.left_only:
                path = os.path.join(root, name)
                fullpath = os.path.join(self.suite_dir, path)
                if os.path.isdir(fullpath):
                    for root_dir, dirs, files in os.walk(fullpath):
                        for file in files:
                            filepath = os.path.relpath(
                                os.path.join(root, root_dir, file), self.suite_dir
                            )
                            added.append(filepath)
                else:
                    added.append(path)
            for name in dcmp.right_only:
                path = os.path.join(root, name)
                fullpath = os.path.join(self.target_dir, path)
                if os.path.isdir(fullpath):
                    for root_dir, dirs, files in os.walk(fullpath):
                        for file in files:
                            filepath = os.path.relpath(
                                os.path.join(root, root_dir, file), self.target_dir
                            )
                            removed.append(filepath)
                else:
                    removed.append(path)
            for dir, sub_dcmp in dcmp.subdirs.items():
                get_diff_files(sub_dcmp, root=os.path.join(root, dir))

        diff = dircmp(self.suite_dir, self.target_dir)
        print("Changes in staged suite:")
        get_diff_files(diff)
        changes = [
            ("Removed", removed),
            ("Added", added),
            ("Modified", modified),
        ]
        for name, files in changes:
            if files:
                print(f"    - {name}:")
                for path in files:
                    print(f"        - {path}")

    def deploy(self, message):
        print("Deploying suite to remote locations:")
        # check if repos are in sync
        print("    -> Checking that git repos are in sync")
        self.check_sync_local_remote("origin")
        if self.backup_repo:
            self.check_sync_local_remote("backup")
            self.check_sync_remotes("origin", "backup")

        # rsync staging folder to current repo
        print("    -> Staging suite")
        # TO DO: check if rsync fails
        cmd = f"rsync -avz --delete {self.suite_dir}/ {self.local_dir}/ --exclude .git"
        run_cmd(cmd)
        # POSSIBLE TO DO: lock others for change

        # git commit and push to remotes
        print("    -> Git commit")
        self.commit(message)
        print(f"    -> Git push to target {self.target_repo} on host {self.host}")
        self.push("origin")
        if self.backup_repo:
            print(f"    -> Git push to backup repository {self.backup_repo}")
            self.push("backup")

    # TODO: add function to sync remotes
    def sync_remotes(self, source, target):
        return


class FakeOuput:
    returncode = 1
    stderr = "Timeout! It took more than 300 seconds"


def run_cmd(cmd, capture_output=True, timeout=1000, **kwargs):
    try:
        value = subprocess.run(
            cmd, shell=True, capture_output=capture_output, timeout=timeout, **kwargs
        )
    except subprocess.TimeoutExpired:
        value = FakeOuput()
    if value.returncode > 0:
        raise Exception(f"ERROR! Command failed!\n{value}")
    return value


def main(args=None):
    description = "Suite deployment tool"
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--suite", required=True, help="Suite to deploy")
    parser.add_argument("--staging", required=True, help="Staging suite directory")
    parser.add_argument("--target", required=True, help="Target directory")
    parser.add_argument("--backup", help="Backup git repository")
    parser.add_argument("--host", default=os.getenv("HOSTNAME"), help="Target host")
    parser.add_argument("--user", default=os.getenv("USER"), help="Deploy user")
    parser.add_argument(
        "--push", action="store_true", help="Push staged suite to target"
    )
    parser.add_argument("--message", help="Git message")

    args = parser.parse_args()

    print("Initialisation options:")
    print(f"    - host: {args.host}")
    print(f"    - user: {args.user}")
    print(f"    - suite: {args.staging}")
    print(f"    - staging: {args.staging}")
    print(f"    - target: {args.target}")
    print(f"    - backup: {args.backup}")
    print(f"    - git message: {args.message}")

    deployer = GitDeployment(
        host=args.host,
        user=args.user,
        suite_dir=args.suite,
        local_repo=args.staging,
        target_repo=args.target,
        backup_repo=args.backup,
    )

    deployer.pull_target("origin")
    deployer.diff_staging()

    if args.push:
        check = input(
            "You are about to push the staged suite to the target directory. Are you sure? (Y/n)"
        )
        if check != "Y":
            exit(1)
        deployer.deploy(args.message)


if __name__ == "__main__":
    main()
