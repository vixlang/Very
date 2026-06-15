"""Tests for SearchCmd."""

import argparse
import json
import time
from unittest.mock import MagicMock

from cmds.cmd_search import SearchCmd


class TestSearchCmd:
    """Test suite for SearchCmd."""

    # -----------------------------------------------------------------------
    #  helpers
    # -----------------------------------------------------------------------

    def _make_cmd(self, tmp_path) -> SearchCmd:
        """Return a SearchCmd instance whose cache paths point at *tmp_path*."""
        parser = argparse.ArgumentParser(prog="very")
        subparsers = parser.add_subparsers(dest="subcommand")
        cmd = SearchCmd(subparsers)
        cmd.CACHE_DIR = tmp_path / "cache"
        cmd.CACHE_FILE = cmd.CACHE_DIR / "search_cache.json"
        return cmd

    @staticmethod
    def _sample_packages():
        return [
            {
                "name": "vlib-zeta",
                "description": "Zeta lib",
                "stars": 5,
                "updated": "2024-03-01",
                "language": "Vix",
                "url": "",
            },
            {
                "name": "vlib-alpha",
                "description": "Alpha lib",
                "stars": 42,
                "updated": "2024-01-15",
                "language": "Vix",
                "url": "",
            },
            {
                "name": "vlib-beta",
                "description": "Beta lib",
                "stars": 10,
                "updated": "2024-02-01",
                "language": "Vix",
                "url": "",
            },
        ]

    # -----------------------------------------------------------------------
    #  sort_packages
    # -----------------------------------------------------------------------

    def test_sort_by_stars(self, tmp_path):
        cmd = self._make_cmd(tmp_path)
        pkgs = self._sample_packages()
        result = cmd.sort_packages(pkgs, "stars")
        stars = [p["stars"] for p in result]
        assert stars == [42, 10, 5]

    def test_sort_by_updated(self, tmp_path):
        cmd = self._make_cmd(tmp_path)
        pkgs = self._sample_packages()
        result = cmd.sort_packages(pkgs, "updated")
        updated = [p["updated"] for p in result]
        assert updated == ["2024-03-01", "2024-02-01", "2024-01-15"]

    def test_sort_by_name(self, tmp_path):
        cmd = self._make_cmd(tmp_path)
        pkgs = self._sample_packages()
        result = cmd.sort_packages(pkgs, "name")
        names = [p["name"] for p in result]
        assert names == ["vlib-alpha", "vlib-beta", "vlib-zeta"]

    def test_sort_invalid_fallback_to_stars(self, tmp_path):
        cmd = self._make_cmd(tmp_path)
        pkgs = self._sample_packages()
        result = cmd.sort_packages(pkgs, "unknown_field")
        stars = [p["stars"] for p in result]
        assert stars == [42, 10, 5]

    # -----------------------------------------------------------------------
    #  read_cache
    # -----------------------------------------------------------------------

    def test_read_cache_file_not_exists(self, tmp_path):
        cmd = self._make_cmd(tmp_path)
        assert cmd.read_cache() is None

    def test_read_cache_valid(self, tmp_path):
        cmd = self._make_cmd(tmp_path)
        cmd.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        packages = [{"name": "vlib-test", "stars": 1}]
        cache_data = {"timestamp": time.time(), "packages": packages}
        with open(cmd.CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache_data, f)
        result = cmd.read_cache()
        assert result == packages

    def test_read_cache_expired(self, tmp_path):
        cmd = self._make_cmd(tmp_path)
        cmd.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_data = {
            "timestamp": time.time() - 7200,
            "packages": [{"name": "vlib-test", "stars": 1}],
        }
        with open(cmd.CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache_data, f)
        assert cmd.read_cache() is None

    def test_read_cache_corrupted(self, tmp_path):
        cmd = self._make_cmd(tmp_path)
        cmd.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(cmd.CACHE_FILE, "w", encoding="utf-8") as f:
            f.write("{invalid")
        assert cmd.read_cache() is None

    def test_read_cache_missing_timestamp(self, tmp_path):
        cmd = self._make_cmd(tmp_path)
        cmd.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(cmd.CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({"packages": []}, f)
        assert cmd.read_cache() is None

    # -----------------------------------------------------------------------
    #  save_cache
    # -----------------------------------------------------------------------

    def test_save_cache(self, tmp_path):
        cmd = self._make_cmd(tmp_path)
        cmd.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        packages = [{"name": "vlib-test", "stars": 1}]
        cmd.save_cache(packages)
        assert cmd.CACHE_FILE.exists()
        with open(cmd.CACHE_FILE, encoding="utf-8") as f:
            data = json.load(f)
        assert "timestamp" in data
        assert data["packages"] == packages

    def test_save_cache_readable(self, tmp_path):
        cmd = self._make_cmd(tmp_path)
        cmd.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        packages = [{"name": "vlib-test", "stars": 1}]
        cmd.save_cache(packages)
        with open(cmd.CACHE_FILE, encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data["timestamp"], (int, float))
        assert data["packages"] == packages

    # -----------------------------------------------------------------------
    #  clear_cache
    # -----------------------------------------------------------------------

    def test_clear_cache_exists(self, tmp_path, capsys):
        cmd = self._make_cmd(tmp_path)
        cmd.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(cmd.CACHE_FILE, "w") as f:
            json.dump({"timestamp": time.time(), "packages": []}, f)
        assert cmd.CACHE_FILE.exists()
        cmd.clear_cache()
        assert not cmd.CACHE_FILE.exists()
        out, _err = capsys.readouterr()
        assert "缓存已清理" in out

    def test_clear_cache_not_exists(self, tmp_path, capsys):
        cmd = self._make_cmd(tmp_path)
        cmd.clear_cache()
        out, _err = capsys.readouterr()
        assert "无需清理" in out

    # -----------------------------------------------------------------------
    #  fetch_github_packages
    # -----------------------------------------------------------------------

    def _mock_github_urlopen(self, data):
        """Return a mock for ``urllib.request.urlopen`` that yields *data*."""

        def mock_urlopen(req, timeout=10, context=None):
            response = MagicMock()
            response.read.return_value = json.dumps(data).encode("utf-8")
            response.__enter__.return_value = response
            return response

        return mock_urlopen

    def test_fetch_github_packages(self, tmp_path, monkeypatch):
        raw_repos = [
            {
                "name": "vlib-vnet",
                "description": "A Vix networking lib",
                "stargazers_count": 42,
                "language": "Vix",
                "updated_at": "2024-01-15T00:00:00Z",
                "html_url": "https://github.com/vixlang/vlib-vnet",
            },
            {
                "name": "vlib-core",
                "description": "Core library",
                "stargazers_count": 99,
                "language": "Vix",
                "updated_at": "2024-02-01T00:00:00Z",
                "html_url": "https://github.com/vixlang/vlib-core",
            },
            {
                "name": "not-a-vix-pkg",
                "description": "Should be filtered out",
                "stargazers_count": 10,
                "language": "Python",
                "updated_at": "2024-03-01T00:00:00Z",
                "html_url": "https://github.com/vixlang/not-a-vix-pkg",
            },
        ]
        monkeypatch.setattr(
            "urllib.request.urlopen", self._mock_github_urlopen(raw_repos)
        )
        cmd = self._make_cmd(tmp_path)
        result = cmd.fetch_github_packages()
        names = [p["name"] for p in result]
        assert names == ["vlib-core", "vlib-vnet"]
        assert result[0]["stars"] == 99
        assert result[1]["stars"] == 42

    def test_fetch_github_packages_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr("urllib.request.urlopen", self._mock_github_urlopen([]))
        cmd = self._make_cmd(tmp_path)
        result = cmd.fetch_github_packages()
        assert result == []

    def test_fetch_github_packages_includes_ver(self, tmp_path, monkeypatch):
        raw_repos = [
            {
                "name": "ver",
                "description": "Vix compiler",
                "stargazers_count": 200,
                "language": "Vix",
                "updated_at": "2024-01-15T00:00:00Z",
                "html_url": "https://github.com/vixlang/ver",
            },
        ]
        monkeypatch.setattr(
            "urllib.request.urlopen", self._mock_github_urlopen(raw_repos)
        )
        cmd = self._make_cmd(tmp_path)
        result = cmd.fetch_github_packages()
        assert len(result) == 1
        assert result[0]["name"] == "ver"

    # -----------------------------------------------------------------------
    #  execute – special flags
    # -----------------------------------------------------------------------

    def test_execute_clear_cache(self, tmp_path, capsys):
        cmd = self._make_cmd(tmp_path)
        cmd.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(cmd.CACHE_FILE, "w") as f:
            json.dump({"timestamp": time.time(), "packages": []}, f)
        assert cmd.CACHE_FILE.exists()
        ns = argparse.Namespace(
            keyword="",
            no_cache=False,
            clear_cache=True,
            cache_status=False,
            sort="stars",
            limit=None,
        )
        cmd.namespace = ns
        cmd.execute()
        assert not cmd.CACHE_FILE.exists()
        out, _err = capsys.readouterr()
        assert "缓存已清理" in out

    def test_execute_cache_status(self, tmp_path, capsys):
        cmd = self._make_cmd(tmp_path)
        cmd.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        packages = [{"name": "vlib-test", "stars": 1}]
        with open(cmd.CACHE_FILE, "w") as f:
            json.dump({"timestamp": time.time(), "packages": packages}, f)
        ns = argparse.Namespace(
            keyword="",
            no_cache=False,
            clear_cache=False,
            cache_status=True,
            sort="stars",
            limit=None,
        )
        cmd.namespace = ns
        cmd.execute()
        out, _err = capsys.readouterr()
        assert "缓存状态" in out
        assert "有效" in out
