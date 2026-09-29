#!/usr/bin/env python3
"""Read-only, local Git evidence for storage review. Python 3.10+, no packages."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time


OUTPUT_LIMIT = 1024 * 1024


def git_environment() -> dict[str, str]:
    # Do not let GIT_DIR/INDEX_FILE/config injection redirect this audit.
    env = {key: value for key, value in os.environ.items()
           if not key.upper().startswith("GIT_")}
    env.update(GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0",
               GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
    return env


def run_git(executable: str, root: Path, args: list[str], env: dict[str, str],
            deadline: float, overrides: list[str]) -> dict:
    result = {"exit_code": None, "timed_out": False,
              "output_truncated": False, "stdout": b""}
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        result["timed_out"] = True
        return result
    command = [executable, "--no-optional-locks", "--no-pager",
               "-c", "core.fsmonitor=false", *overrides, "-C", str(root), *args]
    # Spill output outside the repository; retain at most OUTPUT_LIMIT in memory.
    # Raw stderr may contain config values or remote URLs, so never publish it.
    try:
        with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as error:
            try:
                completed = subprocess.run(command, env=env, stdin=subprocess.DEVNULL,
                                           stdout=output, stderr=error, timeout=remaining)
                result["exit_code"] = completed.returncode
            except subprocess.TimeoutExpired:
                result["timed_out"] = True
            output.seek(0)
            data = output.read(OUTPUT_LIMIT + 1)
            result["output_truncated"] = len(data) > OUTPUT_LIMIT
            result["stdout"] = data[:OUTPUT_LIMIT]
    except OSError:
        result["unavailable"] = True
    return result


def succeeded(result: dict, allowed: tuple[int, ...] = (0,)) -> bool:
    return (result["exit_code"] in allowed and not result["timed_out"]
            and not result["output_truncated"])


def decode(data: bytes) -> str:
    return data.decode("utf-8", errors="replace")


def status_summary(data: bytes, limit: int) -> dict:
    """Porcelain -z uses a second NUL record for the source of a rename/copy."""
    records = data.split(b"\0")
    counts = {"tracked_changes": 0, "untracked_entries": 0, "ignored_entries": 0}
    samples = []
    valid = data == b"" or data.endswith(b"\0")
    index = 0
    while index < len(records) - 1:
        record = records[index]
        index += 1
        if len(record) < 4 or record[2:3] != b" ":
            valid = False
            continue
        code, path = decode(record[:2]), decode(record[3:])
        key = {"??": "untracked_entries", "!!": "ignored_entries"}.get(code, "tracked_changes")
        counts[key] += 1
        item = {"status": code, "path": path}
        if "R" in code or "C" in code:
            if index >= len(records) - 1:
                valid = False
                break
            item["original_path"] = decode(records[index])
            index += 1
        if len(samples) < limit:
            samples.append(item)
    return {**counts, "samples": samples, "parse_complete": valid,
            "counts_unit": "Git entries; untracked/ignored directories may be collapsed"}


def audit(path: Path, *, timeout: float = 20, samples: int = 20) -> dict:
    report = {"schema_version": 1, "path": str(path),
              "checked_at": datetime.now(timezone.utc).isoformat(),
              "complete": False, "remote_verified": False,
              "risks": [], "checks": {}}
    if not math.isfinite(timeout) or not 0 < timeout <= 300 or not 0 <= samples <= 100:
        raise ValueError("timeout must be in (0, 300]; samples must be between 0 and 100")
    if not path.is_absolute() or not path.is_dir():
        report["risks"].append("invalid_directory: provide an existing absolute path")
        return report
    executable = shutil.which("git")
    if not executable:
        report["risks"].append("git_unavailable")
        return report
    env, deadline = git_environment(), time.monotonic() + timeout
    overrides: list[str] = []
    results = {}

    def check(name: str, args: list[str]) -> dict:
        result = run_git(executable, path, args, env, deadline, overrides)
        results[name] = result
        report["checks"][name] = {key: value for key, value in result.items() if key != "stdout"}
        return result

    discovery = check("repository", ["rev-parse", "--is-inside-work-tree",
                                      "--is-bare-repository", "--is-shallow-repository"])
    if not succeeded(discovery):
        report["risks"].append("repository_unavailable: Git failed or exceeded the budget")
        return report
    flags = decode(discovery["stdout"]).splitlines()
    if len(flags) != 3 or any(value not in ("true", "false") for value in flags):
        report["risks"].append("repository_state_unknown")
        return report
    report["bare"], report["shallow"] = flags[1] == "true", flags[2] == "true"

    # A status operation can invoke configured clean/process filters. Disable
    # effective local filters before status, and disclose the altered semantics.
    filters = check("filters", ["config", "--includes", "--null", "--name-only",
                                "--get-regexp", r"^filter\..*\.(clean|smudge|process|required)$"])
    if not succeeded(filters, (0, 1)):
        report["risks"].append("filter_configuration_unknown: worktree inspection skipped")
        return report
    keys = [decode(key) for key in filters["stdout"].split(b"\0") if key]
    for key in set(keys):
        overrides.extend(["-c", key + ("=false" if key.endswith(".required") else "=")])
    report["filters_disabled"] = bool(keys)
    report["configuration_scope"] = "local; system/global config and inherited GIT_* overrides excluded"
    if keys:
        report["risks"].append("filters_disabled: content conversion may change status; inspect separately")

    commands = {
        "location": ["rev-parse", "--show-toplevel"],
        "git_dir": ["rev-parse", "--absolute-git-dir"],
        "common_dir": ["rev-parse", "--path-format=absolute", "--git-common-dir"],
        "status": ["status", "--porcelain=v1", "-z", "--untracked-files=normal",
                   "--ignored=matching", "--ignore-submodules=all"],
        "refs": ["for-each-ref", "--format=%(refname) %(objectname) %(upstream:track)",
                 "refs/heads", "refs/tags"],
        "stash": ["stash", "list", "--format=%gd"],
        "worktrees": ["worktree", "list", "--porcelain", "-z"],
        "submodules": ["ls-files", "--stage", "-z"],
        "remotes": ["remote"],
        "local_commits": ["rev-list", "--count", "--branches", "--tags", "HEAD", "--not", "--remotes"],
    }
    for name, args in commands.items():
        check(name, args)

    for name in ("location", "git_dir", "common_dir"):
        # Remove only Git's record terminator, preserving newlines in path names.
        report[name] = decode(results[name]["stdout"].removesuffix(b"\n")) if succeeded(results[name]) else None
    status = status_summary(results["status"]["stdout"], samples)
    parsed = status.pop("parse_complete")
    status["complete"] = succeeded(results["status"]) and parsed
    report["status"] = status
    for name in ("refs", "stash", "remotes"):
        lines = decode(results[name]["stdout"]).splitlines()
        report[name] = {"observed_count": len(lines), "samples": lines[:samples],
                        "complete": succeeded(results[name])}
    trees = [decode(record[9:]) for record in results["worktrees"]["stdout"].split(b"\0")
             if record.startswith(b"worktree ")]
    report["worktrees"] = {"observed_count": len(trees), "samples": trees[:samples],
                           "complete": succeeded(results["worktrees"])}
    modules = [decode(record.split(b"\t", 1)[1])
               for record in results["submodules"]["stdout"].split(b"\0")
               if record.startswith(b"160000 ") and b"\t" in record]
    report["submodules"] = {"observed_count": len(modules), "samples": modules[:samples],
                            "complete": succeeded(results["submodules"]),
                            "worktrees_inspected": False}
    commits = results["local_commits"]["stdout"].strip()
    report["commits_not_in_cached_remotes"] = (
        int(commits) if succeeded(results["local_commits"]) and commits.isdigit() else None)
    report["complete"] = (all(succeeded(result, (0, 1) if name == "filters" else (0,))
                              for name, result in results.items()) and status["complete"])
    risks = report["risks"]
    risks.append("remote_refs_are_cached: no network verification or complete-backup guarantee")
    if not report["complete"]:
        risks.append("incomplete_checks: failures, timeouts or output limits are unknown, not clean")
    if any(status[name] for name in ("tracked_changes", "untracked_entries", "ignored_entries")):
        risks.append("local_worktree_data")
    if report["stash"]["observed_count"]:
        risks.append("local_stashes")
    normalize = lambda value: os.path.normcase(os.path.normpath(value)) if value else None
    location = report["location"]
    report["external_git_metadata"] = bool(
        location and report["git_dir"] and
        normalize(report["git_dir"]) != normalize(os.path.join(location, ".git")))
    if len(trees) > 1 or normalize(location) != normalize(str(path)) or report["external_git_metadata"]:
        risks.append("check_repository_and_worktree_boundaries")
    if modules:
        risks.append("submodule_worktrees_require_separate_audit")
    if report["shallow"]:
        risks.append("shallow_history: ancestry coverage is incomplete")
    if not report["remotes"]["observed_count"] or report["commits_not_in_cached_remotes"]:
        risks.append("history_not_proven_backed_up")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="absolute repository or worktree directory")
    parser.add_argument("--timeout", type=float, default=20, help="total Git time budget in seconds")
    parser.add_argument("--samples", type=int, default=20, help="samples per category, 0..100")
    args = parser.parse_args()
    if not math.isfinite(args.timeout) or not 0 < args.timeout <= 300 or not 0 <= args.samples <= 100:
        parser.error("timeout must be in (0, 300]; samples must be between 0 and 100")
    report = audit(args.path, timeout=args.timeout, samples=args.samples)
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0 if report["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
