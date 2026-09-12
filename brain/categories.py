"""What the category chips mean, and how each one becomes catalog queries.

## Why this file exists

The obvious design — one chip per Festro tag — does not survive contact with a
real catalog, and this is not specific to Festro. Two things are true of most
event feeds:

* **Tag coverage is uneven.** Plenty of listings carry no tag at all, because
  tags are optional metadata and a lot of inventory arrives from sources that
  never filled them in.
* **The vocabulary is narrower than the catalog.** Here it leans heavily to
  music genre, so the chips a Montrealer actually wants — "théâtre", "danse",
  "humour" — have little or nothing behind them even while the catalog is full
  of exactly those events.

A chip that promises picks and returns none is worse than no chip, so the chips
cannot be a thin wrapper over the tag field.

## What a category is instead

A **definition**: any number of tag filters, keyword queries, and venue slugs.
Running a category means running each strategy against the public catalog and
merging the results, newest-first, de-duplicated on ``short_id``. Keyword
queries reach the whole catalog because Festro's search covers title, venue
name, city, lineup and organizer name — which is why a venue keyword like
"Les Grands Ballets" reaches a run of dance listings that no tag filter would.

A category therefore degrades gracefully: as Festro's tagging improves, the tag
strategy carries more of the weight and the keywords quietly matter less.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Category:
    """One chip.

    ``tags`` are matched verbatim against the event's JSON tag list — Festro
    filters with ``tags__contains=[label]``, so these are **labels** ("Hip Hop"),
    not slugs ("hip-hop"). ``queries`` are free-text searches. ``blurb`` is what
    the agent says when it picks this category for the user.
    """

    key: str
    label_fr: str
    label_en: str
    emoji: str
    tags: tuple[str, ...] = ()
    queries: tuple[str, ...] = ()
    blurb: str = ""

    def label(self, locale: str) -> str:
        return self.label_fr if str(locale).startswith("fr") else self.label_en


# ---------------------------------------------------------------------------
# The default set, derived from what Montréal's catalog actually contains:
# ballet and contemporary dance (Les Grands Ballets, Agora de la danse),
# theatre (TNM, Rialto, Beanfield, St-Denis), club nights (Newspeak, Ausgang,
# Bar Le Ritz), live rooms (MTELUS, Studio TD, Quai des Brumes, Sala Rossa),
# festivals (POP Montréal, Osheaga, LASSO, ÎleSoniq) and city programming
# (Ville de Montréal, the borough libraries).
#
# ⚠️ TUNE ME — this is the one list in the repo that is a product judgement
# rather than a fact about the API. Adding a keyword widens a chip; a chip with
# no inventory tonight is worse than no chip, because the flow promises picks.
# `python manage.py check_categories --when today` prints the live count behind
# every chip, which is the fastest way to see whether an edit helped.
# ---------------------------------------------------------------------------
CATEGORIES: tuple[Category, ...] = (
    Category(
        key="live",
        label_fr="Concerts",
        label_en="Live music",
        emoji="🎤",
        tags=("Rock", "Pop", "Hip Hop", "Indie", "Folk", "Metal", "R&B", "Country"),
        queries=("MTELUS", "Studio TD", "Quai des Brumes", "Sala Rossa", "Bar Le Ritz"),
        blurb="des concerts",
    ),
    Category(
        key="nightlife",
        label_fr="Sortir danser",
        label_en="Nightlife",
        emoji="🪩",
        tags=("Electronic", "House", "Techno", "Afro House", "Disco"),
        queries=("Newspeak", "Ausgang", "club", "DJ", "after"),
        blurb="une soirée dansante",
    ),
    Category(
        key="theatre",
        label_fr="Théâtre",
        label_en="Theatre",
        emoji="🎭",
        queries=("Théâtre", "Theatre", "Rialto", "Beanfield", "St-Denis"),
        blurb="du théâtre",
    ),
    Category(
        key="dance",
        label_fr="Danse",
        label_en="Dance",
        emoji="🩰",
        queries=("Ballets", "danse", "Agora de la danse", "dance"),
        blurb="de la danse",
    ),
    Category(
        key="classical",
        label_fr="Classique & opéra",
        label_en="Classical & opera",
        emoji="🎻",
        tags=("Classical", "Jazz"),
        queries=("orchestre", "opéra", "quatuor", "récital"),
        blurb="du classique",
    ),
    Category(
        key="comedy",
        label_fr="Humour",
        label_en="Comedy",
        emoji="😂",
        queries=("humour", "comedy", "stand-up", "impro", "Comedy Cave"),
        blurb="de l'humour",
    ),
    Category(
        key="festival",
        label_fr="Festivals",
        label_en="Festivals",
        emoji="🎪",
        tags=("Festival",),
        queries=("festival", "POP Montréal", "Osheaga", "LASSO", "ÎleSoniq"),
        blurb="un festival",
    ),
    Category(
        key="free",
        label_fr="Gratuit",
        label_en="Free tonight",
        emoji="🆓",
        # Handled by ?price=free rather than a keyword; see build_queries.
        blurb="quelque chose de gratuit",
    ),
    Category(
        key="surprise",
        label_fr="Surprends-moi",
        label_en="Surprise me",
        emoji="🎲",
        blurb="un peu de tout",
    ),
)

BY_KEY: dict[str, Category] = {c.key: c for c in CATEGORIES}


def get(key: str | None) -> Category | None:
    return BY_KEY.get((key or "").strip().lower())


@dataclass
class CatalogQuery:
    """One call to ``festro.client.search_events``."""

    tags: str | None = None
    q: str | None = None
    price: str | None = None
    extra: dict = field(default_factory=dict)


def build_queries(category_key: str | None, *, limit_strategies: int = 6) -> list[CatalogQuery]:
    """Turn a chip into the catalog calls that answer it.

    ``surprise`` (and an unknown key) means one unfiltered query — the ranked
    feed for the window, which is exactly what "surprends-moi" should return.
    ``free`` is a price filter, not a keyword, because Festro already models it.
    """
    category = get(category_key)
    if category is None or category.key == "surprise":
        return [CatalogQuery()]
    if category.key == "free":
        return [CatalogQuery(price="free")]

    queries = [CatalogQuery(tags=tag) for tag in category.tags]
    queries += [CatalogQuery(q=term) for term in category.queries]
    return queries[:limit_strategies] or [CatalogQuery()]


def chips(locale: str = "fr") -> list[dict]:
    """The chip list a surface renders. Counts are attached by the caller."""
    return [
        {"key": c.key, "label": c.label(locale), "emoji": c.emoji} for c in CATEGORIES
    ]
