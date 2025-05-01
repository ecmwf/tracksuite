import argparse
import os
import logging as log

import ecflow

from .repos import GitRepositories


def get_suite_definition(client, name):
    """
    Get the suite definition from the server.
    """
    client.sync_local()
    defs = client.get_defs()
    suite = defs.find_suite(name)
    return suite


def save_definition(suite, filename):
    """
    Save the suite definition to a file.
    """
    with open(filename, "w") as f:
        f.write(str(suite))


def update_definition_from_server(args):
    """
    Update the suite definition on the target repository.
    Steps:
        - Get the suite definition from the server
        - Save the suite definition to a file
        - Push the changes to the target repository
    """

    # Create the GitSuiteDefinition object
    deployer = GitRepositories(
        host=args.host,
        user=args.user,
        target_repo=args.target,
        backup_repo=args.backup,
        local_repo=args.local,
    )

    # Get the suite definition from the server
    client = ecflow.Client(args.host, args.user)
    suite = get_suite_definition(client, args.name)

    # Save the suite definition to a file
    filename = os.path.join(args.local, f"{args.name}.ecf")
    save_definition(suite, filename)

    deployer.pull_remotes()

    hash_init = deployer.check_sync_local_remote("target")
    if deployer.backup_repo:
        deployer.check_sync_local_remote("backup")
        deployer.check_sync_remotes("target", "backup")

    # Commit the changes to the local repository
    log.info("    -> Git commit")
    if not deployer.commit(args.message):
        log.info("Nothing to commit... aborting")
        return False
    deployer.commit(message="Update suite definition from server")

    hash_check = deployer.get_hash_remote("target")
    if hash_check != hash_init:
        raise Exception(
            "Remote repositories have changed during deployment!\n \
            Please check the state of the remote repositories"
        )

    deployer.push("target")
    if deployer.backup_repo:
        log.info(f"    -> Git push to backup repository {deployer.backup_repo}")
        deployer.push("backup")


def main(args=None):
    description = "Update suite definition on target"
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--target", required=True, help="Path to target git repository on host"
    )
    parser.add_argument("--local", help="Path to local git repository. DEFAULT: $TMP")
    parser.add_argument("--backup", help="URL to backup git repository")
    parser.add_argument("--host", default=os.getenv("HOSTNAME"), help="Target host")
    parser.add_argument("--user", default=os.getenv("USER"), help="Deploy user")
    parser.add_argument("--server", required=True, help="Ecflow server")
    parser.add_argument("--port", required=True, help="Ecflow port")
    parser.add_argument("--name", required=True, help="Ecflow suite name")

    args = parser.parse_args()

    update_definition_from_server(args)
