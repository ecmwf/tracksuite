import argparse
import os

from tracksuite import LOGGER as log
from tracksuite.ecflow_client import EcflowClient


def replace_on_server(
    name: str,
    definition,
    host: str,
    port: int,
    enable_ssl: bool,
    node_path: str = None,
    sync_variables: bool = False,
    skip_status: bool = False,
    skip_attributes: bool = False,
    skip_repeat: bool = False,
):
    """
    Replace a suite on the server with a new definition file while keeping some attributes from the old suite.

    Parameters:
        name (str): Name of the Ecflow suite to replace.
        definition (str or ecflow.Defs): Path to the new definition file or ecflow.Defs object.
        host (str): Hostname of the Ecflow server.
        port (int): Port number of the Ecflow server.
        enable_ssl (bool): Whether to enable SSL connection.
        node_path (str, optional): Path to the node to replace. If not provided, the entire suite is replaced.
        sync_variables (bool): If True, synchronise variables from the old suite to the new one.
        skip_status (bool): If True, do not synchronise the status of the nodes.
        skip_attributes (bool): If True, do not synchronise attributes of the nodes.
        skip_repeat (bool): If True, do not synchronise repeat attributes of the nodes.
    """

    log.warning(
        "The 'replace_on_server' function of tracksuite is experimental. Do not use it in production!"
    )

    node_path = node_path or f"/{name}"
    attributes = ["events", "meters", "labels"]
    if sync_variables:
        attributes.append("variables")

    # we need two clients because the defs and suite objects are updated as well
    # when we update the client from the server
    old_client = EcflowClient(host, port, enable_ssl)
    new_client = EcflowClient(host, port, enable_ssl)

    # stage the suite running on the server
    old_suite = old_client.get_suite(name)

    new_client.replace_on_server(node_path, definition, force=False)

    new_suite = new_client.get_suite(name)

    new_client.sync_node_recursive(
        new_suite,
        old_suite,
        attributes=attributes,
        skip_status=skip_status,
        skip_attributes=skip_attributes,
        skip_repeat=skip_repeat,
    )

    # udpate new suite to check the status
    new_client.update()
    new_suite = new_client.get_suite(name)


def get_parser():
    description = "Replace suite on server and keep some attributes from the old one"
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("name", help="Ecflow suite name")
    parser.add_argument(
        "--def-file", required=True, help="Name of the definition file to update"
    )
    parser.add_argument("--host", default=os.getenv("HOSTNAME"), help="Target host")
    parser.add_argument("--port", default=3141, help="Ecflow port")
    parser.add_argument(
        "--enable-ssl", help="Enable SSL connection", action="store_true"
    )
    parser.add_argument("--node", help="Path to the node to replace")
    parser.add_argument(
        "--sync-variables", help="Synchronise variables", action="store_true"
    )
    parser.add_argument(
        "--skip-status", help="Don't synchronise status", action="store_true"
    )
    parser.add_argument(
        "--skip-attributes", help="Don't synchronise attributes", action="store_true"
    )
    parser.add_argument(
        "--skip-repeat", help="Don't synchronise repeat", action="store_true"
    )
    return parser


def main(args=None):
    parser = get_parser()
    args = parser.parse_args()
    replace_on_server(
        name=args.name,
        definition=args.def_file,
        host=args.host,
        port=args.port,
        enable_ssl=args.enable_ssl,
        node_path=args.node,
        sync_variables=args.sync_variables,
        skip_status=args.skip_status,
        skip_attributes=args.skip_attributes,
        skip_repeat=args.skip_repeat,
    )


if __name__ == "__main__":
    main()
