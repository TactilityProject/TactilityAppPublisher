#!/usr/bin/env python3
# License: Apache License v2
"""Publishes Tactility apps to an S3 compatible bucket or to GitHub Pages. Run "python apppublisher.py --help"."""

import argparse
import sys

from apppublisher.s3 import DEFAULT_BUCKET, DEFAULT_PREFIX, DEFAULT_REGION, publish_s3
from apppublisher.matrix import matrix
from apppublisher.pages import publish_pages
from apppublisher.release import release
from apppublisher.versions import bump, check


def main():
    parser = argparse.ArgumentParser(prog="apppublisher", description="Publishes Tactility apps to an S3 compatible bucket or to GitHub Pages")
    commands = parser.add_subparsers(dest="command", required=True)

    command = commands.add_parser("matrix", help="print a GitHub Actions matrix with the apps of the project")
    command.add_argument("--apps-dir", default="Apps")

    command = commands.add_parser("check-versions", help="check that changed apps have a bumped version")
    command.add_argument("base_ref", nargs="?", default="main")
    command.add_argument("--apps-dir", default="Apps")

    command = commands.add_parser("bump", help="bump the version of all apps")
    command.add_argument("component", choices=("major", "minor", "patch"))
    command.add_argument("--apps-dir", default="Apps")

    command = commands.add_parser("release", help="create the index files next to the .app files of a folder")
    command.add_argument("directory")
    command.add_argument("--sdk-version-file", default="sdk_version.txt", help="where the SDK version of the apps is written")

    command = commands.add_parser("publish", help="publish the files of a released folder")
    targets = command.add_subparsers(dest="target", required=True)
    s3 = targets.add_parser("s3", help="upload to an S3 compatible bucket, only tested with Cloudflare R2 (env: S3_ACCESS_KEY_ID, S3_SECRET_ACCESS_KEY, S3_ENDPOINT_URL)")
    s3.add_argument("directory")
    s3.add_argument("--sdk", required=True, help="the SDK version, which is a path segment")
    s3.add_argument("--bucket", default=DEFAULT_BUCKET)
    s3.add_argument("--prefix", default=DEFAULT_PREFIX)
    s3.add_argument("--endpoint-url", help="the endpoint of the service (default: S3_ENDPOINT_URL, else the R2 endpoint of CDN_ID, else AWS S3)")
    s3.add_argument("--region", default=DEFAULT_REGION)
    s3.add_argument("--index-only", action="store_true", help="upload only the index files")
    pages = targets.add_parser("pages", help="copy to a site folder for GitHub Pages")
    pages.add_argument("directory")
    pages.add_argument("--sdk", required=True, help="the SDK version, which is a path segment")
    pages.add_argument("--out", required=True, help="the site folder")
    pages.add_argument("--prefix", default=DEFAULT_PREFIX)

    args = parser.parse_args()
    if args.command == "matrix":
        matrix(args.apps_dir)
    elif args.command == "check-versions":
        sys.exit(check(args.base_ref, args.apps_dir))
    elif args.command == "bump":
        sys.exit(bump(args.component, args.apps_dir))
    elif args.command == "release":
        release(args.directory, args.sdk_version_file)
    elif args.target == "s3":
        publish_s3(args.directory, args.sdk, args.bucket, args.prefix, args.index_only, args.endpoint_url, args.region)
    else:
        publish_pages(args.directory, args.sdk, args.out, args.prefix)


if __name__ == "__main__":
    main()
