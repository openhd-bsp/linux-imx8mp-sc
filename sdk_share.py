#!/usr/bin/env python3

from __future__ import annotations

import argparse
import base64
import fnmatch
import getpass
import json
import os
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path


THRESHOLD_BYTES = 50 * 1024 * 1024
PART_SIZE_BYTES = 50 * 1024 * 1024
INDEX_FILE = "bigFileIndex.txt"
GITIGNORE_FILE = ".gitignore"
MANAGED_START = "# sdk-share managed start"
MANAGED_END = "# sdk-share managed end"
PART_SUFFIX = ".sdkshare.tar.part-"
TAR_SUFFIX = ".sdkshare.tar"
STATE_DIR = Path.home() / ".config" / "sdk-share"
STATE_FILE = STATE_DIR / "config.json"
CLEAN_PATTERNS = (
    "tmp",
    "cache",
    "sstate-cache",
    "tmp-glibc",
    "tmp-eglibc",
    "deploy",
    "deploy-*",
)
COPY_SKIP_TOP_LEVEL = {".git", ".repo"}
SKIP_PATH_PATTERNS = (
    ".git/*",
    ".repo/*",
    f"*/{INDEX_FILE}",
    f"*{TAR_SUFFIX}",
    f"*{PART_SUFFIX}*",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare a Yocto SDK tree for Git sharing and restore it later."
    )
    parser.add_argument(
        "mode",
        choices=("prepare", "unpack", "transfer", "transfer-batched"),
        help="prepare removes disposable build output and packages large files; unpack restores them; transfer stages and pushes a clean copy; transfer-batched pushes in size-limited batches",
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="repository root to process (default: current directory)",
    )
    parser.add_argument(
        "--threshold-mb",
        type=int,
        default=50,
        help="size threshold in MB for packaging (default: 50)",
    )
    parser.add_argument(
        "--part-size-mb",
        type=int,
        default=50,
        help="split size in MB for archive parts (default: 50)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print planned actions without modifying the tree",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite existing restored files during unpack",
    )
    parser.add_argument(
        "--target-repo",
        help="GitHub repository URL to push the staged copy to",
    )
    parser.add_argument(
        "--github-token",
        help="GitHub personal access token; if omitted, prompt securely or reuse saved config",
    )
    parser.add_argument(
        "--tmp-root",
        default="/tmp",
        help="temporary root used for the clean transfer copy (default: /tmp)",
    )
    parser.add_argument(
        "--push-batch-mb",
        type=int,
        default=500,
        help="maximum approximate payload size per push for transfer-batched (default: 500)",
    )
    parser.add_argument(
        "--remove-build-dirs",
        action="store_true",
        help="remove top-level build directories from the staged upload copy before packaging and push",
    )
    parser.add_argument(
        "--remove-source-build-artifacts",
        action="store_true",
        help="remove regenerable build artifacts such as build-*/tmp from the live workspace before creating the staged upload copy",
    )
    return parser.parse_args()


def human_size(size: int) -> str:
    units = ("B", "KB", "MB", "GB", "TB")
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f}{unit}"
        value /= 1024
    return f"{size}B"


def print_header(title: str) -> None:
    line = "=" * len(title)
    print(line)
    print(title)
    print(line)


def print_welcome(
    mode: str,
    repo_root: Path,
    threshold_bytes: int,
    part_size_bytes: int,
    remove_build_dirs: bool,
    remove_source_build_artifacts: bool,
) -> None:
    print_header("SDK Share Utility")
    print(f"Repository root : {repo_root}")
    print(f"Selected mode   : {mode}")
    print(f"Large file rule : files larger than {human_size(threshold_bytes)}")
    print(f"Split part size : {human_size(part_size_bytes)}")
    print(f"Remove build dir: {'yes' if remove_build_dirs else 'no'}")
    print(f"Clean source tmp : {'yes' if remove_source_build_artifacts else 'no'}")
    print()
    if mode == "prepare":
        print("This mode prepares the repository for transfer.")
        print("It removes disposable Yocto output, indexes large files,")
        print("replaces those files with split tar parts, and updates .gitignore.")
    elif mode == "unpack":
        print("This mode restores previously packed large files.")
        print("It reads bigFileIndex.txt and recreates each original file")
        print("from the split tar parts stored next to it.")
    else:
        print("This mode creates a clean temporary copy of the repository,")
        print("prepares that staged copy for sharing, and pushes it to GitHub.")
        if mode == "transfer-batched":
            print("The upload is split into multiple Git push sessions,")
            print("each capped at the configured batch size.")
        print("It also saves the target repository URL and GitHub token")
        print("outside the repository so they are not uploaded.")
    print()


