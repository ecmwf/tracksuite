import os
import ecflow
from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, Tree
from textual.widgets.tree import TreeNode


class ECFTree(Tree):
    def load_defs(self, defs: ecflow.Defs):
        for suite in defs.suites:
            self.load_node(suite, self.root)

    def load_node(self, node: ecflow.Node, parent: TreeNode):
        label = node.name() + f" ({node.__class__.__name__})"
        if isinstance(node, (ecflow.Suite, ecflow.Family)):
            cur = parent.add(label)
            for child in node.nodes:
                self.load_node(child, cur)
        else:
            cur = parent.add_leaf(label)
        # TODO: load attributes
        # crons, dates, days, events, generics, inlimits, labels, limits, meters, queues, times, todays, variables


class Viewer(App):
    BINDINGS = [
        ("q", "quit", "Quit"),
    ]

    def __init__(self, defs: ecflow.Defs, label: str = "Defs"):
        super().__init__()
        self.label = label
        self.defs = defs

    def compose(self) -> ComposeResult:
        yield Header()
        yield ECFTree(self.label)
        yield Footer()

    def on_mount(self):
        self.title = "ecFlow Definition Viewer"
        tree = self.query_one(ECFTree)
        tree.load_defs(self.defs)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("infile")
    args = parser.parse_args()

    defs = ecflow.Defs(args.infile)
    app = Viewer(defs, os.path.basename(args.infile))
    app.run()