import argparse
import os
import tempfile
from time import sleep

import git

from .utils import run_cmd


class Client():
    def __init__(self, host, user):
        """
        Base client class to run commands on local or remote host.

        Parameters:
            host(str): The target host.
            user(str): The deploying user.
        """
        self.host = host
        self.user = user

    def is_path(self, path):
        """
        Checks if path exists on host.

        Parameters:
            path(str): Path to check.
        """
        raise NotImplementedError
    
    def exec(self, commands, dir=None):
        """
        Execute shell command on host.

        Parameters:
            cmd(str): Command to execute.
            dir(str): Directory in which to run (optional).
        """
        raise NotImplementedError


class SSHClient(Client):
    """
    SSH client class to run commands on remote host.
    """
    def __init__(self, host, user, ssh_options=None):
        self.ssh_command = f"ssh {user}@{host} "
        if ssh_options:
            self.ssh_command += ssh_options
        super().__init__(host, user)

    def is_path(self, path):
        # Build the ssh command
        ssh_command = self.ssh_command + f"[ -d {path} ] && exit 1 || exit 0"
        try:
            run_cmd(ssh_command)
        except Exception:
            return True
        return False

    def exec(self, commands, dir=None):
        if not isinstance(commands, list):
            commands = [commands]
        # Build the ssh command
        ssh_command = self.ssh_command + '"'
        if dir:
            ssh_command += f"cd {dir}; "
        for cmd in commands:
            ssh_command += f"{cmd}; "
        ssh_command += '"'
        value = run_cmd(ssh_command)
        return value


class LocalHostClient(Client):
    """
    Localhost client class to run commands on local host.
    """
    def __init__(self, host, user):
        assert host == "localhost"
        super().__init__(host, user)

    def is_path(self, path):
        return os.path.exists(path)

    def exec(self, command_list, dir=None):
        if not isinstance(command_list, list):
            command = [command_list]
        else:
            command = command_list
        full_command = ""
        if dir:
            full_command += f"cd {dir}; "
        for cmd in command:
            full_command += f"{cmd}; "
        value = run_cmd(full_command)
        return value


def setup_remote(host, user, target_dir, remote=None, force=False, default_branch="master"):
    """
    Setup target and remote repositories.
    Steps:
        - SSH to host, creates the git repository on target_dir
        - Create first dummy commit
        - (optional) git push to remote backup repository

    Parameters:
        host(str): The target host.
        user(str): The deploying user.
        target_dir(str): The target git repository.
        remote(str): The remote backup git repository (optional).
        force(bool): force push to backup.
        default_branch(str): git default branch.
    """
    print(f"Creating remote repository {target_dir} on host {host} with user {user}")
    # for test purpose with /tmp folders, stay local with localhost
    if host == 'localhost':
        ssh = LocalHostClient(host, user)
        target_repo = f"{target_dir}"
    else:
        ssh = SSHClient(host, user)
        target_repo = f"ssh://{user}@{host}:{target_dir}"
    
    # create folder and make sure it exists
    ssh.exec(f"mkdir -p {target_dir}; exit 0")
    if not ssh.is_path(target_dir):
        raise Exception(f'Target directory {target_dir} not properly created on {host} with user {user}')
    
    if ssh.is_path(os.path.join(target_dir, ".git")):
        raise Exception(
            f"Git repo {target_dir} already initialised. Cleanup folder or skip initialisation."
        )
    else:
        commands = [
            f"git init -b {default_branch}",
            "git config receive.denyCurrentBranch updateInstead",
            "touch dummy.txt",
            "git add .",
            "git commit -am 'first commit'",
            "exit 0"
        ]
        ssh.exec(commands, dir=target_dir)
        if not ssh.is_path(os.path.join(target_dir, ".git")):
            raise Exception(f'Target directory {target_dir} not properly created on {host} with user {user}')

        # making sure we can clone the repository
        with tempfile.TemporaryDirectory() as tmp_repo:
            repo = git.Repo.clone_from(target_repo, tmp_repo, branch=default_branch)

            if remote:
                try:
                    repo.create_remote("backup", url=remote)
                    remote_repo = repo.remotes["backup"]
                    try:
                        remote_repo.push(force=force).raise_if_error()
                    except git.exc.GitCommandError:
                        raise git.exc.GitCommandError(
                            f"Could not push changes to remote repository {remote}.\n"
                            + "Check configuration and states of remote repository!"
                        )
                except Exception:
                    raise Exception(
                        f"Could not push first commit to backup repository {remote}! Please check the repository is empty."
                    )


def main(args=None):
    description = "Remote suite folder initialisation tool"
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--target", required=True, help="Target directory")
    parser.add_argument("--backup", help="Backup git repository")
    parser.add_argument("--host", default=os.getenv("HOSTNAME"), help="Target host")
    parser.add_argument("--user", default=os.getenv("USER"), help="Deploy user")
    parser.add_argument("--force", action="store_true", help="Force push to remote")
    parser.add_argument(
        "--no_prompt",
        action="store_true",
        help="No prompt, --force will go through without user input",
    )
    args = parser.parse_args()

    force = False
    if args.backup and args.force and not args.no_prompt:
        force = True
        check = input(
            "You are about to force push to the remote repository. Are you sure? (Y/n)"
        )
        if check != "Y":
            exit(1)

    print("Initialisation options:")
    print(f"    - host: {args.host}")
    print(f"    - user: {args.user}")
    print(f"    - target: {args.target}")
    print(f"    - backup: {args.backup}")
    print(f"    - force push: {force}")

    setup_remote(args.host, args.user, args.target, args.backup, force)


if __name__ == "__main__":
    main()
