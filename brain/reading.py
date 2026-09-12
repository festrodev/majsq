"""Read the conversation before asking anything.

The product rule from Ali: *read the chat, then ask more questions only if
needed*. So this module does two things, in this order:

1. ``extract`` — pull constraints the group already stated, from their own
   messages. In a DM that is the thread; in a group it is the recent
   messages. Whatever is found here is a question that must NOT be asked.
2. ``missing`` — decide what is still unknown and worth one more question.

Extraction is deliberately a regex pass, not a model call: it runs on every
turn, in both transports, and must be fast, free, and identical whether or not
a model key is configured. The model refines what this finds; it is not
trusted to do the finding.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

from brain import categories, slots

# Montréal neighbourhoods people actually name when choosing a night out.
_AREAS = {
    "plateau": "Plateau",
    "mile end": "Mile End",
    "mile-end": "Mile End",
    "centre-ville": "Centre-ville",
    "downtown": "Centre-ville",
    "vieux-port": "Vieux-Port",
    "vieux port": "Vieux-Port",
    "old port": "Vieux-Port",
    "griffintown": "Griffintown",
    "verdun": "Verdun",
    "rosemont": "Rosemont",
    "hochelaga": "Hochelaga",
    "villeray": "Villeray",
    "outremont": "Outremont",
    "ndg": "NDG",
    "saint-henri": "Saint-Henri",
    "quartier latin": "Quartier latin",
}

_FREE = re.compile(r"\b(gratuits?|gratuites?|free|no cover|sans frais)\b", re.I)
_BUDGET = re.compile(r"(?:moins de|under|max|budget|sous)\s*\$?\s*(\d{1,3})\s*\$?", re.I)
_BUDGET_ALT = re.compile(r"\$\s?(\d{1,3})\b")
_PARTY_SIZE = re.compile(
    r"\b(?:on est|nous sommes|we are|we're|there(?:'s| are))\s+(\d{1,2})\b", re.I
)
_PARTY_SIZE_ALT = re.compile(r"\b(\d{1,2})\s*(?:personnes|people|amis|friends|pax)\b", re.I)

# Slot words in both languages. Order matters: "demain soir" must read as
# tomorrow + evening, not as tonight.
_SLOT_WORDS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b(après-demain|day after tomorrow)\b", re.I), "week"),
    (re.compile(r"\b(demain|tomorrow)\b", re.I), "tomorrow"),
    (re.compile(r"\b(ce soir|tonight|à soir|asoir)\b", re.I), "tonight"),
    (
        re.compile(r"\b(week-?end|fin de semaine|samedi|saturday|dimanche|sunday)\b", re.I),
        "weekend",
    ),
    (re.compile(r"\b(cette semaine|this week|semaine)\b", re.I), "week"),
]

_BAND_WORDS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b(après-midi|afternoon|aprem)\b", re.I), "afternoon"),
    (re.compile(r"\b(tard|late|after ?hours|nuit)\b", re.I), "late"),
    (re.compile(r"\b(soir|soirée|evening|tonight|night)\b", re.I), "evening"),
]

# Words that point at a category chip. Kept next to the chips themselves so a
# new category means one edit in `categories.py` plus one line here.
_CATEGORY_WORDS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b(danser|dancing|club|techno|house|dj|rave|party|beat)\b", re.I), "nightlife"),
    (re.compile(r"\b(concert|show|spectacle|band|groupe|live)\b", re.I), "live"),
    (re.compile(r"\b(théâtre|theatre|theater|pièce|play)\b", re.I), "theatre"),
    (re.compile(r"\b(danse|ballet|contemporain|dance)\b", re.I), "dance"),
    (re.compile(r"\b(classique|classical|opéra|opera|orchestre|symphon)\w*\b", re.I), "classical"),
    (re.compile(r"\b(humour|comedy|comédie|stand-?up|impro|rire)\b", re.I), "comedy"),
    (re.compile(r"\b(festival|fest)\b", re.I), "festival"),
]


@dataclass
class Constraints:
    """Everything the agent knows about what this group wants tonight."""

    time_slot: str | None = None
    band: str | None = None
    category: str | None = None
    area: str | None = None
    budget_max: int | None = None
    free_only: bool = False
    party_size: int | None = None
    stated_tags: list[str] = field(default_factory=list)
    # Optional questions already put to this conversation. "Peu importe" is a
    # real answer, but it carries an empty value that `merge` drops — so
    # without remembering that the question was ASKED, the agent asks it again
    # on the next turn, forever. Tracking the question rather than the value is
    # what makes "no preference" expressible at all.
    answered: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)

    def merge(self, other: Constraints) -> Constraints:
        """Later statements win, but never overwrite something with nothing."""
        merged = Constraints(**self.as_dict())
        for key, value in other.as_dict().items():
            if key == "answered":
                # Unions, never replaces: a question answered three turns ago
                # is still answered.
                merged.answered = sorted(set(merged.answered) | set(value or []))
                continue
            if value in (None, False, [], ""):
                continue
            setattr(merged, key, value)
        return merged


def extract(messages: list[str]) -> Constraints:
    """Read constraints out of what people actually wrote.

    Messages are processed oldest to newest so a later correction ("non,
    plutôt samedi") overrides an earlier statement.
    """
    found = Constraints()
    for message in messages:
        text = message or ""
        current = Constraints()

        for pattern, slot_key in _SLOT_WORDS:
            if pattern.search(text):
                current.time_slot = slot_key
                break
        for pattern, band in _BAND_WORDS:
            if pattern.search(text):
                current.band = band
                break
        for pattern, category_key in _CATEGORY_WORDS:
            if pattern.search(text):
                current.category = category_key
                break

        lowered = text.lower()
        for needle, label in _AREAS.items():
            if needle in lowered:
                current.area = label
                break

        if _FREE.search(text):
            current.free_only = True
        budget = _BUDGET.search(text) or _BUDGET_ALT.search(text)
        if budget:
            current.budget_max = int(budget.group(1))
        size = _PARTY_SIZE.search(text) or _PARTY_SIZE_ALT.search(text)
        if size:
            current.party_size = int(size.group(1))

        found = found.merge(current)

    # "gratuit" is an answer to "what kind?", not just a budget: someone who
    # asks for free ideas has chosen the Free chip and must not be asked again.
    if found.free_only and not found.category:
        found.category = "free"

    # A stated category is also a stated taste — it feeds ranking for people
    # who have no Festro history.
    category = categories.get(found.category)
    if category and category.tags:
        found.stated_tags = list(category.tags)
    return found


# ---------------------------------------------------------------------------
# What is worth one more question.
#
# ⚠️ PRODUCT CALL — this gate decides how chatty maj$q is. The window is the
# only thing genuinely required: without it there is no catalog query at all.
# Everything else is a trade: asking narrows the picks, but every question is
# another tap between "quoi faire ce soir?" and three suggestions, and in a
# group each question costs the whole room's attention.
#
# The default below asks for the window, then the category, then stops — at
# most ONE optional question, and only when the catalog is too broad to be
# useful. Widen it (ask about area, budget, party size) if the picks feel
# generic; tighten it to window-only if the demo feels like an interrogation.
# `MAX_OPTIONAL_QUESTIONS` is the dial.
# ---------------------------------------------------------------------------
MAX_OPTIONAL_QUESTIONS = 1

# Below this many candidates the picks are already specific; asking more only
# costs taps. Above it, one narrowing question genuinely improves the answer.
BROAD_CANDIDATE_THRESHOLD = 25


def required(constraints: Constraints) -> list[str]:
    """Questions that must be answered before a search is even possible.

    Only two. Without a window there is no valid catalog query at all, and
    without a category "surprise me" is a choice the user should make rather
    than one made for them.
    """
    questions: list[str] = []
    if not constraints.time_slot:
        questions.append("time_slot")
    if not constraints.category:
        questions.append("category")
    return questions


def optional(constraints: Constraints, *, candidate_count: int) -> list[str]:
    """Narrowing questions worth asking once we know how wide the field is.

    Kept separate from :func:`required` on purpose. When both lived in one
    function, calling it without a candidate count made an optional question
    look required, and the agent asked "un coin en particulier ?" *before*
    searching — a question it had no reason to ask and could not yet justify.
    The signature now makes that mistake impossible: you cannot ask for
    optional questions without saying how many candidates you have.
    """
    if required(constraints):
        return []
    if candidate_count <= BROAD_CANDIDATE_THRESHOLD:
        return []

    narrowing: list[str] = []
    if not constraints.area:
        narrowing.append("area")
    elif not (constraints.budget_max or constraints.free_only):
        narrowing.append("budget")
    # Never ask the same optional question twice. Whatever they tapped — a
    # neighbourhood or "peu importe" — the question is spent.
    already = set(constraints.answered or [])
    return [name for name in narrowing if name not in already][:MAX_OPTIONAL_QUESTIONS]


def question_chips(name: str, *, locale: str = "fr") -> dict:
    """The chips for one question, ready for a surface to render."""
    french = str(locale).startswith("fr")
    if name == "time_slot":
        return {
            "name": "time_slot",
            "question": "C'est pour quand ?" if french else "When is this for?",
            "options": [
                {"value": slot.key, "label": f"{slot.emoji} {slot.label(locale)}".strip()}
                for slot in slots.slots()
            ],
        }
    if name == "category":
        return {
            "name": "category",
            "question": "Vous avez envie de quoi ?" if french else "What are you in the mood for?",
            "options": [
                {"value": chip["key"], "label": f"{chip['emoji']} {chip['label']}"}
                for chip in categories.chips(locale)
            ],
        }
    if name == "area":
        return {
            "name": "area",
            "question": "Un coin en particulier ?" if french else "Any particular area?",
            "options": [{"value": "", "label": "Peu importe" if french else "Anywhere"}]
            + [{"value": area, "label": area} for area in sorted(set(_AREAS.values()))[:6]],
        }
    if name == "budget":
        return {
            "name": "budget",
            "question": "Quel budget ?" if french else "What's the budget?",
            "options": [
                {"value": "free", "label": "Gratuit" if french else "Free"},
                {"value": "20", "label": "Moins de 20 $" if french else "Under $20"},
                {"value": "50", "label": "Moins de 50 $" if french else "Under $50"},
                {"value": "", "label": "Peu importe" if french else "No limit"},
            ],
        }
    return {"name": name, "question": name, "options": []}
