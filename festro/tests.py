"""Festro client tests."""

from django.test import TestCase, override_settings

from festro.client import event_url


class EventUrlTests(TestCase):
    """The link the bot puts in front of a real person.

    This was `/e/<short_id>` for a whole day and 404s on festro.com — every
    pick the bot sent carried a dead link, and nothing caught it because the
    agent builds the URL and never fetches it. The path is asserted literally
    here: a test that rebuilt the URL from the same f-string would have passed
    just as happily while being just as wrong.
    """

    @override_settings(FESTRO_SITE_BASE="https://festro.com")
    def test_event_url_uses_the_events_path(self):
        self.assertEqual(event_url("r9e340uq"), "https://festro.com/events/r9e340uq")

    @override_settings(FESTRO_SITE_BASE="https://festro.com")
    def test_event_url_is_not_the_old_short_path(self):
        self.assertNotIn("/e/", event_url("r9e340uq"))

    @override_settings(FESTRO_SITE_BASE="https://staging.festro.com")
    def test_event_url_follows_the_configured_base(self):
        self.assertTrue(event_url("abc").startswith("https://staging.festro.com/events/"))
