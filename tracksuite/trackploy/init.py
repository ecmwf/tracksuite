import argparse
import os

from .utils import run_cmd


class SSHClient:
    def __init__(self, host, user, ssh_options=None):
        self.host = host
        self.user = user
        self.ssh_command = f"ssh {self.user}@{self.host} "
        if ssh_options:
            self.ssh_command += ssh_options

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
        run_cmd(ssh_command)


class SSHParamiko:
    def __init__(self, host, user):
        """
        Class wrapping the paramiko SSHClient object.

        Parameters:
            host(str): The target host.
            user(str): The deploying user.
        """
        import paramiko

        ssh = paramiko.SSHClient()
        ssh.load_system_host_keys()
        try:
            ssh.connect(hostname=host, username=user)
        except paramiko.ssh_exception.AuthenticationException:
            raise paramiko.ssh_exception.AuthenticationException(
                f"Could not setup remote ssh connection. Check your username ({user}) and host ({host})"
            )
        self.sftp = ssh.open_sftp()
        self.ssh = ssh

    def is_path(self, path):
        """
        Checks if path exists on remote host.

        Parameters:
            path(str): Path to check.
        """
        try:
            self.sftp.stat(path)
            return True
        except FileNotFoundError:
            return False

    def exec(self, cmd, dir=None):
        """
        Execute shell command on remote host.

        Parameters:
            cmd(str): Command to execute.
            dir(str): Directory in which to run (optional).
        """
        if dir:
            cmd = f"cd {dir}; {cmd}"
        stdin, stdout, stderr = self.ssh.exec_command(cmd)
        if stdout.channel.recv_exit_status() != 0:
            for out in stdout, stderr:
                for line in out:
                    print(line)
            raise Exception(f"SSH exec command failed: {cmd}")


def setup_remote(host, user, target_dir, remote=None, push_options=None):
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
        push_options(str): git push options ('typically --force').
    """
    print(f"Creating remote repository {target_dir} on host {host} with user {user}")
    ssh = SSHClient(host, user)
    ssh.exec(f"mkdir -p {target_dir}")
    if ssh.is_path(os.path.join(target_dir, ".git")):
        raise Exception(
            f"Git repo {target_dir} already initialised. Cleanup folder or skip initialisation."
        )
    else:
        commands = [
            "git init",
            "git config receive.denyCurrentBranch updateInstead",
            "touch dummy.txt",
            "git add .",
            "git commit -am 'first commit'",
        ]
        ssh.exec(commands, dir=target_dir)
        if remote:
            try:
                remote_cmds = [
                    f"git remote add origin {remote}",
                    f"git push {push_options} -u origin master",
                ]
                ssh.exec(remote_cmds, dir=target_dir)
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

    push_options = ""
    if args.backup and args.force and not args.no_prompt:
        push_options += "-f"
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
    print(f"    - push_options: {push_options}")

    setup_remote(args.host, args.user, args.target, args.backup, push_options)


if __name__ == "__main__":
    main()