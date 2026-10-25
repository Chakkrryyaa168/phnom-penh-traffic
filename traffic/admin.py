from django.contrib import admin
from .models import Intersection, TrafficRecord


@admin.register(Intersection)
class IntersectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'latitude', 'longitude', 'is_simulated', 'get_record_count', 'created_at')
    search_fields = ('name',)
    list_filter = ('is_simulated', 'created_at')
    ordering = ('name',)

    @admin.display(description='Total Records')
    def get_record_count(self, obj):
        return obj.records.count()


@admin.register(TrafficRecord)
class TrafficRecordAdmin(admin.ModelAdmin):
    list_display = ('intersection', 'timestamp', 'volume')
    list_filter = ('intersection', 'timestamp')
    search_fields = ('intersection__name',)
    date_hierarchy = 'timestamp'
    ordering = ('-timestamp',)
