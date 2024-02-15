import subprocess


class CmdError(Exception):
    def __init__(self, cause, process_ret):
        super().__init__(
            f"ERROR: Command failed with {cause} ({process_ret.returncode})"
            f"\nCalled: {process_ret.args}"
            f"\nOutput: {process_ret.output}"
        )


def run_cmd(cmd, timeout=300, **kwargs):
    """
    Runs a shell command.

    Parameters:
        cmd(str): command to run.

    Returns:
        Exit code.
    """
    try:
        ret = subprocess.run(
            cmd,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            encoding="utf8",
            **kwargs,
        )
    except subprocess.TimeoutExpired as exc:
        exc.returncode = -1
        raise CmdError("timeout", exc)
    except subprocess.CalledProcessError as exc:
        exc.output = str(exc)
        raise CmdError("error", exc)
    except Exception as exc:
        exc.returncode = 99
        exc.output = str(exc)
        raise CmdError("foreign error", exc)
    return ret
