"""Tests for core management commands."""

from __future__ import annotations

from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase


class CheckCategoriesCommandTests(SimpleTestCase):
    @patch("core.management.commands.check_categories.search.category_counts")
    def test_prints_counts_and_unfiltered_surprise(self, category_counts):
        category_counts.return_value = {"live": 7, "theatre": 3}
        output = StringIO()

        call_command("check_categories", "--when", "tonight", stdout=output)

        category_counts.assert_called_once_with(time_slot="tonight", band=None)
        rendered = output.getvalue()
        self.assertIn("Category inventory for tonight", rendered)
        self.assertIn("live (Concerts): 7", rendered)
        self.assertIn("theatre (Théâtre): 3", rendered)
        self.assertIn("surprise (Surprends-moi): n/a (unfiltered)", rendered)

    @patch("core.management.commands.check_categories.search.category_counts")
    def test_forwards_optional_band(self, category_counts):
        category_counts.return_value = {}

        call_command(
            "check_categories",
            "--when",
            "today",
            "--band",
            "evening",
            stdout=StringIO(),
        )

        category_counts.assert_called_once_with(time_slot="today", band="evening")

    def test_rejects_unknown_window(self):
        with self.assertRaisesMessage(CommandError, "Unsupported --when value"):
            call_command(
                "check_categories",
                "--when",
                "someday",
                stdout=StringIO(),
            )
