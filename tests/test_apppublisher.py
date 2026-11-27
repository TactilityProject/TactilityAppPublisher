import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apppublisher.purge import get_purge_urls, purge
from apppublisher.s3 import get_endpoint_url, get_upload_args, is_index_file
from apppublisher.pages import publish_pages
from apppublisher.release import PAGE_SIZE, get_list_file_name, write_list_pages
from apppublisher.versions import bump_version


def make_app(index, platforms):
    return {
        "appId": f"test.app{index:03}",
        "appName": f"App {index:03}",
        "appVersionCode": 1,
        "shortDescription": "Test",
        "targetPlatforms": platforms,
    }


def read(directory, name):
    with open(os.path.join(directory, name)) as file:
        return json.load(file)


class ReleaseTest(unittest.TestCase):
    def test_list_is_paged(self):
        apps = [make_app(i, []) for i in range(PAGE_SIZE + 1)]
        with tempfile.TemporaryDirectory() as directory:
            write_list_pages(directory, {"sdkVersion": "1.0.0"}, apps, set())
            first = read(directory, "index.json")
            second = read(directory, "list_2.json")
            self.assertEqual((first["page"], first["pageCount"], first["appCount"]), (1, 2, PAGE_SIZE + 1))
            self.assertEqual(len(first["apps"]), PAGE_SIZE)
            self.assertEqual(len(second["apps"]), 1)

    def test_architecture_list_has_apps_that_support_it(self):
        apps = [make_app(1, []), make_app(2, ["esp32s3"]), make_app(3, ["esp32"])]
        with tempfile.TemporaryDirectory() as directory:
            write_list_pages(directory, {}, apps, set(), "esp32s3")
            listed = [app["id"] for app in read(directory, get_list_file_name(1, "esp32s3"))["apps"]]
            self.assertEqual(listed, ["test.app001", "test.app002"])

    def test_app_without_icon_is_marked(self):
        with tempfile.TemporaryDirectory() as directory:
            write_list_pages(directory, {}, [make_app(1, [])], {"test.app001"})
            self.assertIs(read(directory, "index.json")["apps"][0]["icon"], False)

    def test_index_files_are_recognized(self):
        for name in ("apps.json", "index.json", "list_2.json", "list-esp32s3-1.json"):
            self.assertTrue(is_index_file(name), name)
        for name in ("test.app.json", "test.app-1.app", "test.app-1-icon.svg"):
            self.assertFalse(is_index_file(name), name)


class S3Test(unittest.TestCase):
    def test_endpoint(self):
        keep = {name: os.environ.pop(name, None) for name in ("S3_ENDPOINT_URL", "CDN_ID")}
        try:
            self.assertIsNone(get_endpoint_url())
            os.environ["CDN_ID"] = "abc"
            self.assertEqual(get_endpoint_url(), "https://abc.r2.cloudflarestorage.com")
            os.environ["S3_ENDPOINT_URL"] = "https://s3.example.com"
            self.assertEqual(get_endpoint_url(), "https://s3.example.com")
            self.assertEqual(get_endpoint_url("https://other.example.com"), "https://other.example.com")
        finally:
            for name, value in keep.items():
                os.environ.pop(name, None)
                if value is not None:
                    os.environ[name] = value


    def test_json_files_are_cached_briefly(self):
        self.assertEqual(get_upload_args("index.json"), {"CacheControl": "public, max-age=60"})
        self.assertEqual(get_upload_args("test.app-1.app"), {})


class PurgeTest(unittest.TestCase):
    def test_urls(self):
        urls = get_purge_urls(["b.json", "a.app"], "0.8.0", "apps", "https://cdn.example.com/")
        self.assertEqual(urls, ["https://cdn.example.com/apps/0.8.0/a.app", "https://cdn.example.com/apps/0.8.0/b.json"])

    def test_without_token_nothing_happens(self):
        keep = {name: os.environ.pop(name, None) for name in ("CLOUDFLARE_ZONE_ID", "CLOUDFLARE_PURGE_CACHE_TOKEN")}
        try:
            with tempfile.TemporaryDirectory() as directory:
                purge(directory, "0.8.0", "apps")
        finally:
            for name, value in keep.items():
                if value is not None:
                    os.environ[name] = value


class PagesTest(unittest.TestCase):
    def test_files_are_copied_to_the_bucket_layout(self):
        with tempfile.TemporaryDirectory() as source, tempfile.TemporaryDirectory() as site:
            Path(source, "index.json").write_text("{}")
            publish_pages(source, "0.8.0", site)
            self.assertTrue(Path(site, "apps", "0.8.0", "index.json").is_file())
            self.assertTrue(Path(site, ".nojekyll").is_file())


class VersionTest(unittest.TestCase):
    def test_bump(self):
        self.assertEqual(bump_version("0.10.0", "major"), "1.0.0")
        self.assertEqual(bump_version("0.10.0", "minor"), "0.11.0")
        self.assertEqual(bump_version("0.10.0", "patch"), "0.10.1")


if __name__ == "__main__":
    unittest.main()
