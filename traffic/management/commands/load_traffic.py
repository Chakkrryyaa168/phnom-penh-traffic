import os
import time
from django.core.management.base import BaseCommand, CommandError
from traffic.services import import_traffic_csv


class Command(BaseCommand):
    help = 'Load hourly traffic volume data from a CSV file into SQLite database'

    def add_arguments(self, parser):
        parser.add_argument(
            'csv_file',
            type=str,
            help='Path to the traffic hourly data CSV file (e.g. traffic_hourly_data.csv)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing traffic records and intersections before loading'
        )

    def handle(self, *args, **options):
        csv_path = options['csv_file']
        clear = options['clear']

        if not os.path.exists(csv_path):
            raise CommandError(f"CSV file not found at path: {csv_path}")

        self.stdout.write(self.style.NOTICE(f"Loading traffic data from '{csv_path}'..."))
        start_time = time.time()

        try:
            # Check if this is the default demo file
            is_demo = os.path.basename(csv_path).startswith('traffic_hourly_data')

            result = import_traffic_csv(csv_path, is_demo=is_demo, clear_existing=clear)
            elapsed = time.time() - start_time

            self.stdout.write(self.style.SUCCESS(
                f"Successfully loaded {result['records_created']} records across "
                f"{result['intersections_count']} intersections in {elapsed:.2f}s."
            ))
            if result.get('skipped_invalid_rows', 0) > 0:
                self.stdout.write(self.style.WARNING(
                    f"Skipped {result['skipped_invalid_rows']} invalid rows."
                ))
        except Exception as e:
            raise CommandError(f"Error loading traffic data: {str(e)}")

