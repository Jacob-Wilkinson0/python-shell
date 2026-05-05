import os
import subprocess
import sys
from collections.abc import Callable


def parse_tokens(raw_args: str) -> list[str]:
    curr: list[str] = []
    arg_list: list[str] = []

    in_single_quote: bool = False
    in_double_quote: bool = False
    is_escape: bool = False

    i = 0
    length_of_raw_args = len(raw_args)

    while i < length_of_raw_args:
        char = raw_args[i]

        if is_escape:
            curr.append(char)
            is_escape = False
            i += 1
            continue

        if in_single_quote:
            if char == "'":
                in_single_quote = False
            else:
                curr.append(char)
            i += 1
            continue

        if in_double_quote:
            if char == "\\":
                is_escape = True
            elif char == '"':
                in_double_quote = False
            else:
                curr.append(char)
            i += 1
            continue

        if char == "\\":
            is_escape = True
        elif char == "'":
            in_single_quote = True
        elif char == '"':
            in_double_quote = True
        elif char.isspace():
            if curr:
                arg_list.append("".join(curr))
                curr.clear()
            while i < length_of_raw_args and raw_args[i].isspace():
                i += 1
            continue
        else:
            curr.append(char)

        i += 1

    if is_escape:
        curr.append("\\")

    if curr:
        arg_list.append("".join(curr))

    if in_single_quote:
        print("error: quotation not closed")
    if in_double_quote:
        print("error: quotation not closed")

    return arg_list


def extract_redirection(
    args: list[str],
) -> tuple[list[str], dict[str | None, str | None]]:

    stdout_redirect_tokens: list[str] = ["1>", ">"]
    stderr_redirect_tokens: list[str] = ["2>"]
    result_args: list[str] = []
    redirection_type: str | None = None
    redirection_file: str | None = None
    redirection_info: dict[str | None, str | None] = {}

    for idx, arg in enumerate(args):
        if arg not in stdout_redirect_tokens and arg not in stderr_redirect_tokens:
            if idx != 0:
                if args[idx - 1] in stdout_redirect_tokens:
                    redirection_type = "stdout"
                    redirection_file = arg
                    break
                elif args[idx - 1] in stderr_redirect_tokens:
                    redirection_type = "stderr"
                    redirection_file = arg
                    break
                else:
                    result_args.append(arg)
            else:
                result_args.append(arg)
        else:
            continue

    redirection_info[redirection_type] = redirection_file

    return (result_args, redirection_info)


def is_executable_path(path_dirs: list[str], executable: str) -> bool:
    found = False
    for path_dir in path_dirs:
        full_path: str = os.path.join(path_dir, executable)  # pyright: ignore
        if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
            found = True
            break

    return found


def main() -> None:

    def output(
        message: str,
        stream: str,
        redirect_type: str | None,
        redirect_path: str | None,
    ) -> None:
        out = sys.stderr if stream == "stderr" else sys.stdout
        if redirect_type == stream and redirect_path:
            with open(redirect_path, "w") as f:
                print(message, file=f)
        else:
            print(message, file=out)

    def builtin_echo(
        args: list[str], redirection: tuple[str | None, str | None]
    ) -> None:

        redirect_type, redirect_path = redirection

        output(" ".join(args), "stdout", redirect_type, redirect_path)

        if redirect_type == "stderr" and redirect_path:
            with open(redirect_path, "w"):
                pass

    def builtin_type(
        args: list[str], redirection: tuple[str | None, str | None]
    ) -> None:

        redirect_type, redirect_path = redirection

        if not args:
            output("type: no argument given", "stderr", redirect_type, redirect_path)
            return

        arg1: str = args[0]

        if arg1 in BUILTINS:
            output(f"{arg1} is a shell builtin", "stdout", redirect_type, redirect_path)
            return

        for path_dir in path_dirs:
            full_path: str = os.path.join(path_dir, " ".join(args))

            if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                output(f"{arg1} is {full_path}", "stdout", redirect_type, redirect_path)
                return

        output(f"{arg1}: not found", "stderr", redirect_type, redirect_path)

    def builtin_pwd(
        args: list[str], redirection: tuple[str | None, str | None]
    ) -> None:

        redirect_type, redirect_path = redirection
        output(os.getcwd(), "stdout", redirect_type, redirect_path)

    def builtin_cd(args: list[str], redirection: tuple[str | None, str | None]) -> None:

        redirect_type, redirect_path = redirection

        if args:
            new_dir: str = args[0]
            if new_dir == "~":
                os.chdir(os.path.expanduser("~"))
            elif not os.path.exists(new_dir) and new_dir != "~":
                output(
                    f"cd: {new_dir}: No such file or directory",
                    "stderr",
                    redirect_type,
                    redirect_path,
                )
            else:
                os.chdir(new_dir)

    def builtin_exit(
        args: list[str], redirection: tuple[str | None, str | None]
    ) -> None:
        sys.exit()

    BUILTINS: dict[str, Callable[[list[str], tuple[str | None, str | None]], None]] = {
        "echo": builtin_echo,
        "exit": builtin_exit,
        "type": builtin_type,
        "pwd": builtin_pwd,
        "cd": builtin_cd,
    }

    path: str = os.environ.get("PATH", "")
    path_dirs: list[str] = path.split(os.pathsep)

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

        args, redirection_info = extract_redirection(raw_args)

        redirection: tuple[str | None, str | None] = next(
            iter(redirection_info.items()), (None, None)
        )

        redirect_type, redirect_path = redirection

        if command in BUILTINS:
            BUILTINS[command](args, redirection)

        else:
            if is_executable_path(path_dirs, command):
                if redirect_type == "stdout" and redirect_path:
                    with open(redirect_path, "w") as file:
                        subprocess.run([command] + args, stdout=file)
                elif redirect_type == "stderr" and redirect_path:
                    with open(redirect_path, "w") as file:
                        subprocess.run([command] + args, stderr=file)
                else:
                    subprocess.run([command] + args)
            else:
                output(
                    f"{command}: command not found",
                    "stderr",
                    redirect_type,
                    redirect_path,
                )
    return


if __name__ == "__main__":
    main()
