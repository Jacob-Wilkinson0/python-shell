import sys

from ._builtins import BUILTINS
from .autocomplete import setup_autocomplete
from .executor import is_executable_path, path_dirs, run_external_command
from .output import output
from .parser import parse_redirection, parse_tokens


def main() -> None:
    setup_autocomplete()

    while True:
        sys.stdout.write("$ ")
        command_txt: str = input()
        stripped: str = command_txt.lstrip()
        if not stripped:
            continue

        tokens: list[str] = parse_tokens(stripped)
        if not tokens:
            continue

        command: str = tokens[0]
        raw_args: list[str] = tokens[1:]

        args, redirection_info = parse_redirection(raw_args)

        redirection_type = redirection_info.get("redirection_type")
        redirection_path = redirection_info.get("file")
        redirection_mode = redirection_info.get("mode", "w")

        if command in BUILTINS:
            BUILTINS[command](
                args, redirection_type, redirection_path, redirection_mode
            )

        else:
            if is_executable_path(path_dirs, command):
                run_external_command(
                    command, args, redirection_type, redirection_path, redirection_mode
                )
            else:
                output(
                    f"{command}: command not found",
                    "stderr",
                    redirection_type,
                    redirection_path,
                    redirection_mode,
                )
    return


if __name__ == "__main__":
    main()
