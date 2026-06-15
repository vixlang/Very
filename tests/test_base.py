"""Tests for cmds/base.py"""

import argparse

import pytest

from cmds.base import Command


class _TestCommand(Command):
    NAME = "test-cmd"

    def set_parser(self, p):
        return p.add_parser(self.NAME, help="test")

    def execute(self):
        pass


class TestCommand:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            Command(None)

    def test_name_property_returns_name(self):
        parser = argparse.ArgumentParser(prog="test")
        sub = parser.add_subparsers()
        cmd = _TestCommand(sub)
        assert cmd.name == "test-cmd"

    def test_namespace_defaults_to_none(self):
        parser = argparse.ArgumentParser(prog="test")
        sub = parser.add_subparsers()
        cmd = _TestCommand(sub)
        assert cmd.namespace is None
