from datetime import datetime
import io
from django.test import TestCase, Client
from django.utils import timezone
from .models import Intersection, TrafficRecord
from .services import (
    peak_summary,
    hourly_profile,
    classify_period,
    import_traffic_csv,
    get_kpi_summary,
)


class PeakSummaryTestCase(TestCase):
    """Unit tests for peak_summary() using a controlled small fixture."""

    def setUp(self):
        # 1. Create three distinct intersections for testing different rush periods
        self.inter_evening = Intersection.objects.create(
            name="Monivong & Mao Tse Toung",
            latitude=11.5375,
            longitude=104.9250
        )
        self.inter_morning = Intersection.objects.create(
            name="Chroy Changvar Bridge",
            latitude=11.5833,
            longitude=104.9297
        )
        self.inter_other = Intersection.objects.create(
            name="Central Market Ring",
            latitude=11.5695,
            longitude=104.9228
        )

        records = []
        # Create 3 days of hourly records (2026-10-01 is Thursday, 02 is Friday, 03 is Saturday)
        for day in [1, 2, 3]:
            for hour in range(24):
                dt = timezone.make_aware(datetime(2026, 10, day, hour, 0, 0))

                # Intersection 1: Evening peak at 17:00 (Evening rush 16-19)
                if hour == 17:
                    vol1 = 2000
                elif hour == 8:
                    vol1 = 1000
                else:
                    vol1 = 200
                records.append(TrafficRecord(intersection=self.inter_evening, timestamp=dt, volume=vol1))

                # Intersection 2: Morning peak at 07:00 (Morning rush 06-09)
                if hour == 7:
                    vol2 = 1800
                elif hour == 18:
                    vol2 = 800
                else:
                    vol2 = 150
                records.append(TrafficRecord(intersection=self.inter_morning, timestamp=dt, volume=vol2))

                # Intersection 3: Midday peak at 12:00 (Other)
                if hour == 12:
                    vol3 = 1500
                else:
                    vol3 = 100
                records.append(TrafficRecord(intersection=self.inter_other, timestamp=dt, volume=vol3))

        TrafficRecord.objects.bulk_create(records)

    def test_peak_summary_calculations(self):
        """Verify peak_hour, peak_volume, avg_hourly_volume, peak_ratio, and period."""
        summaries = peak_summary()
        self.assertEqual(len(summaries), 3)

        by_name = {s['intersection_name']: s for s in summaries}

        # Check Evening Peak intersection
        evening_data = by_name["Monivong & Mao Tse Toung"]
        self.assertEqual(evening_data['peak_hour'], 17)
        self.assertEqual(evening_data['peak_volume'], 2000.0)
        self.assertEqual(evening_data['period'], "Evening rush 16-19")
        self.assertGreater(evening_data['peak_ratio'], 1.0)
        # 23 hours of 200 (except hour 8=1000, hour 17=2000) -> 22*200 + 1000 + 2000 = 7400 / 24 = 308.3
        self.assertAlmostEqual(evening_data['avg_hourly_volume'], 308.3, delta=1.0)

        # Check Morning Peak intersection
        morning_data = by_name["Chroy Changvar Bridge"]
        self.assertEqual(morning_data['peak_hour'], 7)
        self.assertEqual(morning_data['peak_volume'], 1800.0)
        self.assertEqual(morning_data['period'], "Morning rush 06-09")
        self.assertGreater(morning_data['peak_ratio'], 1.0)

        # Check Other Peak intersection
        other_data = by_name["Central Market Ring"]
        self.assertEqual(other_data['peak_hour'], 12)
        self.assertEqual(other_data['peak_volume'], 1500.0)
        self.assertEqual(other_data['period'], "Other")

    def test_classify_period_helper(self):
        """Verify the period classification logic directly."""
        self.assertEqual(classify_period(6), "Morning rush 06-09")
        self.assertEqual(classify_period(7), "Morning rush 06-09")
        self.assertEqual(classify_period(8), "Morning rush 06-09")
        self.assertEqual(classify_period(9), "Morning rush 06-09")

        self.assertEqual(classify_period(16), "Evening rush 16-19")
        self.assertEqual(classify_period(17), "Evening rush 16-19")
        self.assertEqual(classify_period(18), "Evening rush 16-19")
        self.assertEqual(classify_period(19), "Evening rush 16-19")

        self.assertEqual(classify_period(0), "Other")
        self.assertEqual(classify_period(12), "Other")
        self.assertEqual(classify_period(23), "Other")

    def test_hourly_profile_filters(self):
        """Verify hourly profile for all, weekday, and weekend day types."""
        # 2026-10-01 (Thu) and 2026-10-02 (Fri) are weekdays, 2026-10-03 (Sat) is weekend
        prof_all = hourly_profile(self.inter_evening, day_type="all")
        self.assertEqual(len(prof_all['hours']), 24)
        self.assertEqual(prof_all['volumes'][17], 2000.0)

        prof_weekday = hourly_profile(self.inter_evening, day_type="weekday")
        self.assertEqual(len(prof_weekday['hours']), 24)
        self.assertEqual(prof_weekday['volumes'][17], 2000.0)

        prof_weekend = hourly_profile(self.inter_evening, day_type="weekend")
        self.assertEqual(len(prof_weekend['hours']), 24)
        self.assertEqual(prof_weekend['volumes'][17], 2000.0)

        # Invalid day type should raise ValueError
        with self.assertRaises(ValueError):
            hourly_profile(self.inter_evening, day_type="invalid_type")

    def test_kpi_summary(self):
        """Verify dashboard KPI summary computation."""
        kpis = get_kpi_summary()
        self.assertTrue(kpis['has_data'])
        self.assertEqual(kpis['total_intersections'], 3)
        self.assertEqual(kpis['busiest_intersection']['intersection_name'], "Monivong & Mao Tse Toung")


