"""
Analysis services for Phnom Penh Traffic Insights.
Kept strictly separate from views.
"""

from typing import Union, List, Dict, Any, Optional
import pandas as pd
import numpy as np
from django.db import transaction
from django.utils import timezone
from .models import Intersection, TrafficRecord


# Coordinates for prominent Phnom Penh intersections
PHNOM_PENH_COORDINATES = {
    'Russian Federation Blvd & Preah Monivong Blvd': (11.5724, 104.9189),
    'Chroy Changvar Bridge & Sisowath Quay': (11.5833, 104.9297),
    'Russian Federation Blvd & St. 271': (11.5432, 104.8872),
    'Russian Federation Blvd & St. 271 (5 Makara)': (11.5432, 104.8872),
    'Hun Sen Blvd & National Road 2': (11.5123, 104.9298),
    'Monivong Blvd & Mao Tse Toung Blvd': (11.5375, 104.9250),
    'Preah Norodom Blvd & Preah Sihanouk Blvd': (11.5564, 104.9282),
    'Preah Monivong Blvd & Kampuchea Krom Blvd': (11.5698, 104.9205),
    'Preah Sihanouk Blvd & Preah Monivong Blvd': (11.5552, 104.9213),
    'Central Market (Phsar Thmey) Ring Road': (11.5695, 104.9228),
    'Charles de Gaulle & Preah Monireth Blvd': (11.5578, 104.9126),
    'Camko City Roundabout': (11.5950, 104.8910),
}


def classify_period(hour: int) -> str:
    """
    Classify hour into traffic rush periods:
    - Morning rush 06-09 (hours 6, 7, 8, 9)
    - Evening rush 16-19 (hours 16, 17, 18, 19)
    - Other (all other hours)
    """
    if 6 <= hour <= 9:
        return "Morning rush 06-09"
    elif 16 <= hour <= 19:
        return "Evening rush 16-19"
    else:
        return "Other"


def get_period_color(period: str) -> str:
    """Return theme color corresponding to rush period."""
    if "Morning" in period:
        return "#2a9d8f"  # Teal
    elif "Evening" in period:
        return "#e76f51"  # Coral
    else:
        return "#e9c46a"  # Sand / Gold


def format_hour_range(hour: int, style: str = "12h") -> str:
    """
    Format hour integer into readable range.
    style="12h": 17 -> '5 - 6 PM', 7 -> '7 - 8 AM', 11 -> '11 AM - 12 PM'
    style="24h": 17 -> '17:00 - 18:00'
    """
    h1 = hour % 24
    h2 = (hour + 1) % 24

    if style == "24h":
        return f"{h1:02d}:00 - {h2:02d}:00"

    ampm1 = "AM" if h1 < 12 else "PM"
    ampm2 = "AM" if h2 < 12 else "PM"

    disp1 = 12 if h1 % 12 == 0 else h1 % 12
    disp2 = 12 if h2 % 12 == 0 else h2 % 12

    if ampm1 == ampm2:
        return f"{disp1} - {disp2} {ampm2}"
    else:
        return f"{disp1} {ampm1} - {disp2} {ampm2}"


def _resolve_intersection(intersection: Union[Intersection, int, str]) -> Intersection:
    """Helper to resolve an intersection object from ID or name or instance."""
    if isinstance(intersection, Intersection):
        return intersection
    elif isinstance(intersection, int) or (isinstance(intersection, str) and str(intersection).isdigit()):
        return Intersection.objects.get(pk=int(intersection))
    elif isinstance(intersection, str):
        return Intersection.objects.get(name=intersection)
    else:
        raise ValueError(f"Cannot resolve intersection reference: {intersection}")


