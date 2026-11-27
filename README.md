# Tactility App Publisher

Builds, versions and publishes Tactility apps to an S3 compatible bucket or to GitHub Pages.
It makes the catalog files that the Tactility app hub reads: `apps.json`, `index.json`, `list_N.json`, `list-<arch>-N.json`, a `<app id>.json` per app and the icons.
Both targets get the same layout, `apps/<sdk version>/...`, so a device only needs another base URL.

## Use it in a project

A project has an `Apps/` folder with one folder per app (each with a `manifest.properties`) and a `tt.py` in its root.
Add `.github/workflows/main.yml`:

```yaml
name: Main
on:
  push:
    branches: [main]
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  apps:
    uses: TactilityProject/TactilityAppPublisher/.github/workflows/publish.yml@main
    with:
      target: both          # s3, pages or both
    permissions:
      contents: read
      pages: write          # GitHub rejects the workflow without these two, also when target is s3
      id-token: write
    secrets: inherit        # S3_ACCESS_KEY_ID and S3_SECRET_ACCESS_KEY, only for s3 or both
```

What it does:

- Pull requests: checks that every changed app has a higher `version.code` and another `version.name`.
- Every app folder is built with `tt app build` (one matrix job per app, with a compiler cache).
- The packages are bundled into the catalog files. All apps must target the same SDK version.
- Pushes to `main` publish: to the S3 bucket, and/or to the GitHub Pages site.

Options (`with:`):

| Option | Default | |
|---|---|---|
| `target` | `s3` | `s3`, `pages` or `both` |
| `apps_dir` | `Apps` | Folder with the apps |
| `tt_path` | `tt.py` | The `tt.py` of the project, relative to its root |
| `esp_idf_version` | `v6.1` | |
| `publish_ref` | `refs/heads/main` | Other refs only build |
| `warm_cache_app` | | An app that targets every ESP32 platform, built first to fill the compiler cache |
| `bucket`, `prefix` | `tactility`, `apps` | Where files go in the bucket, and the folder in the Pages site |
| `endpoint_url`, `region` | empty, `auto` | The S3 service, see below |

For GitHub Pages, set Settings > Pages > Source to "GitHub Actions". A deployment replaces the whole site, so the site holds the apps of the SDK version of the latest build.
### S3 compatible storage

The `s3` target uploads with `boto3`, so it works with services that have an S3 compatible API, such as AWS S3, Cloudflare R2, Backblaze B2, DigitalOcean Spaces, Wasabi, MinIO and Hetzner Object Storage.
**It has only been tested with Cloudflare R2.** Other services should work, but they have not been tried.

Set the secrets `S3_ACCESS_KEY_ID` and `S3_SECRET_ACCESS_KEY`, and the `endpoint_url` option (or the `S3_ENDPOINT_URL` secret as an environment variable when running locally). Without an endpoint it uses AWS S3. Set `region` when the service needs one (R2 uses `auto`, the default).

The older secrets of Cloudflare R2 still work: `CDN_TOKEN_NAME` and `CDN_TOKEN_VALUE` are the access key, and without an endpoint, `CDN_ID` (the Cloudflare account id) gives the R2 endpoint `https://<CDN_ID>.r2.cloudflarestorage.com`.

The files go to `<prefix>/<sdk version>/` in the bucket. The packages, details and icons are uploaded first and the index files last. The bucket has to serve the files publicly, for example through a CDN or a public bucket URL. Other storage APIs (Azure Blob, Bunny Storage and so on) are not supported.

The JSON files are uploaded with `Cache-Control: public, max-age=60`. With the secrets `CLOUDFLARE_ZONE_ID` and `CLOUDFLARE_PURGE_CACHE_TOKEN` (an API token with the Zone > Cache Purge permission), the Cloudflare cache of the uploaded files is purged after the upload. Without them, or when the purge fails, the job only prints a warning.

The workflow and its actions are used at `@main`. Fork the repository or change the `@main` of the actions in `publish.yml` to pin a version.

## Use it locally

Python 3.11 or newer. Only the S3 upload needs `pip install boto3`.

```
python apppublisher.py matrix [--apps-dir Apps]
python apppublisher.py check-versions [base-ref] [--apps-dir Apps]
python apppublisher.py bump major|minor|patch [--apps-dir Apps]
python apppublisher.py release <folder with .app files>
python apppublisher.py publish s3 <folder> --sdk <version> [--endpoint-url <url>] [--region <region>]
                                  # env: S3_ACCESS_KEY_ID, S3_SECRET_ACCESS_KEY, S3_ENDPOINT_URL
python apppublisher.py publish pages <folder> --sdk <version> --out <site folder>
python apppublisher.py purge-cache <folder> --sdk <version> [--prefix apps] [--base-url https://cdn.tactilityproject.org]
                                  # env: CLOUDFLARE_ZONE_ID, CLOUDFLARE_PURGE_CACHE_TOKEN
```

`release` runs in a git repository, as it stores the commit hash. It renames the `.app` files to `<app id>-<version code>.app` and writes the catalog files next to them, then `publish` uploads or copies the folder.
An app needs `description.short` (at most 32 characters) in its `manifest.properties`.

Tests: `python -m unittest discover -s tests`.

## License

[Apache License v2](LICENSE.md)
