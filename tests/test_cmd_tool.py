"""Tests for ToolCmd."""

import argparse
import json
import time
from unittest.mock import MagicMock

from cmds.cmd_tool import ToolCmd, install_tool


class TestToolSearchSubcommand:
    """Test suite for tool search cache/sort/fetch logic."""

    def _make_cmd(self, tmp_path) -> ToolCmd:
        parser = argparse.ArgumentParser(prog="very")
        subparsers = parser.add_subparsers(dest="subcommand")
        cmd = ToolCmd(subparsers)
        cmd.CACHE_DIR = tmp_path / "cache"
        cmd.CACHE_FILE = cmd.CACHE_DIR / "tool_search_cache.json"
        return cmd

    @staticmethod
    def _sample_packages():
        return [
            {
                "name": "vtool-game",
                "description": "A game",
                "stars": 50,
                "updated": "2024-03-01",
                "language": "Vix",
                "url": "",
            },
            {
                "name": "vtool-score",
                "description": "Score tool",
                "stars": 10,
                "updated": "2024-01-15",
                "language": "Vix",
                "url": "",
            },
        ]

    # ---- sort ----
    def test_sort_by_stars(self, tmp_path):
        cmd = self._make_cmd(tmp_path)
        pkgs = self._sample_packages()
        result = cmd._sort_packages(pkgs, "stars")
        assert [p["stars"] for p in result] == [50, 10]

    def test_sort_by_name(self, tmp_path):
        cmd = self._make_cmd(tmp_path)
        pkgs = self._sample_packages()
        result = cmd._sort_packages(pkgs, "name")
        assert [p["name"] for p in result] == ["vtool-game", "vtool-score"]

    def test_sort_by_updated(self, tmp_path):
        cmd = self._make_cmd(tmp_path)
        pkgs = self._sample_packages()
        result = cmd._sort_packages(pkgs, "updated")
        assert [p["updated"] for p in result] == ["2024-03-01", "2024-01-15"]

    def test_sort_invalid_fallback(self, tmp_path):
        cmd = self._make_cmd(tmp_path)
        pkgs = self._sample_packages()
        result = cmd._sort_packages(pkgs, "unknown")
        assert [p["stars"] for p in result] == [50, 10]

    # ---- cache ----
    def test_read_cache_not_exists(self, tmp_path):
        cmd = self._make_cmd(tmp_path)
        assert cmd._read_cache() is None

    def test_read_cache_valid(self, tmp_path):
        cmd = self._make_cmd(tmp_path)
        cmd.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        packages = [{"name": "vtool-test", "stars": 1}]
        with open(cmd.CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({"timestamp": time.time(), "packages": packages}, f)
        assert cmd._read_cache() == packages

    def test_read_cache_expired(self, tmp_path):
        cmd = self._make_cmd(tmp_path)
        cmd.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(cmd.CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({"timestamp": time.time() - 7200, "packages": []}, f)
        assert cmd._read_cache() is None

    def test_read_cache_corrupted(self, tmp_path):
        cmd = self._make_cmd(tmp_path)
        cmd.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(cmd.CACHE_FILE, "w", encoding="utf-8") as f:
            f.write("{invalid")
        assert cmd._read_cache() is None

    def test_save_and_read(self, tmp_path):
        cmd = self._make_cmd(tmp_path)
        cmd.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        packages = [{"name": "vtool-test", "stars": 1}]
        cmd._save_cache(packages)
        assert cmd._read_cache() == packages

    def test_clear_cache(self, tmp_path):
        cmd = self._make_cmd(tmp_path)
        cmd.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(cmd.CACHE_FILE, "w") as f:
            json.dump({"timestamp": time.time(), "packages": []}, f)
        assert cmd.CACHE_FILE.exists()
        cmd._clear_cache()
        assert not cmd.CACHE_FILE.exists()

    def test_clear_cache_not_exists(self, tmp_path):
        cmd = self._make_cmd(tmp_path)
        cmd._clear_cache()

    # ---- fetch_github_packages ----
    @staticmethod
    def _mock_urlopen(data):
        def mock_urlopen(req, timeout=10, context=None):
            resp = MagicMock()
            resp.read.return_value = json.dumps(data).encode("utf-8")
            resp.__enter__.return_value = resp
            return resp
        return mock_urlopen

    def test_fetch_filters_vtool_only(self, tmp_path, monkeypatch):
        raw = [
            {
                "name": "vtool-game",
                "description": "Game",
                "stargazers_count": 50,
                "language": "Vix",
                "updated_at": "2024-01-15T00:00:00Z",
                "html_url": "",
            },
            {
                "name": "vlib-core",
                "description": "Core lib",
                "stargazers_count": 99,
                "language": "Vix",
                "updated_at": "2024-02-01T00:00:00Z",
                "html_url": "",
            },
        ]
        monkeypatch.setattr("urllib.request.urlopen", self._mock_urlopen(raw))
        cmd = self._make_cmd(tmp_path)
        result = cmd._fetch_github_packages()
        assert len(result) == 1
        assert result[0]["name"] == "vtool-game"

    def test_fetch_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr("urllib.request.urlopen", self._mock_urlopen([]))
        cmd = self._make_cmd(tmp_path)
        result = cmd._fetch_github_packages()
        assert result == []

    # ---- display_results ----
    def test_display_results(self, tmp_path, capsys):
        cmd = self._make_cmd(tmp_path)
        packages = [
            {
                "name": "vtool-game",
                "description": "A game",
                "stars": 50,
                "updated": "2024-03-01",
                "language": "Vix",
                "url": "",
            },
        ]
        cmd._display_results(packages, "stars")
        out, _ = capsys.readouterr()
        assert "game" in out
        assert "A game" in out

    def test_display_results_non_vtool_name(self, tmp_path, capsys):
        cmd = self._make_cmd(tmp_path)
        packages = [
            {
                "name": "other-tool",
                "description": "Desc",
                "stars": 5,
                "updated": "2024-03-01",
                "language": "Vix",
                "url": "",
            },
        ]
        cmd._display_results(packages, "name")
        out, _ = capsys.readouterr()
        assert "other-tool" in out

    # ---- cache status ----
    def test_cache_status_no_cache(self, tmp_path, capsys):
        cmd = self._make_cmd(tmp_path)
        cmd._show_cache_status()
        out, _ = capsys.readouterr()
        assert "缓存文件不存在" in out

    def test_cache_status_valid(self, tmp_path, capsys):
        cmd = self._make_cmd(tmp_path)
        cmd.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(cmd.CACHE_FILE, "w") as f:
            json.dump({"timestamp": time.time(), "packages": [{"name": "vtool-test"}]}, f)
        cmd._show_cache_status()
        out, _ = capsys.readouterr()
        assert "有效" in out

    def test_cache_status_expired(self, tmp_path, capsys):
        cmd = self._make_cmd(tmp_path)
        cmd.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(cmd.CACHE_FILE, "w") as f:
            json.dump({"timestamp": time.time() - 7200, "packages": []}, f)
        cmd._show_cache_status()
        out, _ = capsys.readouterr()
        assert "已过期" in out

    # ---- execute ----
    def test_execute_clear_cache(self, tmp_path, capsys):
        cmd = self._make_cmd(tmp_path)
        cmd.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(cmd.CACHE_FILE, "w") as f:
            json.dump({"timestamp": time.time(), "packages": []}, f)
        ns = argparse.Namespace(
            tool_subcommand="__unused",
            package="",
            keyword="",
            no_cache=False,
            clear_cache=True,
            cache_status=False,
            sort="stars",
            limit=None,
        )
        cmd.namespace = ns
        cmd._cmd_search()
        assert not cmd.CACHE_FILE.exists()

    def test_execute_cache_status_cmd(self, tmp_path, capsys):
        cmd = self._make_cmd(tmp_path)
        cmd.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(cmd.CACHE_FILE, "w") as f:
            json.dump({"timestamp": time.time(), "packages": [{"name": "vtool-test"}]}, f)
        ns = argparse.Namespace(
            tool_subcommand="__unused",
            package="",
            keyword="",
            no_cache=False,
            clear_cache=False,
            cache_status=True,
            sort="stars",
            limit=None,
        )
        cmd.namespace = ns
        cmd._cmd_search()
        out, _ = capsys.readouterr()
        assert "有效" in out