def _prepare_records_dataframe(records: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Convert queryset records into a DataFrame and adjust timestamps
    to the active project timezone (Asia/Phnom_Penh).
    """
    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records)
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Convert UTC timestamps stored by Django to current timezone (Asia/Phnom_Penh)
    cur_tz = timezone.get_current_timezone_name()
    if df['timestamp'].dt.tz is not None:
        df['timestamp'] = df['timestamp'].dt.tz_convert(cur_tz)
    else:
        # If naive, localize then convert
        df['timestamp'] = df['timestamp'].dt.tz_localize('UTC').dt.tz_convert(cur_tz)

    df['hour'] = df['timestamp'].dt.hour
    df['dayofweek'] = df['timestamp'].dt.dayofweek  # 0=Monday, 6=Sunday
    return df


def hourly_profile(
    intersection: Union[Intersection, int, str],
    day_type: str = "all"
) -> Dict[str, Any]:
    """
    Calculate average volume for each hour 0-23 for a given intersection.
    
    Args:
        intersection: Intersection model instance, integer ID, or name
        day_type: "all" / "weekday" / "weekend"
        
    Returns:
        Dictionary containing:
            - intersection_id: int
            - intersection_name: str
            - day_type: str
            - hours: list of ints [0..23]
            - labels: list of formatted hour labels ['00:00'..'23:00']
            - volumes: list of floats for each hour [v0..v23]
            - profile: list of dicts [{'hour': h, 'volume': v, 'label': l}]
            - Can also be accessed by integer hour key: result[0], result[1], etc.
    """
    intersection_obj = _resolve_intersection(intersection)
    day_type_clean = day_type.strip().lower() if day_type else "all"

    # Query records
    qs = TrafficRecord.objects.filter(intersection=intersection_obj).values('timestamp', 'volume')
    records = list(qs)

    hours = list(range(24))
    hour_labels = [f"{h:02d}:00" for h in hours]

    if not records:
        volumes = [0.0] * 24
    else:
        df = _prepare_records_dataframe(records)

        if day_type_clean == 'weekday':
            df = df[df['dayofweek'] < 5]
        elif day_type_clean == 'weekend':
            df = df[df['dayofweek'] >= 5]
        elif day_type_clean != 'all':
            raise ValueError(f"Invalid day_type: '{day_type}'. Allowed values: 'all', 'weekday', 'weekend'.")

        if df.empty:
            volumes = [0.0] * 24
        else:
            series = df.groupby('hour')['volume'].mean().reindex(range(24), fill_value=0.0)
            volumes = [round(float(series.loc[h]), 1) for h in hours]

    result = {
        'intersection_id': intersection_obj.id,
        'intersection_name': intersection_obj.name,
        'day_type': day_type_clean,
        'hours': hours,
        'labels': hour_labels,
        'volumes': volumes,
        'profile': [
            {'hour': h, 'volume': volumes[h], 'label': hour_labels[h]}
            for h in hours
        ]
    }

    # Also support direct integer indexing by hour result[h]
    for h in hours:
        result[h] = volumes[h]

    return result


def peak_summary(as_dataframe: bool = False) -> Union[List[Dict[str, Any]], pd.DataFrame]:
    """
    For every intersection return:
        - peak_hour (hour with highest average volume across all days)
        - peak_volume (average volume at peak hour)
        - avg_hourly_volume (average volume across all hours)
        - peak_ratio (peak / average)
        - period ("Morning rush 06-09", "Evening rush 16-19", "Other")
        
    Returns:
        List of dictionaries (or pandas DataFrame if as_dataframe=True)
    """
    intersections = list(Intersection.objects.all().order_by('name'))
    if not intersections:
        return pd.DataFrame() if as_dataframe else []

    # Efficiently load all records in one query
    qs = TrafficRecord.objects.all().values('intersection_id', 'timestamp', 'volume')
    records = list(qs)

    if not records:
        # Intersections exist but no records loaded yet
        summaries = []
        for inter in intersections:
            summaries.append({
                'intersection_id': inter.id,
                'intersection_name': inter.name,
                'latitude': inter.latitude,
                'longitude': inter.longitude,
                'peak_hour': 0,
                'peak_hour_range': format_hour_range(0),
                'peak_hour_range_24h': format_hour_range(0, style="24h"),
                'peak_volume': 0.0,
                'avg_hourly_volume': 0.0,
                'peak_ratio': 0.0,
                'period': 'Other',
                'period_color': get_period_color('Other'),
                'record_count': 0,
            })
        return pd.DataFrame(summaries) if as_dataframe else summaries

    df = _prepare_records_dataframe(records)

    summaries = []
    # Compute per-intersection profile
    for inter in intersections:
        inter_df = df[df['intersection_id'] == inter.id]
        if inter_df.empty:
            peak_h = 0
            peak_v = 0.0
            avg_v = 0.0
            ratio = 0.0
            period = "Other"
            count = 0
        else:
            # Average volume for each hour across all days
            hourly_means = inter_df.groupby('hour')['volume'].mean().reindex(range(24), fill_value=0.0)
            peak_h = int(hourly_means.idxmax())
            peak_v = round(float(hourly_means.loc[peak_h]), 1)
            # Overall average hourly volume across 24 hours
            avg_v = round(float(hourly_means.mean()), 1)
            ratio = round(peak_v / avg_v, 2) if avg_v > 0 else 0.0
            period = classify_period(peak_h)
            count = len(inter_df)

        summaries.append({
            'intersection_id': inter.id,
            'intersection_name': inter.name,
            'latitude': inter.latitude,
            'longitude': inter.longitude,
            'peak_hour': peak_h,
            'peak_hour_range': format_hour_range(peak_h),
            'peak_hour_range_24h': format_hour_range(peak_h, style="24h"),
            'peak_volume': peak_v,
            'avg_hourly_volume': avg_v,
            'peak_ratio': ratio,
            'period': period,
            'period_color': get_period_color(period),
            'record_count': count,
        })

    # Sort by peak_volume descending
    summaries.sort(key=lambda x: x['peak_volume'], reverse=True)

    if as_dataframe:
        return pd.DataFrame(summaries)
    return summaries


def get_kpi_summary() -> Dict[str, Any]:
    """
    Computes dashboard KPIs:
    - Busiest intersection
    - Overall peak hour
    - Weekday vs weekend average
    - Total intersections & records
    """
    summaries = peak_summary()
    total_intersections = Intersection.objects.count()
    total_records = TrafficRecord.objects.count()

    if not summaries or total_records == 0:
        return {
            'busiest_intersection': None,
            'overall_peak_hour': None,
            'overall_peak_hour_range': "N/A",
            'overall_peak_hour_range_24h': "N/A",
            'overall_peak_hour_avg': 0.0,
            'weekday_avg': 0.0,
            'weekend_avg': 0.0,
            'weekday_vs_weekend_diff': 0.0,
            'total_intersections': total_intersections,
            'total_records': total_records,
            'has_data': False,
        }

    # Busiest intersection by average hourly volume or peak volume
    busiest = max(summaries, key=lambda x: x['avg_hourly_volume'])

    # Overall peak hour across all intersections and all days
    qs = TrafficRecord.objects.all().values('timestamp', 'volume')
    df = _prepare_records_dataframe(list(qs))

    hourly_overall = df.groupby('hour')['volume'].mean()
    overall_peak_hour = int(hourly_overall.idxmax())
    overall_peak_avg = round(float(hourly_overall.max()), 1)

    # Weekday vs Weekend average
    weekday_df = df[df['dayofweek'] < 5]
    weekend_df = df[df['dayofweek'] >= 5]

    weekday_avg = round(float(weekday_df['volume'].mean()), 1) if not weekday_df.empty else 0.0
    weekend_avg = round(float(weekend_df['volume'].mean()), 1) if not weekend_df.empty else 0.0

    if weekend_avg > 0:
        pct_diff = round(((weekday_avg - weekend_avg) / weekend_avg) * 100, 1)
    else:
        pct_diff = 0.0

    return {
        'busiest_intersection': busiest,
        'overall_peak_hour': overall_peak_hour,
        'overall_peak_hour_range': format_hour_range(overall_peak_hour),
        'overall_peak_hour_range_24h': format_hour_range(overall_peak_hour, style="24h"),
        'overall_peak_hour_avg': overall_peak_avg,
        'weekday_avg': weekday_avg,
        'weekend_avg': weekend_avg,
        'weekday_vs_weekend_diff': pct_diff,
        'total_intersections': total_intersections,
        'total_records': total_records,
        'has_data': True,
    }


def compare_profiles(
    intersection_ids: List[int],
    day_type: str = "all"
) -> Dict[str, Any]:
    """
    Overlay hourly profiles for 2 to 4 intersections for comparative charts.
    """
    colors = ['#2a9d8f', '#e76f51', '#264653', '#e9c46a', '#457b9d', '#9b5de5']
    datasets = []
    labels = [f"{h:02d}:00" for h in range(24)]
    intersections_data = []

    for i, i_id in enumerate(intersection_ids[:4]):
        try:
            profile = hourly_profile(i_id, day_type=day_type)
            color = colors[i % len(colors)]
            datasets.append({
                'label': profile['intersection_name'],
                'data': profile['volumes'],
                'borderColor': color,
                'backgroundColor': color + '22',
                'borderWidth': 3,
                'tension': 0.35,
                'fill': False,
                'pointRadius': 4,
                'pointHoverRadius': 6,
            })
            intersections_data.append({
                'id': profile['intersection_id'],
                'name': profile['intersection_name'],
                'color': color,
            })
        except Exception:
            continue

    return {
        'labels': labels,
        'datasets': datasets,
        'intersections': intersections_data,
        'day_type': day_type,
    }


def import_traffic_csv(
    file_or_path: Any,
    is_demo: bool = False,
    clear_existing: bool = False
) -> Dict[str, Any]:
    """
    Import traffic records from a CSV file (file path or file-like object).
    Validates required columns: intersection, timestamp, volume.
    Uses bulk_create for high performance.
    """
    # 1. Read CSV with pandas
    try:
        df = pd.read_csv(file_or_path)
    except Exception as e:
        raise ValueError(f"Unable to read CSV file: {str(e)}")

    # 2. Validate columns
    required_cols = {'intersection', 'timestamp', 'volume'}
    missing = required_cols - set(df.columns.str.lower().str.strip())
    if missing:
        raise ValueError(f"Missing required columns in CSV: {', '.join(sorted(missing))}. "
                         f"Found columns: {', '.join(df.columns)}")

    # Normalize column names to lowercase
    col_map = {col: col.lower().strip() for col in df.columns}
    df.rename(columns=col_map, inplace=True)

    # 3. Clean and validate rows
    df.dropna(subset=['intersection', 'timestamp', 'volume'], inplace=True)
    df['intersection'] = df['intersection'].astype(str).str.strip()
    df = df[df['intersection'] != '']

    # Convert timestamps
    df['parsed_timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    invalid_dates = df['parsed_timestamp'].isna().sum()
    if invalid_dates > 0:
        df = df.dropna(subset=['parsed_timestamp'])

    # Convert volumes
    df['parsed_volume'] = pd.to_numeric(df['volume'], errors='coerce')
    df = df.dropna(subset=['parsed_volume'])
    df['parsed_volume'] = df['parsed_volume'].astype(int)
    df = df[df['parsed_volume'] >= 0]

    if df.empty:
        raise ValueError("CSV contains no valid traffic data rows after parsing.")

    with transaction.atomic():
        if clear_existing:
            TrafficRecord.objects.all().delete()
            Intersection.objects.all().delete()

        # Cache existing intersections
        intersection_cache = {obj.name: obj for obj in Intersection.objects.all()}
        unique_names = df['intersection'].unique()
        new_intersections = []

        for name in unique_names:
            if name not in intersection_cache:
                coords = PHNOM_PENH_COORDINATES.get(name, (None, None))
                inter_obj = Intersection(
                    name=name,
                    latitude=coords[0],
                    longitude=coords[1],
                    is_simulated=is_demo
                )
                new_intersections.append(inter_obj)

        if new_intersections:
            Intersection.objects.bulk_create(new_intersections)
            for obj in Intersection.objects.filter(name__in=[i.name for i in new_intersections]):
                intersection_cache[obj.name] = obj

        # Build traffic records
        records_to_create = []
        cur_tz = timezone.get_current_timezone()
        for _, row in df.iterrows():
            inter_obj = intersection_cache[row['intersection']]
            # Make timestamp timezone aware in project timezone
            ts = row['parsed_timestamp']
            if timezone.is_naive(ts):
                ts = timezone.make_aware(ts, cur_tz)

            records_to_create.append(
                TrafficRecord(
                    intersection=inter_obj,
                    timestamp=ts,
                    volume=int(row['parsed_volume'])
                )
            )

        TrafficRecord.objects.bulk_create(records_to_create, batch_size=5000)

    return {
        'records_created': len(records_to_create),
        'intersections_count': len(unique_names),
        'skipped_invalid_rows': invalid_dates,
    }

