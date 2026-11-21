# License: Apache License v2
"""Checks and bumps the versions in the manifest.properties of the apps of a project"""

import subprocess
import sys
from pathlib import Path

MANIFEST = "manifest.properties"
VERSION_CODE_KEY = "version.code"
VERSION_NAME_KEY = "version.name"


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, check=True, **kwargs)


def parse_properties(text: str) -> dict[str, str]:
    props: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            props[key.strip()] = value.strip()
    return props


def parse_version_code(value: str) -> int | None:
    """Return version code as an integer, or None if it isn't a non-negative integer."""
    return int(value) if value.isdecimal() else None


def get_changed_apps(base_ref: str, apps_dir: str) -> set[str]:
    """Return set of app names that have file changes vs base_ref."""
    result = run(["git", "diff", base_ref, "--name-only", "--", apps_dir])
    apps: set[str] = set()
    for line in result.stdout.splitlines():
        parts = line.split("/")
        if len(parts) >= 2 and parts[0] == apps_dir:
            apps.add(parts[1])
    return apps


def get_file_at_ref(ref: str, path: str) -> str | None:
    """Return file contents at a git ref, or None if it doesn't exist."""
    try:
        result = run(["git", "show", f"{ref}:{path}"])
        return result.stdout
    except subprocess.CalledProcessError:
        return None


def path_exists_at_ref(ref: str, path: str) -> bool:
    """Return True if a file or directory exists at a git ref."""
    try:
        run(["git", "cat-file", "-e", f"{ref}:{path}"])
        return True
    except subprocess.CalledProcessError:
        return False


def check(base_ref: str, apps_dir: str) -> int:
    """Checks that the apps that changed against base_ref have a higher version.code and another version.name. @return the exit code"""

    # Make sure base ref exists
    try:
        run(["git", "rev-parse", "--verify", base_ref])
    except subprocess.CalledProcessError:
        print(f"Error: cannot resolve ref '{base_ref}'", file=sys.stderr)
        return 1

    changed_apps = get_changed_apps(base_ref, apps_dir)
    if not changed_apps:
        print("No app changes detected.")
        return 0

    print(f"Changed apps: {', '.join(sorted(changed_apps))}\n")

    failures: list[str] = []

    for app_name in sorted(changed_apps):
        manifest_path = f"{apps_dir}/{app_name}/{MANIFEST}"

        base_content = get_file_at_ref(base_ref, manifest_path)
        head_content = get_file_at_ref("HEAD", manifest_path)

        if head_content is None:
            if not path_exists_at_ref("HEAD", f"{apps_dir}/{app_name}"):
                print(f"  {app_name}: removed app – skipped")
                continue
            failures.append(f"{app_name}: manifest.properties missing on HEAD")
            continue

        if base_content is None:
            # New app – no check needed
            print(f"  {app_name}: new app (no base manifest) – OK")
            continue

        base_props = parse_properties(base_content)
        head_props = parse_properties(head_content)

        missing = [key for key in (VERSION_CODE_KEY, VERSION_NAME_KEY) if not head_props.get(key)]
        if missing:
            failures.append(f"{app_name}: {', '.join(missing)} missing on HEAD")
            continue

        base_code = base_props.get(VERSION_CODE_KEY, "")
        head_code = head_props.get(VERSION_CODE_KEY, "")
        base_name = base_props.get(VERSION_NAME_KEY, "")
        head_name = head_props.get(VERSION_NAME_KEY, "")

        head_code_num = parse_version_code(head_code)
        if head_code_num is None:
            failures.append(f"{app_name}: version.code is not an integer ({head_code})")
            continue

        # A non-numeric base code can't be compared; accept any valid head code then
        base_code_num = parse_version_code(base_code)
        code_bumped = base_code_num is None or head_code_num > base_code_num
        name_bumped = base_name != head_name

        if code_bumped and name_bumped:
            print(f"  {app_name}: version bumped ({base_name}→{head_name}, {base_code}→{head_code}) – OK")
        else:
            problems: list[str] = []
            if not code_bumped:
                problems.append(f"version.code not increased ({base_code}→{head_code})")
            if not name_bumped:
                problems.append(f"version.name unchanged ({head_name})")
            failures.append(f"{app_name}: {', '.join(problems)}")

    print()

    if failures:
        print("FAIL – missing version bump:")
        for f in failures:
            print(f"  ✗ {f}")
        return 1

    print("PASS – all changed apps have bumped versions.")
    return 0


def parse_version(name: str) -> list[int]:
    parts = name.strip().split(".")
    return [int(p) for p in parts]


def bump_version(name: str, component: str) -> str:
    parts = parse_version(name)
    while len(parts) < 3:
        parts.append(0)

    if component == "major":
        parts[0] += 1
        parts[1] = 0
        parts[2] = 0
    elif component == "minor":
        parts[1] += 1
        parts[2] = 0
    elif component == "patch":
        parts[2] += 1

    return ".".join(str(p) for p in parts)


def process_manifest(path: Path, component: str) -> None:
    lines = path.read_text().splitlines(keepends=True)
    changed = False
    new_lines = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith(VERSION_NAME_KEY + "="):
            old_value = stripped.split("=", 1)[1].strip()
            new_value = bump_version(old_value, component)
            new_lines.append(line.replace(old_value, new_value))
            changed = True
        elif stripped.startswith(VERSION_CODE_KEY + "="):
            old_code = int(stripped.split("=", 1)[1].strip())
            new_code = old_code + 1
            new_lines.append(line.replace(str(old_code), str(new_code), 1))
            changed = True
        else:
            new_lines.append(line)

    if changed:
        path.write_text("".join(new_lines))
        print(f"  {path.parent.name}: bumped")


def bump(component: str, apps_dir: str) -> int:
    """Bumps the version name and increments the version code of all apps. @return the exit code"""
    manifests = sorted(Path(apps_dir).glob(f"*/{MANIFEST}"))
    if not manifests:
        print(f"No manifests found in {apps_dir}", file=sys.stderr)
        return 1

    print(f"Bumping {component} (+ version.code) in {len(manifests)} apps:\n")
    for manifest in manifests:
        process_manifest(manifest, component)

    print("\nDone.")
    return 0
