# License: Apache License v2
"""Prepares the release files for GitHub Pages"""

import os
import shutil
import sys

from .s3 import DEFAULT_PREFIX


def publish_pages(path, sdk_version, out, prefix=DEFAULT_PREFIX):
    """Copies the files to <out>/<prefix>/<sdk_version>/, the same layout as the bucket.
    The result is a site folder for actions/upload-pages-artifact. Existing files in out are kept,
    so that the folders of other SDK versions stay in the site."""
    if not os.path.isdir(path):
        sys.exit(f"Path not found: {path}")
    destination = os.path.join(out, prefix, sdk_version)
    os.makedirs(destination, exist_ok=True)
    files = sorted(os.listdir(path))
    for file_name in files:
        shutil.copy2(os.path.join(path, file_name), os.path.join(destination, file_name))
    # Without this file Pages runs Jekyll, which ignores files and folders that start with an underscore
    open(os.path.join(out, ".nojekyll"), "a").close()
    print(f"Copied {len(files)} files to {destination}")
