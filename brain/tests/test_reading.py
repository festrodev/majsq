"""What the agent understands from what people actually type.

Extraction is a regex pass, not a model call, so it runs identically on every
turn in both transports whether or not a model key is configured. That makes it
cheap to test and expensive to get wrong silently.
"""

from django.test import TestCase

from brain import reading


class ExtractTests(TestCase):
    def test_reads_a_whole_group_message(self):
        found = reading.extract(
            ["salut", "on est 6, quoi faire ce soir?", "genre danser, pas cher, plateau"]
        )
        self.assertEqual(found.time_slot, "tonight")
        self.assertEqual(found.band, "evening")
        self.assertEqual(found.category, "nightlife")
        self.assertEqual(found.area, "Plateau")
        self.assertEqual(found.party_size, 6)

    def test_english_works_too(self):
        found = reading.extract(["we are 4, what should we do this weekend? something dance"])
        self.assertEqual(found.time_slot, "weekend")
        self.assertEqual(found.category, "dance")
        self.assertEqual(found.party_size, 4)

    def test_tomorrow_evening_is_not_tonight(self):
        """Order matters in the slot patterns: 'demain soir' has both words."""
        found = reading.extract(["demain soir?"])
        self.assertEqual(found.time_slot, "tomorrow")
        self.assertEqual(found.band, "evening")

    def test_a_later_correction_wins(self):
        found = reading.extract(["ce soir?", "non, plutôt samedi"])
        self.assertEqual(found.time_slot, "weekend")

    def test_free_is_an_answer_to_the_category_question(self):
        """Someone asking for free ideas has chosen a chip; don't ask again."""
        found = reading.extract(["des idées gratuites ce week-end?"])
        self.assertTrue(found.free_only)
        self.assertEqual(found.category, "free")
        self.assertEqual(reading.required(found), [])

    def test_budget_in_both_phrasings(self):
        self.assertEqual(reading.extract(["moins de 20$"]).budget_max, 20)
        self.assertEqual(reading.extract(["under 50"]).budget_max, 50)


class GateTests(TestCase):
    """The two gates must stay separate.

    When they were one function, calling it without a candidate count made an
    optional question look required, and the agent asked about the
    neighbourhood before it had searched anything.
    """

    def test_window_and_category_are_required(self):
        self.assertEqual(reading.required(reading.Constraints()), ["time_slot", "category"])
        self.assertEqual(reading.required(reading.Constraints(time_slot="tonight")), ["category"])
        self.assertEqual(
            reading.required(reading.Constraints(time_slot="tonight", category="live")), []
        )

    def test_optional_needs_a_candidate_count(self):
        ready = reading.Constraints(time_slot="tonight", category="live")
        # A narrow field earns no further question.
        self.assertEqual(reading.optional(ready, candidate_count=3), [])
        # A wide one earns exactly one.
        self.assertEqual(reading.optional(ready, candidate_count=200), ["area"])

    def test_optional_asks_nothing_while_required_is_outstanding(self):
        self.assertEqual(reading.optional(reading.Constraints(), candidate_count=999), [])

    def test_never_more_than_one_optional_question(self):
        ready = reading.Constraints(time_slot="tonight", category="live")
        self.assertLessEqual(len(reading.optional(ready, candidate_count=999)), 1)
