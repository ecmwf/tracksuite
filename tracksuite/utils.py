import subprocess


class FakeOuput:
    returncode = 1
    stderr = "Timeout! It took more than 300 seconds"


def run_cmd(cmd, capture_output=True, timeout=1000, **kwargs):
    """
    Runs a shell command.

    Parameters:
        cmd(str): command to run.

    Returns:
        Exit code.
    """
    try:
        value = subprocess.run(
            cmd, shell=True, capture_output=capture_output, timeout=timeout, **kwargs
        )
    except subprocess.TimeoutExpired:
        value = FakeOuput()
    if value.returncode > 0:
        raise Exception(f"ERROR! Command failed!\n{value}")
    return value
