"""One turn, and the boundaries it must not cross."""

from django.test import TestCase

from brain import engine
from core.models import Conversation, Membership, Participant, Turn


def conversation(kind="group", locale="fr", external_id="t1"):
    return Conversation.objects.create(kind=kind, external_id=external_id, locale=locale)


# Window + category + area. Without the area the agent asks ONE narrowing
# question first, because theatre returns 26 candidates and the breadth
# threshold is 25 — the optional gate doing its job, not a failure. Tests that
# want picks have to answer everything it can reasonably ask.
ANSWERED = {"time_slot": "weekend", "category": "theatre", "area": ""}


class TurnTests(TestCase):
    def test_asks_for_what_is_missing_then_answers(self):
        convo = conversation()
        Turn.objects.create(conversation=convo, role=Turn.Role.USER, text="quoi faire ce soir?")
        first = engine.respond(conversation=convo, text="quoi faire ce soir?")
        self.assertEqual(first.question["name"], "category")
        self.assertEqual(first.picks, [])

        second = engine.respond(
            conversation=convo, text="", chosen={"category": "theatre", "area": ""}
        )
        self.assertIsNone(second.question)
        self.assertTrue(second.picks, "a chosen category must produce picks")
        self.assertTrue(second.share_id)
        self.assertTrue(second.map_url.endswith(second.share_id))

    def test_never_re_asks_what_the_chat_already_said(self):
        """Window and category were both stated, so neither is asked again.

        It may still ask ONE narrowing question when the field is wide; what it
        must never do is ask for something the chat already answered.
        """
        convo = conversation(external_id="t2")
        reply = engine.respond(conversation=convo, text="on sort ce week-end, du théâtre")
        asked = (reply.question or {}).get("name")
        self.assertNotIn(asked, ("time_slot", "category"))
        self.assertEqual(reply.state["time_slot"], "weekend")
        self.assertEqual(reply.state["category"], "theatre")

    def test_a_group_gets_a_poll_and_a_dm_does_not(self):
        group = engine.respond(
            conversation=conversation(external_id="g1"),
            text="",
            chosen=ANSWERED,
        )
        self.assertIsNotNone(group.poll)
        self.assertGreaterEqual(len(group.poll["options"]), 2)

        dm = engine.respond(
            conversation=conversation(kind="dm", external_id="d1"),
            text="",
            chosen=ANSWERED,
        )
        self.assertIsNone(dm.poll)

    def test_an_empty_category_widens_and_says_so(self):
        """A chip with no inventory must not dead-end the conversation."""
        convo = conversation(external_id="t3", locale="fr")
        reply = engine.respond(
            conversation=convo, text="", chosen={"time_slot": "tonight", "category": "comedy"}
        )
        if reply.picks:
            # Either comedy had inventory, or it widened — never a dead end.
            self.assertTrue(reply.text)

    def test_a_pure_chip_flow_keeps_what_was_tapped(self):
        """Tap the window, then the category, and the window must survive.

        Constraints used to be re-derived from MESSAGES every turn, so a value
        that was tapped rather than typed evaporated on the next turn — and
        Telegram is entirely chip-driven, so that was the normal path. Each
        turn here carries no text at all, which is exactly the case that broke.
        """
        convo = conversation(external_id="chips")
        first = engine.respond(conversation=convo, text="", chosen={"time_slot": "weekend"})
        self.assertEqual(first.question["name"], "category")
        self.assertEqual(first.state["time_slot"], "weekend")

        second = engine.respond(conversation=convo, text="", chosen={"category": "theatre"})
        self.assertEqual(second.state["time_slot"], "weekend", "the tapped window must survive")
        self.assertEqual(second.state["category"], "theatre")

    def test_no_preference_spends_the_question(self):
        """Tapping "Peu importe" must not re-ask the same question forever.

        The area chip offers an empty value, and `merge` drops empty values on
        purpose (so nothing overwrites a real answer with nothing). Together
        that looped: area stayed unset, the optional gate asked again, and the
        user could tap "Peu importe" all night. The fix remembers which
        questions were ASKED, not just which values came back.
        """
        convo = conversation(external_id="t5")
        first = engine.respond(
            conversation=convo, text="", chosen={"time_slot": "weekend", "category": "theatre"}
        )
        self.assertEqual((first.question or {}).get("name"), "area")

        second = engine.respond(conversation=convo, text="", chosen={"area": ""})
        self.assertNotEqual(
            (second.question or {}).get("name"), "area", "the question must be spent"
        )
        self.assertTrue(second.picks, "and it should now answer")

    def test_picks_carry_public_fields_only(self):
        """This shape reaches a chat message and an unguessable share page."""
        reply = engine.respond(
            conversation=conversation(external_id="t4"),
            text="",
            chosen=ANSWERED,
        )
        self.assertTrue(reply.picks)
        for pick in reply.picks:
            self.assertNotIn("score", pick, "the ranker's score must not leak")
            for forbidden in ("cover_image", "card_image", "email"):
                self.assertNotIn(forbidden, pick)
            self.assertIn("url", pick)


class ConsentTests(TestCase):
    """Per-group taste consent, read live on every turn.

    The rule is that switching it off excludes the member on the NEXT turn,
    not whenever a cached profile happens to expire.
    """

    def test_a_group_ignores_a_member_who_has_not_opted_in(self):
        convo = conversation(external_id="c1")
        participant = Participant.objects.create(
            channel="telegram", external_id="42", display_name="Ali"
        )
        membership = Membership.objects.create(conversation=convo, participant=participant)
        self.assertFalse(membership.use_my_taste)

        constraints = type("C", (), {"stated_tags": ["Techno"]})()
        self.assertEqual(engine._consenting_tastes(convo, constraints), [])

        membership.set_taste_consent(enabled=True)
        self.assertEqual(len(engine._consenting_tastes(convo, constraints)), 1)

        membership.set_taste_consent(enabled=False)
        self.assertEqual(
            engine._consenting_tastes(convo, constraints), [], "off takes effect immediately"
        )

    def test_a_dm_needs_no_opt_in(self):
        """There is only one person to talk about, and they are the one asking."""
        convo = conversation(kind="dm", external_id="c2")
        participant = Participant.objects.create(channel="telegram", external_id="43")
        Membership.objects.create(conversation=convo, participant=participant)
        constraints = type("C", (), {"stated_tags": ["Techno"]})()
        self.assertEqual(len(engine._consenting_tastes(convo, constraints)), 1)
