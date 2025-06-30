import argparse
import os

from tracksuite import LOGGER, warn
from tracksuite.ecflow_client import EcflowClient, save_definition
from tracksuite.repos import GitRepositories


def update_definition_from_server(
    name: str,
    definition: str,
    user: str,
    host: str,
    port: int,
    target: str,
    backup: str,
    local: str,
):
    """
    Update the suite definition on the target repository.
    Steps:
        - Get the suite definition from the server
        - Save the suite definition to a file
        - Push the changes to the target repository
    """

    warn(
        "The 'update_definition_from_server' function of tracksuite is experimental. Do not use it in production!",
        stacklevel=2,
    )

    # Create the GitSuiteDefinition object
    deployer = GitRepositories(
        host=host,
        user=user,
        target_repo=target,
        backup_repo=backup,
        local_repo=local,
    )

    if definition is None:
        definition = f"{name}.def"

    # Get the suite definition from the server
    client = EcflowClient(host, port)
    suite = client.get_suite(name)

    # Save the suite definition to a file
    filename = os.path.join(deployer.local_dir, definition)
    save_definition(suite, filename)

    deployer.pull_remotes()

    hash_init = deployer.check_sync_local_remote("target")
    if deployer.backup_repo:
        deployer.check_sync_local_remote("backup")
        deployer.check_sync_remotes("target", "backup")

    # Commit the changes to the local repository
    LOGGER.info("    -> Git commit")
    if not deployer.commit(message="Update suite definition from server"):
        LOGGER.info("Nothing to commit... aborting")
        return False

    hash_check = deployer.get_hash_remote("target")
    if hash_check != hash_init:
        raise Exception(
            "Remote repositories have changed during deployment!\n \
            Please check the state of the remote repositories"
        )

    deployer.push("target")
    if deployer.backup_repo:
        LOGGER.info(f"    -> Git push to backup repository {deployer.backup_repo}")
        deployer.push("backup")


def get_parser():
    description = "Update suite definition on target from ecflow server"
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("name", help="Ecflow suite name")
    parser.add_argument("--definition", help="Name of the definition file to update")
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
    return parser


def main(args=None):
    parser = get_parser()
    args = parser.parse_args()
    update_definition_from_server(
        name=args.name,
        definition=args.definition,
        user=args.user,
        host=args.host,
        port=args.port,
        target=args.target,
        backup=args.backup,
        local=args.local,
    )


if __name__ == "__main__":
    main()
