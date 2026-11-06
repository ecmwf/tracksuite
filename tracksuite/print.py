"""
tracksuite.print
================

Provides utilities for printing ecFlow node trees with state icons and formatting options.
Supports raw, Markdown, and HTML output formats. Displays job output logs for tasks if available.

Classes:
    SuiteDisplay: Extracts and formats ecFlow node trees and associated logs.
    Formatter: Abstract base class for output formatters.
    RawFormatter: Formatter for plain text output.
    MarkdownFormatter: Formatter for Markdown output.
    HTMLFormatter: Formatter for HTML output.

Functions:
    get_state_icon(node): Returns a unicode icon for the ecFlow node state.
    get_formatter(format_type): Returns a formatter instance for the given format type.
    get_parser(): Returns an argument parser for the CLI.
    main(args=None): CLI entry point.

Usage:
    tracksuite-print <node> [--host HOST] [--port PORT] [-f FORMAT] [--failed-only] [-n TAIL]
"""

import argparse
import os
from collections import deque
from typing import Any, cast

from tracksuite.ecflow_client import EcflowClient

try:
    import ecflow
except ModuleNotFoundError:
    ecflow = cast(Any, None)


def get_state_icon(node):
    """
    Return a unicode icon representing the state of the given ecFlow node.

    Args:
        node (ecflow.Node): The ecFlow node.

    Returns:
        str: Unicode icon for the node state.

    Raises:
        ValueError: If the node state is unknown.
    """
    if node.get_state() == ecflow.State.complete:
        return "✅"
    elif node.get_state() == ecflow.State.active:
        return "▶️"
    elif node.get_state() == ecflow.State.queued:
        return "⏸️"
    elif node.get_state() == ecflow.State.submitted:
        return "🔄"
    elif node.get_state() == ecflow.State.aborted:
        return "❌"
    else:
        raise ValueError(f"Unknown state: {node.get_state()}")


def read_log(path, tail=None):
    """
    Read a job output file, optionally keeping only its last lines.

    Args:
        path (str): Path to the job output file.
        tail (int, optional): Number of lines to keep from the end of the file.

    Returns:
        str: Log content, prefixed with a note if it was truncated.
    """
    if not path or not os.path.exists(path):
        return "Could not find jobout file."
    with open(path, "r", errors="replace") as f:
        if tail is None:
            return f.read()
        n_lines = 0
        last_lines = deque(maxlen=tail)
        for line in f:
            n_lines += 1
            last_lines.append(line)
    content = "".join(last_lines)
    if n_lines > tail:
        content = (
            f"[... truncated, showing last {tail} of {n_lines} lines ...]\n" + content
        )
    return content


class SuiteDisplay:
    """
    Extracts and formats an ecFlow node tree and associated job output logs.

    Args:
        format (str): Output format ('raw', 'md', or 'html').
        failed_only (bool): Only extract job output of aborted tasks.
        tail (int, optional): Only keep the last N lines of each job output.
    """

    def __init__(self, format="raw", failed_only=False, tail=None):
        self.tree = ""
        self.content = {}
        self.formatter = get_formatter(format)
        self.failed_only = failed_only
        self.tail = tail

    def process_task(self, task):
        """
        Process a task node, extracting its job output if available.

        Args:
            task (ecflow.Task): The task node.

        Returns:
            str or None: Path label for the task, or None if its job output is skipped.
        """
        if self.failed_only and task.get_state() != ecflow.State.aborted:
            return None
        var = task.find_gen_variable("ECF_JOBOUT")
        jobout = getattr(var, "value")()
        path = f"{task.get_abs_node_path()} + {get_state_icon(task)}"
        self.content[path] = read_log(jobout, self.tail)
        return path

    def extract_node_tree(self, node, prefix=""):
        """
        Recursively extract the node tree structure and build formatted output.

        Args:
            node (ecflow.Node): The root node.
            prefix (str): Prefix for tree formatting.
        """
        if self.tree == "":
            self.tree = f"{node.name()}/\n"

        children = node.nodes
        n_child = 0
        for child in children:
            n_child += 1
        children = node.nodes
        for i, child in enumerate(children):
            connector = "└── " if i == n_child - 1 else "├── "
            state_icon = get_state_icon(child)
            label = f"{child.name()} {state_icon}"
            if isinstance(child, ecflow.Task):
                anchor = self.process_task(child)
                if anchor is not None:
                    label = self.formatter.label(anchor, label)
            line = f"{prefix}{connector}{label}\n"
            self.tree += line
            try:
                if child.nodes:
                    extension = "    " if i == n_child - 1 else "│   "
                    self.extract_node_tree(child, prefix + extension)
            except Exception:
                # hit in case of Alias type, but maybe others too
                pass

    def print(self):
        """
        Print the formatted node tree and logs using the selected formatter.
        """
        self.formatter.tree(self.tree)
        if self.failed_only and not self.content:
            print("No failed tasks.")
        else:
            self.formatter.logs(self.content)


