#!/usr/bin/env -S python3 -BOO
import enum
import os
import re
import subprocess as sp
import sys

RC_NO_INTERNET_CONN = enum.auto()
RC_CANT_FETCH       = enum.auto()
RC_CANT_GET_OLD_REV = enum.auto()
RC_CANT_GET_NEW_REV = enum.auto()


def run_get_stdout(cmd: list[str] | str, stdin: str | bytes | None = None) -> sp.CompletedProcess:
    return sp.run(
        cmd,
        stdin=stdin,
        stdout=sp.PIPE,
        stderr=sp.DEVNULL,
        text=True,
        check=False,
    )


def ask(prompt: str, default: bool = True) -> bool | None:
    print(prompt, end=" ([y]/n): ")
    choice = input()
    if choice == "":
        return default
    if choice.lower() in ("y", "yes"):
        return True
    elif choice.lower() in ("n", "no"):
        return False


def info(msg: str) -> None:
    print(f"I: {msg}", file=sys.stderr)


def warn(msg: str) -> None:
    print(f"W: {msg}", file=sys.stderr)


def error(msg: str) -> None:
    print(f"E: {msg}", file=sys.stderr)


def main() -> None:
    # connectivity check
    connectivity_check_cmd = [
        "curl",
        "-s",
        "--head",
        "--request",
        "GET",
        "https://www.google.com",
        "--max-time",
        "5",
    ]
    if sp.run(connectivity_check_cmd, stderr=sp.DEVNULL, stdout=sp.DEVNULL, check=False).returncode != 0:
        error("connect to the internet, dumbass")
        sys.exit(RC_NO_INTERNET_CONN)
    info("internet connection available")

    # print("BEHOLD! THE GREATEST SCRIPT TO EVER GRACE THIS PLANET IS HERE!")

    for item in os.scandir(os.path.expanduser("~/AUR/")):
        if not item.is_dir():
            continue
        os.chdir(item.path)
        pkg = item.name
        info(f"package: {pkg}")

        # get old rev
        old_rev = run_get_stdout(["git", "rev-parse", "HEAD"])
        if old_rev.returncode != 0:
            error("cannot retrieve old rev")
            continue
        old_rev = old_rev.stdout.strip()
        info(f"old rev: {old_rev}")

        # fetch changes
        if sp.run(["git", "fetch", "--quiet"], check=False).returncode:
            error("cannot fetch")
            continue

        # get new rev
        new_rev = run_get_stdout(["git", "rev-parse", "@{u}"])
        if new_rev.returncode != 0:
            error("cannot retrieve new rev")
            continue
        new_rev = new_rev.stdout.strip()
        info(f"new rev: {new_rev}")

        #####

        if old_rev == new_rev:
            installed_ver = run_get_stdout(["pacman", "-Q", pkg])
            if installed_ver.returncode != 0:
                error("package not installed")
                continue
            installed_ver = re.search(r"^[^\s]+\s(.+)$", installed_ver.stdout)
            if installed_ver is None:
                error("cannot parse package search output")
                continue
            installed_ver = installed_ver.group(1)
            info(f"installed version: {installed_ver}")

            # get PKGBUILD
            PKGBUILD_info = run_get_stdout(["makepkg", "--printsrcinfo"])
            if PKGBUILD_info.returncode != 0:
                error("cannot retrieve pkgver...")
                continue
            PKGBUILD_info = PKGBUILD_info.stdout
            # get pkgver from PKGBUILD
            pkgver_matches = re.search(r"^\s+pkgver\s=\s(.+)$", PKGBUILD_info, re.MULTILINE)
            if pkgver_matches is None:
                error("cannot parse pkgver...")
                continue
            info(f"pkgver: {pkgver_matches.group(1)}")
            # get pkgrel from PKGBUILD
            pkgrel_matches = re.search(r"^\s+pkgrel\s=\s(.+)$", PKGBUILD_info, re.MULTILINE)
            if pkgrel_matches is None:
                error("cannot retrieve pkgrel...")
                continue
            info(f"pkgrel: {pkgrel_matches.group(1)}")


if __name__ == "__main__":
    main()
