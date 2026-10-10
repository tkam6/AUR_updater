#!/usr/bin/env -S python3 -BOO
import enum
import os
import re
import shlex
import subprocess as sp
import sys

ANSI_RESET = "\x1b[0m"
ANSI_BOLD = "\x1b[1m"
ANSI_BLUE_4 = "\x1b[94m"
ANSI_CYAN_4 = "\x1b[96m"
ANSI_GREEN_4 = "\x1b[92m"
ANSI_RED_4 = "\x1b[91m"
ANSI_YELLOW_4 = "\x1b[93m"
ANSI_BOLD_RED_4 = ANSI_BOLD + ANSI_RED_4
ANSI_BOLD_YELLOW_4 = ANSI_BOLD + ANSI_YELLOW_4

class LogLvls(enum.IntEnum):
    DEBUG = enum.auto(0)
    WARN  = enum.auto()
    ERROR = enum.auto()


LOG_LVL = LogLvls.WARN


class RC(enum.IntEnum):
    ALL_GOOD         = enum.auto(0)
    NO_INTERNET_CONN = enum.auto()
    CANT_FETCH       = enum.auto()
    CANT_GET_OLD_REV = enum.auto()
    CANT_GET_NEW_REV = enum.auto()


def parse_argv(argv: list[str]) -> None:
    pass


def run_get_none(
    cmd: list[str],
    cwd: str | None = None,
    stdin: str | None = None,
) -> sp.CompletedProcess:
    return sp.run(
        cmd,
        cwd=cwd,
        input=stdin,
        stdout=sp.DEVNULL,
        stderr=sp.DEVNULL,
        text=True,
        check=False,
    )


def run_get_stdout(
    cmd: list[str],
    cwd: str | None = None,
    stdin: str | None = None,
) -> sp.CompletedProcess:
    return sp.run(
        cmd,
        cwd=cwd,
        input=stdin,
        stdout=sp.PIPE,
        stderr=sp.DEVNULL,
        text=True,
        check=False,
    )


def run_get_stderr(
    cmd: list[str],
    cwd: str | None = None,
    stdin: str | None = None,
) -> sp.CompletedProcess:
    return sp.run(
        cmd,
        cwd=cwd,
        input=stdin,
        stdout=sp.DEVNULL,
        stderr=sp.PIPE,
        text=True,
        check=False,
    )


def run_get_both(
    cmd: list[str],
    cwd: str | None = None,
    stdin: str | None = None,
) -> sp.CompletedProcess:
    return sp.run(
        cmd,
        cwd=cwd,
        input=stdin,
        capture_output=True,
        text=True,
        check=False,
    )


def ask(prompt: str, default: bool = True) -> tuple[bool | None, str]:
    print(prompt, end=" ([y]/n): ")
    choice = input()
    if choice == "":
        return default, choice
    if choice.lower() in ("y", "yes"):
        return True, choice
    elif choice.lower() in ("n", "no"):
        return False, choice
    return None, choice


def dump_debug_stdout_stderr(
    cmd: list[str],
    completed_proc: sp.CompletedProcess,
    pkg_name: str | None = None,
) -> None:
    stdout = (completed_proc.stdout or "").strip()
    stderr = (completed_proc.stderr or "").strip()
    debug(f"{shlex.join(cmd)} STDOUT:{f"\n{stdout}" if stdout else ""}", pkg_name=pkg_name)
    debug(f"{shlex.join(cmd)} STDERR:{f"\n{stderr}" if stderr else ""}", pkg_name=pkg_name)


def debug(msg: str, pkg_name: str, start: str = "", end: str = "\n") -> None:
    if LOG_LVL <= LogLvls.DEBUG:
        print(f"{start}{ANSI_BOLD}D:{ANSI_RESET} ({pkg_name}) {msg}", end=end, file=sys.stderr)


