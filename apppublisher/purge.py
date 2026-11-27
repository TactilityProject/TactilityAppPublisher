# License: Apache License v2
"""Purges the Cloudflare CDN cache of the files that were uploaded, so devices get the new files right away."""

import json
import os
import urllib.error
import urllib.request

DEFAULT_BASE_URL = "https://cdn.tactilityproject.org"
# Cloudflare purges at most this many URLs per request on the lower plans
URLS_PER_REQUEST = 30


def get_purge_urls(file_names, sdk_version, prefix, base_url=DEFAULT_BASE_URL):
    return [f"{base_url.rstrip('/')}/{prefix}/{sdk_version}/{name}" for name in sorted(file_names)]


def _purge_batch(zone_id, token, urls):
    request = urllib.request.Request(
        f"https://api.cloudflare.com/client/v4/zones/{zone_id}/purge_cache",
        data=json.dumps({"files": urls}).encode("utf-8"),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.load(response)
    except urllib.error.HTTPError as e:
        print(f"WARNING: Cache purge failed with status {e.code}: {e.read().decode('utf-8', 'replace')}")
        return False
    except (urllib.error.URLError, TimeoutError, ValueError) as e:
        print(f"WARNING: Cache purge failed: {e}")
        return False
    if not result.get("success", False):
        print(f"WARNING: Cache purge failed: {result.get('errors')}")
        return False
    return True


def purge(path, sdk_version, prefix, base_url=DEFAULT_BASE_URL):
    """Purges <base_url>/<prefix>/<sdk_version>/<file> for the files in path. Reads CLOUDFLARE_ZONE_ID and
    CLOUDFLARE_PURGE_CACHE_TOKEN. Without them, or when the purge fails, it only prints a warning: the files then
    refresh when their cache expires."""
    zone_id = os.environ.get("CLOUDFLARE_ZONE_ID", "")
    token = os.environ.get("CLOUDFLARE_PURGE_CACHE_TOKEN", "")
    if not zone_id or not token:
        print("WARNING: CLOUDFLARE_ZONE_ID or CLOUDFLARE_PURGE_CACHE_TOKEN is not set, so the CDN cache isn't purged")
        return
    if not os.path.isdir(path):
        print(f"WARNING: Path not found: {path}")
        return
    urls = get_purge_urls(os.listdir(path), sdk_version, prefix, base_url)
    purged = 0
    for start in range(0, len(urls), URLS_PER_REQUEST):
        batch = urls[start:start + URLS_PER_REQUEST]
        if _purge_batch(zone_id, token, batch):
            purged += len(batch)
    print(f"Purged the CDN cache of {purged}/{len(urls)} files")
