#!/usr/bin/env python3
"""Create and safely remove private X Article publishing workspaces."""

import argparse
import os
import shutil
import stat
import tempfile
from pathlib import Path
from typing import Mapping


PREFIX = ".x-article-"
MARKER = ".x-article-workspace"
MARKER_CONTENT = "managed by x-article-chrome-publisher\n"


class WorkspaceError(ValueError):
    """Raised when a path is not a managed X Article workspace."""


def workspace_parent(
    platform_name: str | None = None,
    environ: Mapping[str, str] | None = None,
) -> Path:
    """Return a user-private temporary root for the active platform."""
    platform_name = platform_name or os.name
    environ = environ or os.environ

    if platform_name == "nt":
        local_app_data = environ.get("LOCALAPPDATA")
        if not local_app_data:
            raise WorkspaceError("LOCALAPPDATA is required for a private Windows workspace")
        parent = Path(local_app_data).expanduser().resolve() / "Temp"
        parent.mkdir(parents=True, exist_ok=True)
        return parent.resolve()

    return Path(tempfile.gettempdir()).resolve()


def create_workspace() -> Path:
    """Create a private per-run workspace in the user temporary root."""
    workspace = Path(tempfile.mkdtemp(prefix=PREFIX, dir=workspace_parent())).resolve()
    try:
        workspace.chmod(0o700)
        marker_fd = os.open(workspace / MARKER, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(marker_fd, "w", encoding="utf-8") as marker_file:
            marker_file.write(MARKER_CONTENT)
    except Exception:
        shutil.rmtree(workspace, ignore_errors=True)
        raise
    return workspace


def validate_workspace(path: str | Path) -> Path:
    """Return a managed workspace path or reject an unsafe cleanup target."""
    candidate = Path(path).expanduser()
    if candidate.is_symlink():
        raise WorkspaceError("workspace path must not be a symlink")

    try:
        workspace = candidate.resolve(strict=True)
    except FileNotFoundError as exc:
        raise WorkspaceError("workspace does not exist") from exc

    if workspace.parent != workspace_parent() or not workspace.name.startswith(PREFIX):
        raise WorkspaceError("workspace must be a direct managed child of the private root")

    marker = workspace / MARKER
    try:
        marker_stat = marker.lstat()
    except FileNotFoundError as exc:
        raise WorkspaceError("workspace marker is missing") from exc
    if not stat.S_ISREG(marker_stat.st_mode):
        raise WorkspaceError("workspace marker must be a regular file")
    if hasattr(os, "getuid") and marker_stat.st_uid != os.getuid():
        raise WorkspaceError("workspace marker is not owned by the current user")
    if marker.read_text(encoding="utf-8") != MARKER_CONTENT:
        raise WorkspaceError("workspace marker content is invalid")

    return workspace


def cleanup_workspace(path: str | Path) -> None:
    """Remove a validated managed workspace without following directory symlinks."""
    workspace = validate_workspace(path)
    shutil.rmtree(workspace)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser(
        "create",
        help="create a private workspace and print its path",
    )
    cleanup_parser = subparsers.add_parser("cleanup", help="remove a managed workspace")
    cleanup_parser.add_argument("path", help="path printed by the create command")
    args = parser.parse_args()

    if args.command == "create":
        print(create_workspace())
    else:
        cleanup_workspace(args.path)


if __name__ == "__main__":
    main()
