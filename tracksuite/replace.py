import os
import argparse

from tracksuite import EcflowClient


def replace_on_server(args):
    suite = args.name
    new_def_file = args.def_file

    # we need two clients because the defs and suite objects are updated as well
    # when we update the client from the server
    old_client = EcflowClient(args.host, args.port)
    new_client = EcflowClient(args.host, args.port)

    # grab the suite running on the server
    old_suite = old_client.get_suite(suite)

    new_client.replace_on_server(args.node_path, new_def_file, force=False)

    new_suite = new_client.get_suite(suite)
    new_client.sync_node_recursive(new_suite, old_suite)

    # udpate new suite to check the status
    new_client.update()
    new_suite = new_client.get_suite(suite)
    # print(fin_suite.get_state())
    # print(fin_suite.get_dstate())
    # print(fin_suite.get_defstatus())


def get_parser():
    description = "Replace suite on server and keep some attributes from the old one"
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("name", help="Ecflow suite name")
    parser.add_argument(
        "--def_file", required=True, help="Name of the definition file to update"
    )
    parser.add_argument("--node", help="Path to the node to replace")
    parser.add_argument("--host", default=os.getenv("HOSTNAME"), help="Target host")
    parser.add_argument("--port", default=3141, help="Ecflow port")
    return parser


def main(args=None):
    parser = get_parser()
    args = parser.parse_args()
    replace_on_server(args)


if __name__ == "__main__":
    main()
