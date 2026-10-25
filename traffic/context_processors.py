from .models import Intersection, TrafficRecord


def demo_badge_context(request):
    """
    Context processor to supply simulation status and quick dataset stats
    globally to all templates for the 'Simulated data' badge and navbar indicators.
    """
    try:
        has_data = TrafficRecord.objects.exists()
        is_simulated = Intersection.objects.filter(is_simulated=True).exists()
        # If there are records and either is_simulated flag is set or default demo exists
        is_demo_loaded = has_data and (is_simulated or Intersection.objects.filter(name__icontains='Monivong').exists())
    except Exception:
        has_data = False
        is_demo_loaded = False

    return {
        'is_simulated_dataset': is_demo_loaded,
        'has_traffic_data': has_data,
    }

