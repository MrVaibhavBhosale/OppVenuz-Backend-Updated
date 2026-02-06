from django.contrib import admin
from .models import OppvenuzChoiceMaster, Service_master

@admin.register(OppvenuzChoiceMaster)
class OppvenuzChoiceAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'choice_name',
        'minimum_comments_count',
        'archived_comments_count',
        'average_percentage',
        'status',
        'created_at',
    )
    search_fields = ('choice_name',)
    list_filter = ('status',)

admin.site.register(Service_master)