import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.views.decorators.http import require_GET, require_http_methods
from .models import Intersection, TrafficRecord
from .forms import TrafficUploadForm
from .services import (
    hourly_profile,
    peak_summary,
    get_kpi_summary,
    compare_profiles,
    import_traffic_csv,
    format_hour_range,
    classify_period,
    get_period_color,
)


def dashboard_view(request):
    """
    Dashboard view showing:
    - KPI cards (busiest intersection, overall peak hour, weekday vs weekend average)
    - Peak-hour volume bar chart per intersection labelled with peak range & colored by rush period
    - Intersections overview table
    """
    kpis = get_kpi_summary()
    summaries = peak_summary()

    # Pre-serialize chart data for smooth initial render
    chart_labels = [s['intersection_name'] for s in summaries]
    chart_volumes = [s['peak_volume'] for s in summaries]
    chart_colors = [s['period_color'] for s in summaries]
    chart_ranges = [s['peak_hour_range'] for s in summaries]
    chart_periods = [s['period'] for s in summaries]
    chart_ids = [s['intersection_id'] for s in summaries]

    chart_payload = {
        'labels': chart_labels,
        'volumes': chart_volumes,
        'colors': chart_colors,
        'ranges': chart_ranges,
        'periods': chart_periods,
        'ids': chart_ids,
    }

    context = {
        'kpis': kpis,
        'summaries': summaries,
        'chart_payload_json': json.dumps(chart_payload),
    }
    return render(request, 'traffic/dashboard.html', context)


def intersection_detail_view(request, pk):
    """
    Intersection detail view showing:
    - Line chart of average volume by hour (with Weekday / Weekend / All toggle)
    - Metrics table: peak hour, peak volume, average hourly volume, peak ratio
    - Quick selector to switch between intersections
    """
    intersection = get_object_or_404(Intersection, pk=pk)

    # Compute hourly profiles for all day types
    all_prof = hourly_profile(intersection, day_type='all')
    weekday_prof = hourly_profile(intersection, day_type='weekday')
    weekend_prof = hourly_profile(intersection, day_type='weekend')

    # Find this intersection's peak stats
    all_summaries = peak_summary()
    inter_summary = next((s for s in all_summaries if s['intersection_id'] == intersection.id), None)

    if not inter_summary:
        inter_summary = {
            'intersection_id': intersection.id,
            'intersection_name': intersection.name,
            'peak_hour': 0,
            'peak_hour_range': "N/A",
            'peak_volume': 0.0,
            'avg_hourly_volume': 0.0,
            'peak_ratio': 0.0,
            'period': 'Other',
            'period_color': get_period_color('Other'),
            'record_count': intersection.records.count(),
        }

    # All intersections for quick switch
    all_intersections = Intersection.objects.all().order_by('name')

    # Prepare chart data JSON
    chart_data = {
        'labels': all_prof['labels'],
        'all': all_prof['volumes'],
        'weekday': weekday_prof['volumes'],
        'weekend': weekend_prof['volumes'],
        'intersection_name': intersection.name,
    }

    context = {
        'intersection': intersection,
        'summary': inter_summary,
        'chart_data_json': json.dumps(chart_data),
        'all_intersections': all_intersections,
        'all_profile': all_prof,
        'weekday_profile': weekday_prof,
        'weekend_profile': weekend_prof,
    }
    return render(request, 'traffic/detail.html', context)


def compare_view(request):
    """
    Compare view allowing selection of 2-4 intersections and overlaying
    their hourly profiles on one multi-line chart.
    """
    all_intersections = list(Intersection.objects.all().order_by('name'))
    
    # Selected intersection IDs from query string (?intersection=1&intersection=2)
    selected_raw = request.GET.getlist('intersection')
    if not selected_raw:
        # Default to top 3 intersections by peak volume if available
        summaries = peak_summary()
        selected_ids = [s['intersection_id'] for s in summaries[:3]] if summaries else [i.id for i in all_intersections[:3]]
    else:
        selected_ids = []
        for x in selected_raw:
            try:
                selected_ids.append(int(x))
            except ValueError:
                pass
        # Restrict to maximum 4
        selected_ids = selected_ids[:4]

    day_type = request.GET.get('day_type', 'all').lower()
    if day_type not in ['all', 'weekday', 'weekend']:
        day_type = 'all'

    comparison_chart_data = compare_profiles(selected_ids, day_type=day_type)

    # Detailed stats table for the selected intersections
    all_summaries = peak_summary()
    selected_summaries = [s for s in all_summaries if s['intersection_id'] in selected_ids]

    context = {
        'all_intersections': all_intersections,
        'selected_ids': selected_ids,
        'day_type': day_type,
        'chart_data_json': json.dumps(comparison_chart_data),
        'selected_summaries': selected_summaries,
    }
    return render(request, 'traffic/compare.html', context)


