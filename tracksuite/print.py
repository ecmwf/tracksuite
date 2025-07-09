
import os
import argparse
import logging as log
from tracksuite.ecflow_client import EcflowClient

import ecflow


def print_state(node):
    if node.get_state() == ecflow.State.complete:
        return "✅"
    elif node.get_state() == ecflow.State.active:
        return "▶️"
    elif node.get_state() == ecflow.State.queued:
        return "🔄"
    elif node.get_state() == ecflow.State.submitted:
        return "🔄"
    elif node.get_state() == ecflow.State.aborted:
        return "❌"
    else:
        raise ValueError(f"Unknown state: {node.get_state()}")


def print_node_status(node, indent=""):
    print(f"| {indent}{node.name()} | {print_state(node)} |")

    for child in node.nodes:
        print_node_status(child, indent + "--")


def get_parser():
    description = "Replace suite on server and keep some attributes from the old one"
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("node", help="Ecflow node on server to print")
    parser.add_argument("--host", default=os.getenv("HOSTNAME"), help="Target host")
    parser.add_argument("--port", default=3141, help="Ecflow port")
    return parser


def main(args=None):
    parser = get_parser()
    args = parser.parse_args()

    log.info("Revert options:")
    log.info(f"    - node: {args.node}")
    log.info(f"    - host: {args.host}")
    log.info(f"    - port: {args.port}")

    client = EcflowClient(args.host, args.port)

    # stage the suite running on the server
    defs = client.get_defs()
    node = defs.find_abs_node(args.node)
    # node = client.get_node(args.node)

    print("| Node | State |")
    print("| --- | --- |")
    print_node_status(node)


if __name__ == "__main__":
    main()