def get_formatter(format_type):
    """
    Return a formatter instance for the given format type.

    Args:
        format_type (str): Output format ('raw', 'md', or 'html').

    Returns:
        Formatter: Formatter instance.

    Raises:
        ValueError: If the format type is unknown.
    """
    if format_type == "raw":
        return RawFormatter()
    elif format_type == "md":
        return MarkdownFormatter()
    elif format_type == "html":
        return HTMLFormatter()
    else:
        raise ValueError(f"Unknown format type: {format_type}")


class Formatter:
    """
    Abstract base class for output formatters.
    """

    def tree(self, tree):
        """
        Print the formatted node tree.

        Args:
            tree (str): The formatted tree string.
        """
        raise NotImplementedError("Header method not implemented")

    def logs(self, logs):
        """
        Print the logs for each node.

        Args:
            logs (dict): Mapping from node path to log content.
        """
        raise NotImplementedError("Logs method not implemented")

    def label(self, anchor, label):
        """
        Format a label for a node.

        Args:
            anchor (str): Anchor or reference for the node.
            label (str): Display label.

        Returns:
            str: Formatted label.
        """
        raise NotImplementedError("Label method not implemented")


class RawFormatter(Formatter):
    """
    Formatter for plain text output.
    """

    def tree(self, tree):
        print(tree)

    def logs(self, logs):
        print("Logs cannot be printed in raw format.")

    def label(self, anchor, label):
        return label


class MarkdownFormatter(RawFormatter):
    """
    Formatter for Markdown output.
    """

    def tree(self, tree):
        print("```text")
        print(tree)
        print("```")

    def logs(self, logs):
        for name, content in logs.items():
            print(f'<details id="{name}">\n')
            print(f"<summary><strong>{name}</strong></summary>\n\n")
            print(f"{content}\n\n")
            print("</details>\n")


class HTMLFormatter(Formatter):
    """
    Formatter for HTML output.
    """

    def tree(self, tree):
        print("<pre>")
        print(tree)
        print("</pre>\n")

    def logs(self, logs):
        for name, content in logs.items():
            print(f'<details id="{name}">\n')
            print(f"<summary><strong>{name}</strong></summary>\n\n")
            print("<pre><code>\n")
            print(f"{content}\n\n")
            print("</code></pre>\n")
            print("</details>\n")

    def label(self, anchor, label):
        return f'<a href="#{anchor}">{label}</a>'


def get_parser():
    """
    Return an argument parser for the CLI.

    Returns:
        argparse.ArgumentParser: The argument parser.
    """
    description = "Print ecFlow node tree with states"
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("node", help="Ecflow node on server to print")
    parser.add_argument("--host", default=os.getenv("HOSTNAME"), help="Target host")
    parser.add_argument("--port", default=3141, help="Ecflow port")
    parser.add_argument(
        "-f", "--format", default="raw", help="Output format (md, html, raw)"
    )
    parser.add_argument(
        "--failed-only",
        action="store_true",
        help="Only print logs of aborted tasks (no effect in raw format)",
    )
    parser.add_argument(
        "-n",
        "--tail",
        type=int,
        default=None,
        help="Only print the last N lines of each log (default: full log)",
    )
    return parser


def main(args=None):
    """
    CLI entry point for printing ecFlow node trees.

    Args:
        args (list, optional): Command-line arguments.
    """
    parser = get_parser()
    args = parser.parse_args()

    client = EcflowClient(args.host, args.port)
    node = client.get_node(args.node)

    processor = SuiteDisplay(args.format, failed_only=args.failed_only, tail=args.tail)
    processor.extract_node_tree(node)
    processor.print()


if __name__ == "__main__":
    main()