@require_http_methods(["GET", "POST"])
def upload_view(request):
    """
    CSV upload view:
    - Validates file format and required columns (intersection, timestamp, volume)
    - Imports records with bulk_create
    - Shows success or error flash message
    - Redirects to dashboard on success
    """
    if request.method == 'POST':
        form = TrafficUploadForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['csv_file']
            clear_existing = form.cleaned_data.get('clear_existing', False)
            try:
                result = import_traffic_csv(
                    csv_file,
                    is_demo=False,
                    clear_existing=clear_existing
                )
                msg = (
                    f"Successfully imported {result['records_created']:,} records across "
                    f"{result['intersections_count']} intersections!"
                )
                if result.get('skipped_invalid_rows', 0) > 0:
                    msg += f" (Skipped {result['skipped_invalid_rows']} invalid rows)"
                messages.success(request, msg)
                return redirect('traffic:dashboard')
            except ValueError as ve:
                messages.error(request, f"Validation Error: {str(ve)}")
            except Exception as e:
                messages.error(request, f"Failed to import CSV: {str(e)}")
    else:
        form = TrafficUploadForm()

    return render(request, 'traffic/upload.html', {'form': form})


def about_view(request):
    """
    Methodology view explaining how peak hour is calculated,
    rush hour definitions, and technical implementation details.
    """
    return render(request, 'traffic/about.html')


# ==============================================================================
# JSON API ENDPOINTS FOR CHART.JS & CLIENT-SIDE FETCHING
# ==============================================================================

@require_GET
def api_peaks(request):
    """
    JSON endpoint: /api/peaks/
    Returns peak summary for all intersections.
    """
    summaries = peak_summary()
    return JsonResponse({
        'status': 'success',
        'count': len(summaries),
        'data': summaries
    })


@require_GET
def api_hourly_profile(request, pk):
    """
    JSON endpoint: /api/profile/<int:pk>/
    Query parameter: day_type (all / weekday / weekend)
    Returns hourly volume profile for Chart.js.
    """
    intersection = get_object_or_404(Intersection, pk=pk)
    day_type = request.GET.get('day_type', 'all').lower()
    if day_type not in ['all', 'weekday', 'weekend']:
        day_type = 'all'

    profile = hourly_profile(intersection, day_type=day_type)
    all_prof = hourly_profile(intersection, day_type='all')
    weekday_prof = hourly_profile(intersection, day_type='weekday')
    weekend_prof = hourly_profile(intersection, day_type='weekend')

    return JsonResponse({
        'status': 'success',
        'intersection_id': intersection.id,
        'intersection_name': intersection.name,
        'day_type': day_type,
        'hours': profile['hours'],
        'labels': profile['labels'],
        'volumes': profile['volumes'],
        'all_volumes': all_prof['volumes'],
        'weekday_volumes': weekday_prof['volumes'],
        'weekend_volumes': weekend_prof['volumes'],
    })


@require_GET
def api_compare(request):
    """
    JSON endpoint: /api/compare/
    Query parameters:
    - ids: comma-separated list of intersection IDs (e.g. ?ids=1,2,3)
    - day_type: all / weekday / weekend
    """
    ids_param = request.GET.get('ids', '')
    ids = []
    for x in ids_param.split(','):
        if x.strip().isdigit():
            ids.append(int(x.strip()))

    day_type = request.GET.get('day_type', 'all').lower()
    if day_type not in ['all', 'weekday', 'weekend']:
        day_type = 'all'

    data = compare_profiles(ids, day_type=day_type)
    return JsonResponse({
        'status': 'success',
        **data
    })


@require_GET
def download_sample_csv(request):
    """
    Helper endpoint allowing users to download a ready-to-test CSV template.
    """
    csv_content = (
        "intersection,timestamp,volume\n"
        "Monivong Blvd & Mao Tse Toung Blvd,2026-10-01 07:00:00,1250\n"
        "Monivong Blvd & Mao Tse Toung Blvd,2026-10-01 08:00:00,1450\n"
        "Monivong Blvd & Mao Tse Toung Blvd,2026-10-01 17:00:00,1850\n"
        "Russian Federation Blvd & Preah Monivong Blvd,2026-10-01 07:00:00,1650\n"
        "Russian Federation Blvd & Preah Monivong Blvd,2026-10-01 08:00:00,1400\n"
        "Russian Federation Blvd & Preah Monivong Blvd,2026-10-01 17:00:00,1100\n"
    )
    response = HttpResponse(csv_content, content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="traffic_sample_template.csv"'
    return response
