from __future__ import annotations  # ← annotations are strings at run‑time

from typing import Any, cast

from tracksuite import LOGGER as log

try:
    import ecflow
except ModuleNotFoundError:
    ecflow = cast(Any, None)


class EcflowClient:
    """
    Class to handle the connection to the ecflow server.
    """

    def __init__(self, host: str = None, port: int = None, ssl: bool = False):
        # only raise an error at this point if ecflow is not installed
        if ecflow is None:  # type: ignore[comparison‑overlap]
            raise ModuleNotFoundError(
                "The optional dependency 'ecflow' is not installed.\n"
                "Install it, e.g.:\n"
                "    conda install ecflow"
            )

        self.host = host
        self.port = port

        if host is None and port is None:
            self.client = ecflow.Client()
        else:
            self.client = ecflow.Client(host, port)

        if ssl:
            self.client.enable_ssl()

    def update(self):
        """
        Connect to the ecflow server.
        """
        self.client.sync_local()

    def get_defs(self):
        """
        Get the suite definitions from the server.
        """
        self.update()
        defs = self.client.get_defs()
        return defs

    def get_suite(self, name: str) -> ecflow.Suite:
        """
        Get the suite definition from the server.
        """
        defs = self.get_defs()
        suite = defs.find_suite(name)
        return suite

    def set_state(self, node_path: str, state: str):
        """
        Set the state of the node on the server.
        """
        self.client.force_state(node_path, state)

    def set_dstate(self, node_path: str, dstate: ecflow.DState):
        """
        Set the dstate of the node on the server.
        """
        if str(dstate) == "suspended":
            self.client.suspend(node_path)
        else:
            self.client.resume(node_path)

    def set_defstatus(self, node_path: str, defstatus: ecflow.DState):
        """
        Set the defstatus of the node on the server.
        """
        self.client.alter(node_path, "change", "defstatus", str(defstatus))

    def update_node_status(self, new_node: ecflow.Node, old_node: ecflow.Node):
        """
        Update the status of a node based on the old node's status.
        This function updates the following attributes on the server:
            - state: queued, running, complete, failed
            - dstate: suspended or state
            - defstatus: complete or queued
        """
        node_path = new_node.get_abs_node_path()
        # Update state-related status
        self.set_state(node_path, old_node.get_state())
        self.set_dstate(node_path, old_node.get_dstate())
        self.set_defstatus(node_path, old_node.get_defstatus())

    def set_variable(self, node_path: str, key: str, value: str):
        """
        Set a variable on the server.
        """
        self.client.alter(node_path, "change", "variable", key, value)

    def set_event(self, node_path: str, key: str, value: bool):
        """
        Set an event on the server.
        """
        if value:
            value = "set"
        else:
            value = "clear"
        if value not in ["set", "clear"]:
            raise ValueError(
                f"Event value must {key} be 'set' or 'clear', value is {value}"
            )
        self.client.alter(node_path, "change", "event", key, value)

    def set_meter(self, node_path: str, key: str, value: str):
        """
        Set a meter on the server.
        """
        self.client.alter(node_path, "change", "meter", key, value)

    def set_label(self, node_path: str, key: str, value: str):
        """
        Set a label on the server.
        """
        self.client.alter(node_path, "change", "label", key, value)

    def update_node_attributes(
        self,
        new_node: ecflow.Node,
        old_node: ecflow.Node,
        attributes: list,
    ):
        """
        Update the attributes of a node based on the old node's attributes.
        This function updates the following attributes on the server:
            - state
            - dstate
            - defstatus
        """
        node_path = new_node.get_abs_node_path()
        for attr in attributes:
            old_attributes = getattr(old_node, attr)  # need to use plural form)
            for old_attr in old_attributes:
                # special case for event, where name_or_number is required instead of name
                old_name = getattr(
                    old_attr, "name_or_number", getattr(old_attr, "name")
                )()
                old_value = getattr(old_attr, "value")()
                new_attributes = getattr(new_node, attr)  # need to use plural form)
                for new_attr in new_attributes:
                    new_name = getattr(
                        new_attr, "name_or_number", getattr(new_attr, "name")
                    )()
                    new_value = getattr(new_attr, "value")()
                    if new_name == old_name:
                        if new_value != old_value:
                            getattr(self, "set_" + attr)(node_path, old_name, old_value)

    def update_node_repeat(self, new_node: ecflow.Node, old_node: ecflow.Node):
        """
        Update the repeat attribute of a node based on the old node's repeat attribute.
        This function updates the repeat attribute on the server.
        """
        node_path = new_node.get_abs_node_path()

        repeat = old_node.get_repeat()
        if str(repeat) != "":  # maybe better way to check this?
            self.client.alter(node_path, "change", "repeat", str(repeat.value()))

    def sync_node_recursive(
        self,
        new_node: ecflow.Node,
        old_node: ecflow.Node,
        attributes: list = ["event", "meter", "label"],
        skip_status: bool = False,
        skip_attributes: bool = False,
        skip_repeat: bool = False,
    ):
        """
        Recursively sync the status of nodes in the new suite with the old suite.
        This function updates the status of the new node based on the old node's status.
        It also recurses through the children of the new node.
        """
        # Compute full path of current new_node
        node_path = new_node.get_abs_node_path()
        if old_node.get_abs_node_path() != node_path:
            log.warning(f"could not find node {node_path}")
            return False

        if not skip_status:
            self.update_node_status(new_node, old_node)
        if not skip_attributes:
            self.update_node_attributes(new_node, old_node, attributes)
        if not skip_repeat:
            self.update_node_repeat(new_node, old_node)

        # Recurse through children
        for new_child in new_node.nodes:
            for old_child in old_node.nodes:
                if new_child.name() == old_child.name():
                    self.sync_node_recursive(new_child, old_child, attributes)
                    break
            else:
                log.warning(
                    f"Could not find child node {new_child.name()} in old node {node_path}"
                )

    def replace_on_server(
        self,
        node_path: str,
        definition_file: str,
        force: bool = False,
        create_parent_tree: bool = True,
    ):
        """
        Replace the suite definition on the server.
        """
        self.client.replace(node_path, definition_file, create_parent_tree, force)


def save_definition(suite: ecflow.Node, filename: str):
    """
    Save the suite definition to a file.
    """
    with open(filename, "w") as f:
        f.write(str(suite))


# def update_suite_status(new_suite: ecflow.Suite, old_suite: ecflow.Suite):
#     if new_suite.name() != old_suite.name():
#         raise ValueError("Suite names do not match. Matching by name is required.")

#     sync_status_recursive(new_suite, old_suite)
