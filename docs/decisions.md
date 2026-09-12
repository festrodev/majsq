# Decisions, and what changed them

## Categories are not tags

The first design gave each category chip one Festro tag. Measuring the live
catalog on 2026-09-12 killed it:

- 3,421 upcoming Montréal events
- **8 of the top 60 carried any tag at all**
- the taxonomy is almost entirely music genre — classical 143, rock 109,
  electronic 87, pop 51, hip-hop 26 — with no comedy, theatre, dance or family
  tag carrying real usage

Tag-only chips would have hidden ~87% of the catalog, and the chips a
Montrealer actually wants would have come back empty while the catalog was full
of exactly those events.

A category is now a *definition*: tags, plus keyword queries, plus venues.
Keyword queries reach everything because Festro's search covers title, venue,
city, lineup and organizer — which is how "Les Grands Ballets" finds 31
untagged dance events. As tagging improves, the tag strategy quietly carries
more of the weight.

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
