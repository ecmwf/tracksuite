import os
import argparse
import tempfile
import git


def revert_to_n_commit(git_url, n_state):
    # repo_name = Path(git_url).stem
    clone_path = tempfile.mkdtemp(prefix="suite_")
    
    # Clone the repository if it doesn't already exist
    print(f"Cloning repository from {git_url}...")
    repo = git.Repo.clone_from(git_url, clone_path)
    
    # Check if the repository is clean
    if repo.is_dirty():
        raise Exception("The repository has uncommitted changes. Stash or commit them before reverting.")
    
    # Get the commit history and select the target commit
    commits = list(repo.iter_commits())
    if n_state > len(commits):
        raise Exception(f"The repository has only {len(commits)} commits. Cannot revert to {n_state} states back.")
    
    target_commit = commits[n_state]  # n_state counts back from the latest commit
    print(f"Reverting changes to commit: {target_commit.hexsha}")
    print(f"Commit message: \n {target_commit.message}")
    
    # Revert changes since the target commit
    repo.git.revert(f'{target_commit.hexsha}..HEAD', no_commit=True)
    repo.index.commit(f"Reverted repository to {n_state} commits back (reverting to commit {target_commit.hexsha})")

    check = input(
        f"You are about to revert the git repository to the above previous commit ({n_state} commits back). Are you sure? (y/N)"
    )
    if check != "y":
        exit(1)
    
    remote_repo = repo.remotes["origin"]
    try:
        remote_repo.push().raise_if_error()
    except git.exc.GitCommandError:
        raise git.exc.GitCommandError(
            f"Could not push changes to remote repository {git_url}. "
            + "Check configuration and the state of the remote repository! "
            + "The remote repository might have uncommited changes."
        )
    print(f"Repository reverted with a new commit that undoes changes since {n_state} commits back.")


def main(args=None):
    description = "Revert a git repository to a previous state by creating a new commit that undoes changes since the target commit."
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("git_url", help="URL of the git repository to revert")
    parser.add_argument("n_state", type=int, help="Number of states to revert back")
    parser.add_argument(
        "--no_prompt",
        action="store_true",
        help="No prompt, --force will go through without user input",
    )
    args = parser.parse_args()

    print("Revert options:")
    print(f"    - git_url: {args.git_url}")
    print(f"    - n_state: {args.n_state}")

    revert_to_n_commit(args.git_url, args.n_state)

if __name__ == "__main__":
    main()
