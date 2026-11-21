# License: Apache License v2
"""Reads the manifest.properties of an app and of a packaged .app file"""

import os
import tarfile
import tempfile


def read_properties_file(path):
    properties = {}
    with open(path, "r") as file:
        for line in file:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            key, sep, value = line.partition("=")
            if not sep:
                continue
            properties[key.strip()] = value.strip()
    return properties

def get_manifest(appPath):
    """Reads the manifest.properties inside a .app file (a tar archive). @return a dict, or None on failure"""
    print(f"Unpacking manifest.properties from {appPath}")
    if not os.path.isfile(appPath):
        print(f"File not found: {appPath}")
        return None

    try:
        # Auto-detect compression (tar, tar.gz, tar.bz2, etc.)
        with tarfile.open(appPath, mode="r:*") as tf:
            # Find a member whose base name is exactly 'manifest.properties'
            member = None
            for m in tf.getmembers():
                # Skip directories and non-files
                if not m.isfile():
                    continue
                if os.path.basename(m.name) == "manifest.properties":
                    member = m
                    break

            if member is None:
                print("manifest.properties not found in archive")
                return None

            # Read the member's content and write it directly into outputPath
            # Create a temporary directory that persists after this function returns.
            temp_dir = tempfile.mkdtemp(prefix="tactility_app_")
            dest_file = os.path.join(temp_dir, "manifest.properties")
            with tf.extractfile(member) as src, open(dest_file, "wb") as dst:
                if src is None:
                    print("Failed to open manifest.properties from the archive")
                    return None
                while True:
                    chunk = src.read(1024 * 1024)
                    if not chunk:
                        break
                    dst.write(chunk)
            properties = read_properties_file(dest_file)
            os.remove(dest_file)
            os.rmdir(temp_dir)
            return properties
    except tarfile.ReadError as e:
        print(f"Not a valid tar archive: {appPath} ({e})")
    except Exception as e:
        print(f"Failed to extract manifest.properties from {appPath}: {e}")
    return None

def get_icons(appPath):
    """Read icon.svg and icon_mono.svg from the package. Returns a dict of the ones that exist."""
    icons = {}
    with tarfile.open(appPath, mode="r:*") as tf:
        for m in tf.getmembers():
            if m.isfile() and m.name.lstrip("./") in ("icon.svg", "icon_mono.svg"):
                icons[os.path.basename(m.name)] = tf.extractfile(m).read()
    return icons
