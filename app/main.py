import os
import subprocess
import sys
from typing import Callable


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


def extract_stdout_redirection(args: list[str]) -> tuple[list[str], str | None]:
    stdout_redirection_tokens: list[str] = ["1>", ">"]
    result_args: list[str] = []
    stdout_file: str | None = None

    for idx, arg in enumerate(args):
        if arg not in stdout_redirection_tokens:
            if idx != 0:
                if args[idx - 1] in stdout_redirection_tokens:
                    stdout_file: str = arg
                    break
                else:
                    result_args.append(arg)
            else:
                result_args.append(arg)
        else:
            continue

    return (result_args, stdout_file)


def is_executable_path(path_dirs: list[str], executable: str) -> bool:
    found = False
    for path_dir in path_dirs:
        full_path: str = os.path.join(path_dir, executable)  # pyright: ignore
        if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
            found = True
            break

    return found


def main() -> None:

    def builtin_echo(args: list[str], stdout_file: str | None) -> None:
        if stdout_file:
            with open(stdout_file, "w") as file:
                file.write(" ".join(args) + "\n")
        else:
            print(" ".join(args))

    def builtin_type(args: list[str], stdout_file: str | None) -> None:
        if args:
            arg1: str = args[0]

            if arg1 in BUILTINS.keys():
                if stdout_file:
                    with open(stdout_file, "w") as file:
                        file.write(f"{arg1} is a shell builtin\n")
                else:
                    print(f"{arg1} is a shell builtin")

            else:
                found: bool = False

                for path_dir in path_dirs:
                    full_path: str = os.path.join(path_dir, " ".join(args))

                    if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                        if stdout_file:
                            with open(stdout_file, "w") as file:
                                file.write(f"{arg1} is {full_path}\n")
                                break
                        else:
                            print(f"{arg1} is {full_path}")
                            found = True
                            break

                if not found:
                    print(f"{arg1}: not found")
        else:
            print("type: no argument given")

    def builtin_pwd(args: list[str], stdout_file: str | None) -> None:
        pwd_path: str = os.getcwd()
        if stdout_file:
            with open(stdout_file, "w") as file:
                file.write(pwd_path)
        else:
            print(pwd_path)

    def builtin_cd(args: list[str], stdout_file: str | None) -> None:
        if args:
            new_dir: str = args[0]
            if new_dir == "~":
                os.chdir(os.path.expanduser("~"))
            elif not os.path.exists(new_dir) and new_dir != "~":
                print(f"cd: {new_dir}: No such file or directory")
            else:
                os.chdir(new_dir)

    def builtin_exit(args: list[str], stdout_file: str | None) -> None:
        sys.exit()

    BUILTINS: dict[str, Callable[[list[str], str | None], None]] = {
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

        args, stdout_file = extract_stdout_redirection(raw_args)

        if command in BUILTINS:
            BUILTINS[command](args, stdout_file)

        else:
            if command not in BUILTINS:
                if is_executable_path(path_dirs, command):
                    if stdout_file:
                        with open(stdout_file, "w") as file:
                            subprocess.run([command] + args, stdout=file)
                    else:
                        subprocess.run([command] + args)
                else:
                    print(f"{command}: command not found")
    return


if __name__ == "__main__":
    main()
