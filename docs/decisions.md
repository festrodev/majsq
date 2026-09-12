# Decisions, and what changed them

## Categories are not tags

The first design gave each category chip one tag. Sampling the live feed
killed it, for two reasons that apply to most event catalogs:

- **Tag coverage is uneven.** Tags are optional metadata, and a lot of
  inventory arrives from sources that never filled them in.
- **The vocabulary is narrower than the catalog.** It leans to music genre, so
  "théâtre", "danse" and "humour" have little behind them even though the
  catalog is full of those events.

A chip that promises picks and returns none is worse than no chip.

A category is now a *definition*: tags, plus keyword queries, plus venues.
Keyword queries reach everything because the search covers title, venue, city,
lineup and organizer — which is how "Les Grands Ballets" finds the dance
listings that no tag filter would. As tagging improves, the tag strategy
quietly carries more of the weight without any change here.

## Time slot before category

Mood was the original first question. It was only ever a proxy for "which kind
of event", so the category is asked directly instead. And the window comes
first, because every downstream step is a catalog query and none of them is
valid without one.

## Read before asking

Every question is a tap between "quoi faire ce soir?" and three suggestions,
and in a group it costs the whole room's attention. So constraints already
stated in the conversation are extracted first and never asked again, and at
most one optional question follows. The extraction is a regex pass, not a model
call: it runs on every turn in both transports and must behave identically
whether or not a model key is configured.

## Two services, not three

The Telegram bot is a package inside the agent rather than its own deployment.
One brain, one database, one thing to keep alive.