def warn(msg: str, pkg_name: str | None = None, start: str = "", end: str = "\n") -> None:
    if LOG_LVL <= LogLvls.WARN:
        print(
            f"{start}{ANSI_BOLD_YELLOW_4}W:{ANSI_RESET}{"" if pkg_name is None else f" {pkg_name}:"} {msg}",
            end=end,
            file=sys.stderr,
        )


def error(msg: str, pkg_name: str | None = None, start: str = "", end: str = "\n") -> None:
    if LOG_LVL <= LogLvls.ERROR:
        print(
            f"{start}{ANSI_BOLD_RED_4}E:{ANSI_RESET}{"" if pkg_name is None else f" {pkg_name}:"} {msg}",
            end=end,
            file=sys.stderr,
        )


def info(msg: str, pkg_name: str | None = None, start: str = "", end: str = "\n") -> None:
    print(
        f"{start}{ANSI_BOLD}I:{ANSI_RESET}{"" if pkg_name is None else f" {pkg_name}:"} {msg}",
        end=end,
    )


def get_installed_ver(pkg_name: str, item_path: str) -> str | None:
    cmd = ["pacman", "-Q", pkg_name]
    installed_ver = run_get_both(cmd, cwd=item_path)
    if installed_ver.returncode != 0:
        dump_debug_stdout_stderr(cmd, installed_ver, pkg_name)
        error("package not installed (or pacman failed to get package)", pkg_name)
        return
    installed_ver = re.search(r"^[^\s]+\s(.+)$", installed_ver.stdout)
    if installed_ver is None:
        error("cannot parse package search output", pkg_name)
        return
    installed_ver = installed_ver.group(1)
    debug(f"installed version: {installed_ver}", pkg_name)
    return installed_ver


def get_old_ver(pkg_name: str, item_path: str) -> str | None:
    cmd = ["git", "rev-parse", "HEAD"]
    old_rev = run_get_both(cmd, cwd=item_path)
    if old_rev.returncode != 0:
        dump_debug_stdout_stderr(cmd, old_rev, pkg_name)
        error("cannot retrieve old rev", pkg_name)
        return
    old_rev = old_rev.stdout.strip()
    debug(f"old rev: {old_rev}", pkg_name)
    return old_rev


def get_new_ver(pkg_name: str, item_path: str) -> str | None:
    cmd = ["git", "rev-parse", "@{u}"]
    new_rev = run_get_both(cmd, cwd=item_path)
    if new_rev.returncode != 0:
        dump_debug_stdout_stderr(cmd, new_rev, pkg_name)
        error("cannot retrieve new rev", pkg_name)
        return
    new_rev = new_rev.stdout.strip()
    debug(f"new rev: {new_rev}", pkg_name)
    return new_rev


def get_epoch_pkgver_pkgrel(pkg_name: str, pkgbuild_info: str) -> tuple[str | None, str, str] | None:
    epoch_matches = re.search(r"^\s*epoch\s=\s(.+)$", pkgbuild_info, re.MULTILINE)
    if epoch_matches is None:
        epoch = None
    else:
        epoch = epoch_matches.group(1)
    debug(f"epoch: {epoch}", pkg_name)

    pkgver_matches = re.search(r"^\s*pkgver\s=\s(.+)$", pkgbuild_info, re.MULTILINE)
    if pkgver_matches is None:
        error("cannot parse for pkgver", pkg_name)
        return
    pkgver = pkgver_matches.group(1)
    debug(f"pkgver: {pkgver}", pkg_name)

    pkgrel_matches = re.search(r"^\s*pkgrel\s=\s(.+)$", pkgbuild_info, re.MULTILINE)
    if pkgrel_matches is None:
        error("cannot parse for pkgrel", pkg_name)
        return
    pkgrel = pkgrel_matches.group(1)
    debug(f"pkgrel: {pkgrel}", pkg_name)

    return (epoch, pkgver, pkgrel)


def pulled_but_not_updated(pkg_name: str, item_path: str) -> None:
    info("pulled but not updated", pkg_name)
    do_build_install = ask("build and install?")
    if do_build_install[0] is None:
        error(f"skipping (invalid value: '{do_build_install[1]!r}')", pkg_name)
        return
    if not do_build_install[0]:
        error("skipping (declined)", pkg_name)
        return

    sp.run(["makepkg", "-sic"], cwd=item_path, check=False)


