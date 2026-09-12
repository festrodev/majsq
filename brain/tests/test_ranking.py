"""Which three events a group is shown, and why.

The rules here are the ones that make the recommender look broken when they
regress — a repeated title, a group sent somewhere one member hates, a member's
history leaking into a group message.
"""

from django.test import TestCase

from brain import ranking


def event(title, *, tags=(), venue="", organizer=""):
    return {
        "title": title,
        "tags": list(tags),
        "venue_name": venue,
        "organizer_slug": organizer,
        "start_datetime": "2026-09-13T23:00:00+00:00",
    }


class ChooseTests(TestCase):
    def test_never_shows_the_same_title_twice(self):
        """A recurring series on two nights reads as a broken recommender.

        The venue rule is relaxed when the field is thin; the title rule never
        is, which is the distinction this pins.
        """
        events = [event("Alice in Wonderland", venue="Grands Ballets") for _ in range(4)]
        events.append(event("Lady Chatterley", venue="Grands Ballets"))
        picks = ranking.choose(events, [], count=3)
        titles = [p["title"] for p in picks]
        self.assertEqual(len(titles), len(set(titles)))

    def test_prefers_one_venue_per_pick_when_it_can(self):
        events = [
            event("A", venue="Newspeak"),
            event("B", venue="Newspeak"),
            event("C", venue="MTELUS"),
            event("D", venue="Le Ritz"),
        ]
        venues = [p["venue_name"] for p in ranking.choose(events, [], count=3)]
        self.assertEqual(len(venues), len(set(venues)))

    def test_the_minimum_term_beats_a_bare_majority(self):
        """0.7*mean + 0.3*min, and the min term has to actually change a pick.

        The obvious version of this test does not work: give four people four
        disjoint single-genre tastes and NO event pleases everyone, so `min` is
        zero for every candidate, the mean decides, and the event three of them
        love correctly wins. That is the ranker working, not failing.

        To isolate the min term you need a candidate everyone likes a little.
        Here "Live" sits in all four profiles at a lower weight, so:

            Metal Night  mean .45  min 0    -> 0.7*.45 + 0.3*0   = .315
            Live Session mean .36  min .36  -> 0.7*.36 + 0.3*.36 = .36

        On mean alone Metal Night would win (.45 > .36). The min term is the
        whole reason the group does not get sent somewhere one of them hates.
        """

        def profile(main):
            return ranking.Taste.from_profile(
                {"taste": {"tags": [{"tag": main, "weight": 10}, {"tag": "Live", "weight": 6}]}}
            )

        tastes = [profile("Metal"), profile("Metal"), profile("Metal"), profile("Pop")]
        metal = event("Metal Night", tags=["Metal"])
        common = event("Live Session", tags=["Live"])

        mean_only = sum(ranking.affinity(metal, t) for t in tastes) / len(tastes)
        self.assertGreater(
            mean_only,
            sum(ranking.affinity(common, t) for t in tastes) / len(tastes),
            "the premise: on mean alone the majority pick wins",
        )
        self.assertGreater(ranking.group_score(common, tastes), ranking.group_score(metal, tastes))
        self.assertEqual(
            ranking.choose([metal, common], tastes, count=1)[0]["title"], "Live Session"
        )

    def test_a_group_reason_never_names_a_member(self):
        """A link made in a DM must not disclose anything in a group."""
        tastes = [
            ranking.Taste.from_stated(tags=["Jazz"], label="Ali"),
            ranking.Taste.from_stated(tags=["Jazz"], label="Sam"),
            ranking.Taste.from_stated(tags=["Rock"], label="Max"),
        ]
        why = ranking.reasons(event("Trio", tags=["Jazz"]), tastes, locale="fr")
        self.assertIn("2 sur 3", why)
        for name in ("Ali", "Sam", "Max"):
            self.assertNotIn(name, why)

    def test_a_dm_reason_may_be_personal(self):
        taste = [ranking.Taste.from_stated(tags=["Jazz"], label="Ali")]
        why = ranking.reasons(event("Trio", tags=["Jazz"]), taste, locale="fr", private=True)
        self.assertIn("tu aimes", why)

    def test_a_prolific_history_does_not_dominate_a_light_one(self):
        """Weights normalize to 0..1, so 200 saves does not outvote 3."""
        heavy = ranking.Taste.from_profile({"taste": {"tags": [{"tag": "Techno", "weight": 200}]}})
        light = ranking.Taste.from_profile({"taste": {"tags": [{"tag": "Jazz", "weight": 3}]}})
        self.assertEqual(max(heavy.tags.values()), max(light.tags.values()))

    def test_no_tastes_still_returns_picks(self):
        """A group where nobody connected still gets an answer."""
        events = [event("A", venue="X"), event("B", venue="Y"), event("C", venue="Z")]
        self.assertEqual(len(ranking.choose(events, [], count=3)), 3)

    def test_empty_candidates_returns_nothing(self):
        self.assertEqual(ranking.choose([], [], count=3), [])
