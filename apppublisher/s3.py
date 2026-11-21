# License: Apache License v2
"""Uploads the release files to an S3 compatible bucket. Only tested with Cloudflare R2."""

import os
import re
import sys

DEFAULT_BUCKET = "tactility"
DEFAULT_PREFIX = "apps"
DEFAULT_REGION = "auto"


def is_index_file(file_name: str):
    return file_name == 'apps.json' or file_name == 'index.json' or re.fullmatch(r'list[_-].*\d+\.json', file_name) is not None


def get_endpoint_url(endpoint_url=None):
    """The endpoint option, else S3_ENDPOINT_URL, else the R2 endpoint of the account in CDN_ID. @return None for AWS S3"""
    endpoint_url = endpoint_url or os.environ.get("S3_ENDPOINT_URL")
    if not endpoint_url and os.environ.get("CDN_ID"):
        endpoint_url = f"https://{os.environ['CDN_ID']}.r2.cloudflarestorage.com"
    return endpoint_url or None


def publish_s3(path, sdk_version, bucket=DEFAULT_BUCKET, prefix=DEFAULT_PREFIX, index_only=False, endpoint_url=None, region=DEFAULT_REGION):
    """Uploads to <prefix>/<sdk_version>/. The credentials are in S3_ACCESS_KEY_ID and S3_SECRET_ACCESS_KEY.
    CDN_TOKEN_NAME and CDN_TOKEN_VALUE work too, from before the target was called s3."""
    import boto3

    if not os.path.exists(path):
        sys.exit(f"Path not found: {path}")
    access_key = os.environ.get("S3_ACCESS_KEY_ID") or os.environ.get("CDN_TOKEN_NAME")
    secret_key = os.environ.get("S3_SECRET_ACCESS_KEY") or os.environ.get("CDN_TOKEN_VALUE")
    if not access_key or not secret_key:
        sys.exit("Missing environment variables: S3_ACCESS_KEY_ID and S3_SECRET_ACCESS_KEY")
    s3 = boto3.client(
        service_name="s3",
        endpoint_url=get_endpoint_url(endpoint_url),
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region
    )
    files_to_upload = os.listdir(path)
    if index_only:
        files_to_upload = [f for f in files_to_upload if is_index_file(f)]
    else:
        # The index files go last, so they never reference files that haven't finished uploading yet
        files_to_upload.sort(key=is_index_file)
    total = len(files_to_upload)
    for counter, file_name in enumerate(files_to_upload, start=1):
        object_path = f"{prefix}/{sdk_version}/{file_name}"
        print(f"[{counter}/{total}] Uploading {file_name} to {object_path}")
        try:
            s3.upload_file(os.path.join(path, file_name), bucket, object_path)
        except Exception as e:
            sys.exit(f"Failed to upload {file_name}: {e}")
