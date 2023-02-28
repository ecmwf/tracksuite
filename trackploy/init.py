import argparse
import os

import paramiko


class SSHParamiko:
    def __init__(self, host, user):
        """
        Class wrapping the paramiko SSHClient object.

        Parameters:
            host(str): The target host.
            user(str): The deploying user.
        """
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
    ssh = SSHParamiko(host, user)
    ssh.exec(f"mkdir -p {target_dir}")
    if ssh.is_path(os.path.join(target_dir, ".git")):
        raise Exception(
            f"Git repo {target_dir} already initialised. Cleanup folder or skip initialisation."
        )
    else:
        ssh.exec("git init", dir=target_dir)
        ssh.exec("git config receive.denyCurrentBranch updateInstead", dir=target_dir)
        ssh.exec("touch suite.def", dir=target_dir)
        ssh.exec("git add .", dir=target_dir)
        ssh.exec("git commit -am 'first commit'", dir=target_dir)
        if remote:
            ssh.exec(f"git remote add origin {remote}", dir=target_dir)
            ssh.exec(f"git push {push_options} -u origin master", dir=target_dir)


def main(args=None):
    description = "Remote suite folder initialisation tool"
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--target", required=True, help="Target directory")
    parser.add_argument("--backup", help="Backup git repository")
    parser.add_argument("--host", default=os.getenv("HOSTNAME"), help="Target host")
    parser.add_argument("--user", default=os.getenv("USER"), help="Deploy user")
    parser.add_argument("--force", action="store_true", help="Force push to remote")
    args = parser.parse_args()

    push_options = ""
    if args.backup and args.force:
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
