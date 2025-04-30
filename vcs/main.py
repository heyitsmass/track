from colorama import init as c_init
import json
from lib.base import Core

c_init()


def print_if_verbose(*args, quiet: bool = True, **kwargs):
    if not quiet:
        if len(args) == 1:
            return print(
                json.dumps(args[0], indent=4) if isinstance(args[0], dict) else args[0],
                *args[1:],
                **kwargs,
            )
        print(*args, **kwargs)


if __name__ == "__main__":
    vcs = Core(default_branch_name="main")
    # vcs.add(".")
    # vcs.commit("Second Commit.")
    vcs.checkout(branch_name="stage", create_branch=True)
    print(vcs.branches)