class CSVImportTestCase(TestCase):
    """Unit tests for CSV import validation and bulk creation."""

    def test_import_missing_columns(self):
        """CSV with missing required columns must raise ValueError."""
        csv_data = "intersection,wrong_column\nMonivong,123\n"
        with self.assertRaises(ValueError) as ctx:
            import_traffic_csv(io.StringIO(csv_data))
        self.assertIn("Missing required columns", str(ctx.exception))

    def test_import_valid_csv(self):
        """Valid CSV should create intersections and traffic records."""
        csv_data = (
            "intersection,timestamp,volume\n"
            "Preah Sihanouk Blvd,2026-10-01 08:00:00,1200\n"
            "Preah Sihanouk Blvd,2026-10-01 09:00:00,1100\n"
            "Preah Norodom Blvd,2026-10-01 08:00:00,1350\n"
        )
        result = import_traffic_csv(io.StringIO(csv_data))
        self.assertEqual(result['records_created'], 3)
        self.assertEqual(result['intersections_count'], 2)
        self.assertTrue(Intersection.objects.filter(name="Preah Sihanouk Blvd").exists())
        self.assertEqual(TrafficRecord.objects.count(), 3)


class ViewsAndEndpointsTestCase(TestCase):
    """Tests for HTTP views and JSON API endpoints."""

    def setUp(self):
        self.client = Client()
        self.inter = Intersection.objects.create(name="Olympic Stadium Junction")
        dt = timezone.make_aware(datetime(2026, 10, 1, 8, 0, 0))
        TrafficRecord.objects.create(intersection=self.inter, timestamp=dt, volume=950)

    def test_views_return_200(self):
        """Test all user-facing views respond with 200 OK."""
        res_dash = self.client.get('/')
        self.assertEqual(res_dash.status_code, 200)

        res_detail = self.client.get(f'/intersection/{self.inter.id}/')
        self.assertEqual(res_detail.status_code, 200)

        res_compare = self.client.get('/compare/')
        self.assertEqual(res_compare.status_code, 200)

        res_upload = self.client.get('/upload/')
        self.assertEqual(res_upload.status_code, 200)

        res_about = self.client.get('/about/')
        self.assertEqual(res_about.status_code, 200)

    def test_api_peaks_endpoint(self):
        """Test /api/peaks/ JSON endpoint."""
        res = self.client.get('/api/peaks/')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['status'], 'success')
        self.assertGreaterEqual(len(data['data']), 1)

    def test_api_profile_endpoint(self):
        """Test /api/profile/<id>/ JSON endpoint."""
        res = self.client.get(f'/api/profile/{self.inter.id}/')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(len(data['volumes']), 24)
