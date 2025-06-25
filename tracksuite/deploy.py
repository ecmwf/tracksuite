import argparse
import os
from filecmp import dircmp

from tracksuite import LOGGER as log
from tracksuite.repos import GitRepositories
from tracksuite.utils import run_cmd


class GitDeployment(GitRepositories):
    def __init__(
        self,
        host=None,
        user=None,
        staging_dir=None,
        local_repo=None,
        target_repo=None,
        backup_repo=None,
    ):
        """
        Class used to deploy suites through git.

        Parameters:
            host(str): The target host.
            user(str): The deploying user.
            staging_dir(str): The source suite directory.
            local_repo(str): Path to the local repository.
            target_repo(str): Path to the target repository on the target host.
            backup_repo(str): URL of the backup repository.
        """
        super().__init__(
            host=host,
            user=user,
            target_repo=target_repo,
            backup_repo=backup_repo,
            local_repo=local_repo,
        )

        self.staging_dir = staging_dir
        if self.staging_dir is None:
            raise Exception("Staging directory not specified")

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
            commit_message = f"deployed by {self.deploy_user} from {self.deploy_host}:{self.staging_dir}\n"
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

    def diff_staging(self):
        """
        Prints the difference between the staged suite and the current suite
        """
        modified = []
        removed = []
        added = []

        def get_diff_files(dcmp, root=""):
            for name in dcmp.diff_files:
                path = os.path.join(root, name)
                modified.append(path)
            for name in dcmp.left_only:
                path = os.path.join(root, name)
                fullpath = os.path.join(self.staging_dir, path)
                if os.path.isdir(fullpath):
                    for root_dir, dirs, files in os.walk(fullpath):
                        for file in files:
                            filepath = os.path.relpath(
                                os.path.join(root, root_dir, file), self.staging_dir
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

        diff = dircmp(self.staging_dir, self.local_dir)
        log.info("Changes in staged suite:")
        get_diff_files(diff)
        changes = [
            ("Removed", removed),
            ("Added", added),
            ("Modified", modified),
        ]
        for name, files in changes:
            if files:
                log.info(f"    - {name}:")
                for path in files:
                    log.info(f"        - {path}")
        log.info("For more details, compare the following folders:")
        log.info(self.staging_dir)
        log.info(self.local_dir)

    def deploy(self, message=None, files=None):
        """
        Deploy the staged suite to the target repository.
        Steps:
            - git fetch remote repositories and check they are in sync
            - rsync the staged folder to the local repository
            - git add all the suite files and commit
            - git push to remotes
        Default commit message will be:
            "deployed by {user} from {host}:{staging_dir}"

        Parameters:
            message(str): optional git commit message to append to default message.
        """
        log.info("Deploying suite to remote locations")
        # check if repos are in sync
        log.info("    -> Checking that git repos are in sync")
        hash_init = self.check_sync_local_remote("target")
        if self.backup_repo:
            self.check_sync_local_remote("backup")
            self.check_sync_remotes("target", "backup")

        # rsync staging folder to current repo
        log.info("    -> Staging suite")

        rsync_options = "-avzc --delete  --exclude .git "
        cmd = f"rsync {rsync_options} {self.staging_dir}/ {self.local_dir}/"
        run_cmd(cmd)

        # git commit and push to remotes
        log.info("    -> Git commit")
        if not self.commit(message, files):
            log.info("Nothing to commit... aborting")
            return False
        log.info(f"    -> Git push to target {self.target_repo} on host {self.host}")

        hash_check = self.get_hash_remote("target")
        if hash_check != hash_init:
            raise Exception(
                "Remote repositories have changed during deployment!\n \
                Please check the state of the remote repositories"
            )

        self.push("target")
        if self.backup_repo:
            log.info(f"    -> Git push to backup repository {self.backup_repo}")
            self.push("backup")

        return True


def get_parser():
    description = "Suite deployment tool"
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--stage", required=True, help="Staged suite")
    parser.add_argument(
        "--target", required=True, help="Path to target git repository on host"
    )
    parser.add_argument(
        "--local",
        help="Path to local git repository (will be created if doesn't exist)",
    )
    parser.add_argument("--backup", help="URL to the backup git repository")
    parser.add_argument("--host", default=os.getenv("HOSTNAME"), help="Target host")
    parser.add_argument("--user", default=os.getenv("USER"), help="Deploy user")
    parser.add_argument("--message", help="Git message")
    parser.add_argument(
        "--push", action="store_true", help="Push staged suite to target"
    )
    parser.add_argument(
        "-f",
        "--files",
        nargs="+",
        help="Specific files to deploy, by default everything is deployed",
    )
    return parser


def main(args=None):
    parser = get_parser()
    args = parser.parse_args()

    log.info("Initialisation options:")
    log.info(f"    - host: {args.host}")
    log.info(f"    - user: {args.user}")
    log.info(f"    - staged suite: {args.stage}")
    log.info(f"    - local repo: {args.local}")
    log.info(f"    - target repo: {args.target}")
    log.info(f"    - backup repo: {args.backup}")
    log.info(f"    - git message: {args.message}")
    log.info(f"    - files to deploy: {args.files}")

    deployer = GitDeployment(
        host=args.host,
        user=args.user,
        staging_dir=args.stage,
        local_repo=args.local,
        target_repo=args.target,
        backup_repo=args.backup,
    )

    deployer.pull_remotes()
    deployer.diff_staging()

    if args.push:
        if args.files is not None:
            log.info("Deploying only the following files:")
            for f in args.files:
                log.info(f"    - {f}")

        check = input(
            "You are about to push the staged suite to the target directory. Are you sure? (y/N)"
        )
        if check != "y":
            exit(1)
        deployer.deploy(args.message, args.files)


if __name__ == "__main__":
    main()