class ProgressBar:
    def __init__(self, total: int, label: str) -> None:
        self.total = max(total, 1)
        self.label = label
        self.current = 0
        self.last_rendered = -1

    def update(self, current: int, detail: str = "") -> None:
        self.current = max(0, min(current, self.total))
        percent = int((self.current * 100) / self.total)
        if percent == self.last_rendered and not detail:
            return
        self.last_rendered = percent
        filled = int((self.current * 30) / self.total)
        bar = "#" * filled + "-" * (30 - filled)
        suffix = f" {detail}" if detail else ""
        sys.stdout.write(
            f"\r{self.label}: [{bar}] {percent:3d}% ({self.current}/{self.total}){suffix}"
        )
        sys.stdout.flush()

    def finish(self, detail: str = "") -> None:
        self.update(self.total, detail)
        sys.stdout.write("\n")
        sys.stdout.flush()


def prompt_value(prompt: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{prompt}{suffix}: ").strip()
    return value or (default or "")


def load_state() -> dict[str, str]:
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid state file {STATE_FILE}: {exc}") from exc


def save_state(state: dict[str, str]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    os.chmod(STATE_FILE, stat.S_IRUSR | stat.S_IWUSR)


def resolve_transfer_credentials(
    target_repo: str | None, github_token: str | None
) -> tuple[str, str]:
    state = load_state()
    print("Resolving transfer settings")
    resolved_repo = target_repo or prompt_value("Target GitHub repository URL", state.get("target_repo"))
    if not resolved_repo:
        raise RuntimeError("Target repository URL is required")

    token = github_token
    if not token:
        token = getpass.getpass("GitHub token (leave empty to reuse saved token): ").strip()
    if not token:
        token = state.get("github_token", "")
    if not token:
        raise RuntimeError("GitHub token is required")

    save_state({"target_repo": resolved_repo, "github_token": token})
    print(f"Target repository : {resolved_repo}")
    print(f"Saved credentials : {STATE_FILE}")
    print()
    return resolved_repo, token


def should_skip(rel_path: str) -> bool:
    posix_path = rel_path.replace(os.sep, "/")
    return any(fnmatch.fnmatch(posix_path, pattern) for pattern in SKIP_PATH_PATTERNS)


def remove_path(path: Path, dry_run: bool) -> None:
    if dry_run:
        print(f"[dry-run] remove {path}")
        return
    if path.is_symlink() or path.is_file():
        path.unlink(missing_ok=True)
        return
    shutil.rmtree(path, ignore_errors=True)


def clean_generated_content(repo_root: Path, dry_run: bool) -> None:
    candidates: set[Path] = set()

    for pattern in CLEAN_PATTERNS:
        for path in repo_root.glob(pattern):
            candidates.add(path)
        for path in repo_root.glob(f"build-*/{pattern}"):
            candidates.add(path)

    sorted_candidates = sorted(candidates)
    print(f"Cleaning generated content: {len(sorted_candidates)} path(s) selected")
    progress = ProgressBar(len(sorted_candidates), "Removing generated content")
    removed = 0
    for path in sorted_candidates:
        if not path.exists():
            removed += 1
            progress.update(removed)
            continue
        if path.match("build-*/conf") or path.match("build-*/conf/*"):
            removed += 1
            progress.update(removed)
            continue
        print(f"Cleaning {path.relative_to(repo_root)}")
        remove_path(path, dry_run)
        removed += 1
        progress.update(removed, path.relative_to(repo_root).as_posix())
    progress.finish("done")
    print()


def build_artifact_paths(repo_root: Path) -> list[Path]:
    candidates: set[Path] = set()
    for pattern in CLEAN_PATTERNS:
        for path in repo_root.glob(f"build-*/{pattern}"):
            candidates.add(path)
    return sorted(path for path in candidates if path.exists())


def remove_build_artifacts(repo_root: Path, dry_run: bool, label: str) -> None:
    paths = build_artifact_paths(repo_root)
    print(f"{label}: {len(paths)} path(s) selected")
    progress = ProgressBar(len(paths), label)
    for index, path in enumerate(paths, start=1):
        print(f"Removing {path.relative_to(repo_root)}")
        remove_path(path, dry_run)
        progress.update(index, path.relative_to(repo_root).as_posix())
    progress.finish("done")
    print()


def collect_large_files(repo_root: Path, threshold_bytes: int) -> list[tuple[int, str]]:
    results: list[tuple[int, str]] = []
    print(f"Scanning for files larger than {human_size(threshold_bytes)}")
    command = [
        "find",
        str(repo_root),
        "(",
        "-path",
        str(repo_root / ".git"),
        "-o",
        "-path",
        str(repo_root / ".repo"),
        ")",
        "-prune",
        "-o",
        "-type",
        "f",
        "-size",
        f"+{threshold_bytes}c",
        "-printf",
        "%s\t%P\n",
    ]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        size_text, rel_path = line.split("\t", 1)
        if should_skip(rel_path):
            continue
        results.append((int(size_text), rel_path))
    print(f"Large-file scan completed: found {len(results)} file(s)")
    print()
    results.sort(key=lambda item: item[1])
    return results


def write_index(repo_root: Path, entries: list[tuple[int, str]], dry_run: bool) -> None:
    content = ["# size_bytes\tpath"]
    content.extend(f"{size}\t{rel_path}" for size, rel_path in entries)
    text = "\n".join(content) + "\n"
    index_path = repo_root / INDEX_FILE
    if dry_run:
        print(f"[dry-run] write {index_path}")
        return
    index_path.write_text(text, encoding="utf-8")
    print(f"Wrote large-file index to {index_path}")
    print()


def archive_and_split_file(
    repo_root: Path,
    rel_path: str,
    part_size_bytes: int,
    dry_run: bool,
) -> None:
    source_path = repo_root / rel_path
    tar_path = source_path.with_name(source_path.name + TAR_SUFFIX)
    print(f"Packing {rel_path}")

    if dry_run:
        print(f"[dry-run] create {tar_path.relative_to(repo_root)}")
        print(f"[dry-run] split into {part_size_bytes // (1024 * 1024)}MB parts")
        print(f"[dry-run] remove {rel_path}")
        return

    if tar_path.exists():
        tar_path.unlink()

    for existing_part in sorted(source_path.parent.glob(source_path.name + PART_SUFFIX + "*")):
        existing_part.unlink()

    with tarfile.open(tar_path, "w") as tar:
        tar.add(source_path, arcname=source_path.name)

    total_size = tar_path.stat().st_size
    progress = ProgressBar(total_size, f"Splitting {source_path.name}")
    with tar_path.open("rb") as src:
        part_index = 0
        written = 0
        while True:
            chunk = src.read(part_size_bytes)
            if not chunk:
                break
            part_path = source_path.with_name(
                f"{source_path.name}{PART_SUFFIX}{part_index:03d}"
            )
            with part_path.open("wb") as dst:
                dst.write(chunk)
            written += len(chunk)
            progress.update(written, part_path.name)
            part_index += 1

    progress.finish(f"{part_index} part(s)")
    tar_path.unlink()
    source_path.unlink()
    print(f"Replaced original file with split archive parts for {rel_path}")


def update_gitignore(repo_root: Path, large_files: list[tuple[int, str]], dry_run: bool) -> None:
    gitignore_path = repo_root / GITIGNORE_FILE
    current = ""
    if gitignore_path.exists():
        current = gitignore_path.read_text(encoding="utf-8")

    lines = current.splitlines()
    filtered: list[str] = []
    inside_managed_block = False
    for line in lines:
        stripped = line.strip()
        if stripped == MANAGED_START:
            inside_managed_block = True
            continue
        if stripped == MANAGED_END:
            inside_managed_block = False
            continue
        if not inside_managed_block:
            filtered.append(line)

    large_paths = [rel_path for _, rel_path in large_files]
    managed = [
        MANAGED_START,
        "# Keep original large files out of Git.",
    ]
    managed.extend(large_paths)
    managed.extend(
        [
            "",
            "# Never keep temporary tar files.",
            f"*{TAR_SUFFIX}",
            MANAGED_END,
        ]
    )

    new_content = "\n".join(filtered).rstrip() + "\n\n" + "\n".join(managed) + "\n"
    if dry_run:
        print(f"[dry-run] update {gitignore_path}")
        return
    gitignore_path.write_text(new_content, encoding="utf-8")
    print(f"Updated managed large-file ignore rules in {gitignore_path}")
    print()


def load_index(repo_root: Path) -> list[tuple[int, str]]:
    index_path = repo_root / INDEX_FILE
    if not index_path.exists():
        raise FileNotFoundError(f"Missing {INDEX_FILE} in {repo_root}")

    entries: list[tuple[int, str]] = []
    for line in index_path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        size_text, rel_path = line.split("\t", 1)
        entries.append((int(size_text), rel_path))
    return entries


def unpack_file(repo_root: Path, rel_path: str, dry_run: bool, force: bool) -> None:
    target_path = repo_root / rel_path
    part_paths = sorted(target_path.parent.glob(target_path.name + PART_SUFFIX + "*"))
    if not part_paths:
        print(f"Skipping {rel_path}: no split archive parts found")
        return

    if target_path.exists() and not force:
        print(f"Skipping {rel_path}: file already exists")
        return

    if target_path.exists() and force:
        print(f"Replacing {rel_path}")
        if not dry_run:
            target_path.unlink()
    else:
        print(f"Restoring {rel_path}")

    if dry_run:
        return

    target_path.parent.mkdir(parents=True, exist_ok=True)
    total_size = sum(part_path.stat().st_size for part_path in part_paths)
    progress = ProgressBar(total_size, f"Restoring {target_path.name}")
    with tempfile.NamedTemporaryFile(suffix=TAR_SUFFIX, delete=False) as temp_tar:
        temp_tar_path = Path(temp_tar.name)
        copied = 0
        for part_path in part_paths:
            with part_path.open("rb") as src:
                shutil.copyfileobj(src, temp_tar)
            copied += part_path.stat().st_size
            progress.update(copied, part_path.name)

    try:
        with tarfile.open(temp_tar_path, "r") as tar:
            members = tar.getmembers()
            if len(members) != 1 or members[0].name != target_path.name:
                raise RuntimeError(f"Unexpected archive layout for {rel_path}")
            with tar.extractfile(members[0]) as src, target_path.open("wb") as dst:
                if src is None:
                    raise RuntimeError(f"Archive payload missing for {rel_path}")
                shutil.copyfileobj(src, dst)
    finally:
        temp_tar_path.unlink(missing_ok=True)
    progress.finish("done")
    print(f"Restored original file for {rel_path}")


def prepare(repo_root: Path, threshold_bytes: int, part_size_bytes: int, dry_run: bool) -> None:
    print("Step 1: remove disposable build output")
    clean_generated_content(repo_root, dry_run)
    print("Step 2: scan for large files")
    large_files = collect_large_files(repo_root, threshold_bytes)
    print(f"Found {len(large_files)} file(s) larger than {human_size(threshold_bytes)}")
    for size, rel_path in large_files:
        print(f"  {human_size(size):>8}  {rel_path}")
    print()
    print("Step 3: write index file")
    write_index(repo_root, large_files, dry_run)
    print("Step 4: pack and split large files")
    progress = ProgressBar(len(large_files), "Packing files")
    for index, (_, rel_path) in enumerate(large_files, start=1):
        archive_and_split_file(repo_root, rel_path, part_size_bytes, dry_run)
        progress.update(index, rel_path)
    progress.finish("done")
    print("Step 5: update .gitignore")
    update_gitignore(repo_root, large_files, dry_run)
    print("Prepare mode completed successfully.")


def unpack(repo_root: Path, dry_run: bool, force: bool) -> None:
    print("Reading large-file index and restoring files")
    entries = load_index(repo_root)
    progress = ProgressBar(len(entries), "Unpacking files")
    for index, (_, rel_path) in enumerate(entries, start=1):
        unpack_file(repo_root, rel_path, dry_run, force)
        progress.update(index, rel_path)
    progress.finish("done")
    print("Unpack mode completed successfully.")


def copy_repo_to_stage(repo_root: Path, stage_root: Path, dry_run: bool) -> Path:
    stage_root.mkdir(parents=True, exist_ok=True)
    stage_repo = stage_root / repo_root.name
    if stage_repo.exists():
        raise RuntimeError(f"Stage directory already exists: {stage_repo}")
    print(f"Copying repository to {stage_repo}")
    if dry_run:
        return stage_repo
    stage_repo.mkdir(parents=True, exist_ok=False)
    paths = [
        path
        for path in sorted(repo_root.rglob("*"))
        if path.relative_to(repo_root).parts[0] not in COPY_SKIP_TOP_LEVEL
    ]
    file_paths = [path for path in paths if path.is_file() and not path.is_symlink()]
    progress = ProgressBar(len(file_paths), "Copying stage")

    for path in paths:
        rel_path = path.relative_to(repo_root)
        target = stage_repo / rel_path
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            shutil.copystat(path, target, follow_symlinks=False)
        elif path.is_symlink():
            target.parent.mkdir(parents=True, exist_ok=True)
            os.symlink(os.readlink(path), target)

    copied = 0
    for path in file_paths:
        rel_path = path.relative_to(repo_root)
        target = stage_repo / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        copied += 1
        progress.update(copied, rel_path.as_posix())

    progress.finish(f"{copied} file(s)")
    print(f"Repository copy completed: {stage_repo}")
    print()
    return stage_repo


def remove_stage_build_dirs(stage_repo: Path, dry_run: bool) -> None:
    build_dirs = sorted(
        path for path in stage_repo.iterdir() if path.is_dir() and path.name.startswith("build")
    )
    print(f"Removing staged build directories: {len(build_dirs)} path(s) selected")
    progress = ProgressBar(len(build_dirs), "Removing staged build dirs")
    for index, path in enumerate(build_dirs, start=1):
        print(f"Removing {path.relative_to(stage_repo)} from staged copy")
        remove_path(path, dry_run)
        progress.update(index, path.relative_to(stage_repo).as_posix())
    progress.finish("done")
    print()


def run_git(
    args: list[str],
    cwd: Path,
    env: dict[str, str] | None = None,
    git_config: list[str] | None = None,
) -> None:
    cmd = ["git"]
    config_entries = [f"safe.directory={cwd.resolve()}"]
    config_entries.extend(git_config or [])
    for entry in config_entries:
        cmd.extend(["-c", entry])
    cmd.extend(args)
    subprocess.run(cmd, cwd=cwd, env=env, check=True)


def git_output(
    args: list[str],
    cwd: Path,
    env: dict[str, str] | None = None,
    git_config: list[str] | None = None,
) -> str:
    cmd = ["git"]
    config_entries = [f"safe.directory={cwd.resolve()}"]
    config_entries.extend(git_config or [])
    for entry in config_entries:
        cmd.extend(["-c", entry])
    cmd.extend(args)
    result = subprocess.run(cmd, cwd=cwd, env=env, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def current_branch(repo_root: Path) -> str:
    result = subprocess.run(
        ["git", "-c", f"safe.directory={repo_root.resolve()}", "symbolic-ref", "--short", "HEAD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    branch = result.stdout.strip()
    if branch == "HEAD":
        raise RuntimeError("Cannot transfer from a detached HEAD")
    return branch


def github_auth_header(token: str) -> str:
    payload = base64.b64encode(f"x-access-token:{token}".encode("utf-8")).decode("ascii")
    return f"AUTHORIZATION: basic {payload}"


def init_stage_repository(stage_repo: Path, branch: str, git_env: dict[str, str]) -> None:
    print("Initializing a fresh Git repository in the staged copy")
    run_git(["init", "-q"], stage_repo, git_env)
    run_git(["checkout", "-q", "-b", branch], stage_repo, git_env)
    run_git(["config", "user.name", "SDK Share"], stage_repo, git_env)
    run_git(["config", "user.email", "sdk-share@local"], stage_repo, git_env)
    print()


def staged_repo_files(stage_repo: Path) -> list[tuple[int, str]]:
    files: list[tuple[int, str]] = []
    for path in sorted(stage_repo.rglob("*")):
        if path.relative_to(stage_repo).parts[0] == ".git":
            continue
        if path.is_dir():
            continue
        size = len(os.readlink(path).encode("utf-8")) if path.is_symlink() else path.stat().st_size
        files.append((size, path.relative_to(stage_repo).as_posix()))
    return files


def commit_and_push_all(
    stage_repo: Path,
    resolved_repo: str,
    branch: str,
    git_env: dict[str, str],
    git_config: list[str],
) -> None:
    print("Creating a single Git commit for the staged repository")
    run_git(["remote", "add", "transfer-target", resolved_repo], stage_repo, git_env)
    run_git(["add", "-f", "."], stage_repo, git_env)
    run_git(["commit", "-q", "-m", "Import staged SDK tree"], stage_repo, git_env)
    run_git(
        ["push", "--set-upstream", "transfer-target", f"HEAD:{branch}"],
        stage_repo,
        git_env,
        git_config,
    )
    run_git(["remote", "remove", "transfer-target"], stage_repo, git_env)
    print("Single-session push completed")
    print()


def build_push_batches(stage_repo: Path, batch_limit_bytes: int) -> list[list[str]]:
    batches: list[list[str]] = []
    current_batch: list[str] = []
    current_size = 0
    for size, rel_path in staged_repo_files(stage_repo):
        if current_batch and current_size + size > batch_limit_bytes:
            batches.append(current_batch)
            current_batch = []
            current_size = 0
        current_batch.append(rel_path)
        current_size += size
        if current_size >= batch_limit_bytes:
            batches.append(current_batch)
            current_batch = []
            current_size = 0
    if current_batch:
        batches.append(current_batch)
    return batches


def commit_and_push_in_batches(
    stage_repo: Path,
    resolved_repo: str,
    branch: str,
    git_env: dict[str, str],
    git_config: list[str],
    batch_limit_bytes: int,
) -> None:
    print(f"Creating multiple Git commits with an approximate limit of {human_size(batch_limit_bytes)} per push")
    batches = build_push_batches(stage_repo, batch_limit_bytes)
    print(f"Calculated {len(batches)} push batch(es)")
    print()
    run_git(["remote", "add", "transfer-target", resolved_repo], stage_repo, git_env)
    progress = ProgressBar(len(batches), "Pushing batches")
    for index, batch in enumerate(batches, start=1):
        run_git(["add", "-f", "--", *batch], stage_repo, git_env)
        run_git(
            ["commit", "-q", "-m", f"Import staged SDK tree batch {index}/{len(batches)}"],
            stage_repo,
            git_env,
        )
        push_args = ["push", "transfer-target", f"HEAD:{branch}"]
        if index == 1:
            push_args.insert(1, "--set-upstream")
        run_git(push_args, stage_repo, git_env, git_config)
        progress.update(index, f"batch {index}/{len(batches)}")
    progress.finish("done")
    run_git(["remote", "remove", "transfer-target"], stage_repo, git_env)
    print("Batched push completed")
    print()


def transfer(
    repo_root: Path,
    threshold_bytes: int,
    part_size_bytes: int,
    dry_run: bool,
    target_repo: str | None,
    github_token: str | None,
    tmp_root: Path,
    batched: bool,
    push_batch_bytes: int,
    remove_build_dirs: bool,
    remove_source_build_artifacts: bool,
) -> None:
    print("Step 1: resolve target repository and credentials")
    resolved_repo, token = resolve_transfer_credentials(target_repo, github_token)
    branch = current_branch(repo_root)
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    stage_root = tmp_root / f"sdk-share-{repo_root.name}-{timestamp}"
    print(f"Source branch      : {branch}")
    print(f"Temporary stage dir: {stage_root}")
    print()

    if remove_source_build_artifacts:
        print("Step 2: remove regenerable build artifacts from the live workspace")
        remove_build_artifacts(repo_root, dry_run, "Removing source build artifacts")
        print("Step 3: copy repository into the temporary staging area")
    else:
        print("Step 2: copy repository into the temporary staging area")
    stage_repo = copy_repo_to_stage(repo_root, stage_root, dry_run)
    if dry_run:
        if remove_build_dirs:
            print(f"[dry-run] would remove top-level build directories from {stage_repo}")
        print(f"[dry-run] would prepare staged copy in {stage_repo}")
        if batched:
            print(
                f"[dry-run] would push branch {branch} to {resolved_repo} in batches of about {human_size(push_batch_bytes)}"
            )
        else:
            print(f"[dry-run] would push branch {branch} to {resolved_repo}")
        return

    print("Step 4: prepare the staged repository for sharing" if remove_source_build_artifacts else "Step 3: prepare the staged repository for sharing")
    if remove_build_dirs:
        print("Removing build directories from the staged copy before packaging")
        remove_stage_build_dirs(stage_repo, False)
    prepare(stage_repo, threshold_bytes, part_size_bytes, False)

    print("Step 5: push the staged repository to GitHub" if remove_source_build_artifacts else "Step 4: push the staged repository to GitHub")
    git_env = os.environ.copy()
    git_env["GIT_TERMINAL_PROMPT"] = "0"
    git_config = [f"http.extraheader={github_auth_header(token)}"]
    init_stage_repository(stage_repo, branch, git_env)
    if batched:
        commit_and_push_in_batches(
            stage_repo,
            resolved_repo,
            branch,
            git_env,
            git_config,
            push_batch_bytes,
        )
    else:
        commit_and_push_all(stage_repo, resolved_repo, branch, git_env, git_config)
    print()
    print(f"Transfer complete. Staged copy remains at {stage_repo}")


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    threshold_bytes = args.threshold_mb * 1024 * 1024
    part_size_bytes = args.part_size_mb * 1024 * 1024
    push_batch_bytes = args.push_batch_mb * 1024 * 1024

    if not (repo_root / ".git").exists():
        raise SystemExit(f"{repo_root} does not look like a Git repository root")

    print_welcome(
        args.mode,
        repo_root,
        threshold_bytes,
        part_size_bytes,
        args.remove_build_dirs,
        args.remove_source_build_artifacts,
    )

    if args.mode == "prepare":
        prepare(repo_root, threshold_bytes, part_size_bytes, args.dry_run)
    elif args.mode == "unpack":
        unpack(repo_root, args.dry_run, args.force)
    else:
        transfer(
            repo_root,
            threshold_bytes,
            part_size_bytes,
            args.dry_run,
            args.target_repo,
            args.github_token,
            Path(args.tmp_root).resolve(),
            args.mode == "transfer-batched",
            push_batch_bytes,
            args.remove_build_dirs,
            args.remove_source_build_artifacts,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
