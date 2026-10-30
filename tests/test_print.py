from types import SimpleNamespace

import pytest

from tracksuite import print as tsprint

STATES = SimpleNamespace(
    aborted="aborted",
    complete="complete",
    active="active",
    queued="queued",
    submitted="submitted",
)


@pytest.fixture(autouse=True)
def fake_ecflow(monkeypatch):
    monkeypatch.setattr(tsprint, "ecflow", SimpleNamespace(State=STATES))


class FakeTask:
    def __init__(self, name, state, jobout):
        self._name = name
        self._state = state
        self._jobout = str(jobout)

    def get_state(self):
        return self._state

    def get_abs_node_path(self):
        return f"/suite/{self._name}"

    def find_gen_variable(self, name):
        return SimpleNamespace(value=lambda: self._jobout)


@pytest.fixture
def tasks(tmp_path):
    failed_log = tmp_path / "failed.1"
    failed_log.write_text("failed log\n")
    success_log = tmp_path / "success.1"
    success_log.write_text("success log\n")
    return [
        FakeTask("failed", STATES.aborted, failed_log),
        FakeTask("success", STATES.complete, success_log),
    ]


def test_default_keeps_all_logs(tasks):
    display = tsprint.SuiteDisplay("md")
    for task in tasks:
        display.process_task(task)
    assert list(display.content.values()) == ["failed log\n", "success log\n"]


def test_failed_only_keeps_aborted_logs(tasks):
    display = tsprint.SuiteDisplay("md", failed_only=True)
    anchors = [display.process_task(task) for task in tasks]
    assert anchors[1] is None
    assert list(display.content.values()) == ["failed log\n"]


@pytest.fixture
def log_file(tmp_path):
    path = tmp_path / "task.1"
    path.write_text("".join(f"line {i}\n" for i in range(10)))
    return path


def test_read_log_tail(log_file):
    content = tsprint.read_log(str(log_file), tail=3)
    header = "[... truncated, showing last 3 of 10 lines ...]\n"
    assert content == header + "line 7\nline 8\nline 9\n"


@pytest.mark.parametrize("tail", [None, 10, 20])
def test_read_log_no_truncation(log_file, tail):
    assert tsprint.read_log(str(log_file), tail=tail) == log_file.read_text()
