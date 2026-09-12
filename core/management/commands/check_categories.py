"""Report the catalog inventory behind each category chip."""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from brain import categories, search, slots


class Command(BaseCommand):
    help = "Print the event count behind each category chip for a time window."

    def add_arguments(self, parser):
        parser.add_argument(
            "--when",
            dest="time_slot",
            default="tonight",
            help="Time window: tonight, today, tomorrow, weekend, week, or YYYY-MM-DD.",
        )
        parser.add_argument(
            "--band",
            choices=tuple(slots.BANDS),
            default=None,
            help="Optional part of day: afternoon, evening, or late.",
        )

    def handle(self, *args, **options):
        time_slot = str(options["time_slot"]).strip().lower()
        if time_slot != "today" and slots.get(time_slot) is None:
            raise CommandError(
                "Unsupported --when value. Use tonight, today, tomorrow, "
                "weekend, week, or YYYY-MM-DD."
            )

        band = options["band"]
        counts = search.category_counts(time_slot=time_slot, band=band)
        heading = f"Category inventory for {time_slot}"
        if band:
            heading += f" ({band})"
        self.stdout.write(heading)

        for category in categories.CATEGORIES:
            label = f"{category.key} ({category.label_fr})"
            if category.key == "surprise":
                self.stdout.write(f"{label}: n/a (unfiltered)")
                continue
            self.stdout.write(f"{label}: {counts.get(category.key, 0)}")
