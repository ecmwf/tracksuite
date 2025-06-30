import argparse
import os

from tracksuite import LOGGER as log
from tracksuite.repos import GitRepositories


class GitRevert(GitRepositories):
    def __init__(
        self,
        target_repo,
        host=None,
        user=None,
        backup_repo=None,
        local_repo=None,
    ):
        """
        Class used to revert git repositories to a previous state.

        Parameters:
            target_repo(str): Path to the target repository on the target host.
            n_state(int): Number of states to revert
            host(str): The target host.
            user(str): The deploying user.
            backup_repo(str): URL of the backup repository.
            local_repo(str): Path to the local repository.
        """

        log.info("Creating reverter:")
        super().__init__(
            host=host,
            user=user,
            target_repo=target_repo,
            backup_repo=backup_repo,
            local_repo=local_repo,
        )

    def revert(self, n_state, message=None):
        """
        Revert a git repository to a previous state by creating a new commit
        that undoes changes since the target commit.
        """

        # Get the commit history and select the target commit
        commits = list(self.repo.iter_commits())
        if n_state > len(commits):
            raise Exception(
                f"The repository has only {len(commits)} commits. Cannot revert to {n_state} states back."
            )

        target_commit = commits[n_state]  # n_state counts back from the latest commit
        log.info(f"    -> Reverting changes to commit: {target_commit.hexsha}")
        log.info(f"    -> Commit message: \n {target_commit.message}")

        # Revert changes since the target commit
        self.repo.git.revert(f"{target_commit.hexsha}..HEAD", no_commit=True)
        commit_message = f"Revert changes since {n_state} commits back (reverting to commit {target_commit.hexsha})."
        if message is not None:
            commit_message += f"\n{message}"
        self.repo.index.commit(commit_message)


def main(args=None):
    description = "Revert a git repository to a previous state."
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("target", help="Path to target git repository on host")
    parser.add_argument("n_state", type=int, help="Number of states to revert back")
    parser.add_argument("--host", default="localhost", help="Target host")
    parser.add_argument("--user", default=os.getenv("USER"), help="Deploy user")
    parser.add_argument("--message", help="Git message")
    parser.add_argument("--backup", help="URL to the backup git repository")
    parser.add_argument(
        "--no_prompt",
        action="store_true",
        help="No prompt, --force will go through without user input",
    )

    args = parser.parse_args()

    log.info("Revert options:")
    log.info(f"    - target repo: {args.target}")
    log.info(f"    - number of commits to revert to: {args.n_state}")
    log.info(f"    - host: {args.host}")
    log.info(f"    - user: {args.user}")
    log.info(f"    - backup repo: {args.backup}")
    log.info(f"    - git message: {args.message}")

    reverter = GitRevert(
        args.target,
        host=args.host,
        user=args.user,
        backup_repo=args.backup,
    )
    log.info("Reverting git repository to a previous state")
    hash_init = reverter.check_repos()

    reverter.revert(args.n_state, args.message)

    if not args.no_prompt:
        check = input(
            f"You are about to revert the git repository to the above previous commit ({args.n_state} commits back). Are you sure? (y/N)"  # noqa: E501
        )
        if check != "y":
            exit(1)

    reverter.check_state_remote(hash_init, "target")
    reverter.push_to_remotes()

    log.info(
        f"Repository reverted with a new commit that undoes changes since {args.n_state} commits back."
    )


if __name__ == "__main__":
    main()