def main() -> None:
    # connectivity check
    # connectivity_check_cmd = [
    #     "curl",
    #     "-s",
    #     "--head",
    #     "--request",
    #     "GET",
    #     "https://www.google.com",
    #     "--max-time",
    #     "5",
    # ]
    # if sp.run(connectivity_check_cmd, stderr=sp.DEVNULL, stdout=sp.DEVNULL, check=False).returncode != 0:
    #     error("connect to the internet, dumbass")
    #     sys.exit(RC.NO_INTERNET_CONN)
    # debug("internet connection available")

    # print("BEHOLD! THE GREATEST SCRIPT TO EVER GRACE THIS PLANET IS HERE!")

    for item in os.scandir(os.path.expanduser("~/AUR/")):
        if not item.is_dir():
            continue
        pkg_name = item.name
        item_path = item.path
        debug(f"package name: {pkg_name}", pkg_name)

        installed_ver = get_installed_ver(pkg_name, item_path)
        if installed_ver is None:
            continue
        # get old rev
        old_rev = get_old_ver(pkg_name, item_path)
        if old_rev is None:
            continue
        # fetch changes
        git_fetch_cmd = ["git", "fetch", "--quiet"]
        git_fetch = run_get_both(git_fetch_cmd, cwd=item_path)
        if git_fetch.returncode:
            dump_debug_stdout_stderr(git_fetch_cmd, git_fetch, pkg_name)
            error("cannot fetch", pkg_name)
            continue
        # get new rev
        new_rev = get_new_ver(pkg_name, item_path)
        if new_rev is None:
            continue

        # VERSION IS SAME AFTER FETCHING
        if old_rev == new_rev:
            # get PKGBUILD
            makepkg_printsrcinfo_cmd = ["makepkg", "--printsrcinfo"]
            pkgbuild_info = run_get_both(makepkg_printsrcinfo_cmd, cwd=item_path)
            if pkgbuild_info.returncode != 0:
                dump_debug_stdout_stderr(makepkg_printsrcinfo_cmd, pkgbuild_info, pkg_name)
                error("cannot retrieve pkgver", pkg_name)
                continue
            pkgbuild_info = pkgbuild_info.stdout
            # get epoch, pkgver, pkgrel
            tmp = get_epoch_pkgver_pkgrel(pkg_name, pkgbuild_info)
            if tmp is None:
                continue
            epoch, pkgver, pkgrel = tmp
            ver_from_makepkg = f"{pkgver}-{pkgrel}" if epoch is None else f"{epoch}:{pkgver}-{pkgrel}"
            debug(f"version string from makepkg: {ver_from_makepkg}", pkg_name)

            if installed_ver == ver_from_makepkg:
                info("skipping (up-to-date)", pkg_name)
                continue

            pulled_but_not_updated(pkg_name, item_path)
            continue

        # UPDATES AVAILABLE
        info("updates available", pkg_name)
        do_show_diff = ask("show diff?")
        if do_show_diff[0] is None:
            error(f"continue (invalid show diff value: '{do_show_diff[1]!r}')", pkg_name)
        if do_show_diff[0]:
            sp.run(["git", "diff", "HEAD", "@{u}"], cwd=item_path, check=False)

        do_pull_build_install = ask("pull, build and install?")
        if do_pull_build_install[0] is None:
            error(f"skipping (invalid value: '{do_pull_build_install[1]!r}')", pkg_name)
            continue
        if not do_pull_build_install[0]:
            error("skipping (declined)", pkg_name)
            continue

        sp.run(["git", "reset", "--hard", "@{u}"], cwd=item_path, check=False)
        sp.run(["git", "clean", "-fd"], cwd=item_path, check=False)
        sp.run(["makepkg", "-sic"], cwd=item_path, check=False)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        error("interrupt received, exiting", start="\n")
