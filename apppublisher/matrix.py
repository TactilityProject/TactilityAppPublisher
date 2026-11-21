# License: Apache License v2
"""Discovers the app folders of a project and emits a GitHub Actions matrix"""

import json
import os
from pathlib import Path

MANIFEST = "manifest.properties"


def get_app_names(apps_dir):
    names = []
    for entry in sorted(os.listdir(apps_dir)):
        app_dir = Path(apps_dir) / entry
        if app_dir.is_dir() and (app_dir / MANIFEST).is_file():
            names.append(entry)
    return names


def matrix(apps_dir):
    """Prints the matrix, or writes it to the GITHUB_OUTPUT file when that is set"""
    matrix_json = json.dumps({"app_name": get_app_names(apps_dir)})
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a") as file:
            file.write(f"matrix={matrix_json}\n")
    else:
        print(matrix_json)
