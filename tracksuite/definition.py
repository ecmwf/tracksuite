import argparse
import logging as log
import os

from tracksuite.ecflow_client import EcflowClient, save_definition
from tracksuite.repos import GitRepositories


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

    def_file = args.def_file
    if args.def_file is None:
        def_file = f"{args.name}.def"

    # Get the suite definition from the server
    client = EcflowClient(args.host, args.port)
    suite = client.get_suite(args.name)

    # Save the suite definition to a file
    filename = os.path.join(deployer.local_dir, def_file)
    save_definition(suite, filename)

    deployer.pull_remotes()

    hash_init = deployer.check_sync_local_remote("target")
    if deployer.backup_repo:
        deployer.check_sync_local_remote("backup")
        deployer.check_sync_remotes("target", "backup")

    # Commit the changes to the local repository
    log.info("    -> Git commit")
    if not deployer.commit(message="Update suite definition from server"):
        log.info("Nothing to commit... aborting")
        return False

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
    description = "Update suite definition on target from server"
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("name", help="Ecflow suite name")
    parser.add_argument("--def_file", help="Name of the definition file to update")
    parser.add_argument(
        "--target", required=True, help="Path to target git repository on host"
    )
    parser.add_argument(
        "--local", required=True, help="Path to local git repository. DEFAULT: $TMP"
    )
    parser.add_argument("--backup", required=True, help="URL to backup git repository")
    parser.add_argument("--host", default=os.getenv("HOSTNAME"), help="Target host")
    parser.add_argument("--user", default=os.getenv("USER"), help="Deploy user")
    parser.add_argument("--port", default=3141, help="Ecflow port")

    args = parser.parse_args()

    update_definition_from_server(args)


if __name__ == "__main__":
    main()
