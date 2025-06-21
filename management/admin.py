from django.contrib import admin

from management.models import CompanyProfile, ExternalTopic, SessionTopic


@admin.register(SessionTopic)
class SessionTopicAdmin(admin.ModelAdmin):
    """
    Admin configuration for SessionTopic model to customize the display
    and functionality in the Django admin interface.
    """

    list_display = ("topic", "get_conducted_by_name", "date", "status")
    list_filter = ("status", "conducted_by", "date")
    search_fields = ("topic", "conducted_by__first_name", "conducted_by__last_name")
    ordering = ("-date",)

    def get_conducted_by_name(self, obj):
        """
        Returns the full name of the person who conducted the session.

        Args:
            obj: The SessionTopic instance.

        Returns:
            str: The full name of the person who conducted the session.
        """
        return f"{obj.conducted_by.first_name} {obj.conducted_by.last_name}"

    get_conducted_by_name.short_description = "Conducted By"
    get_conducted_by_name.admin_order_field = "conducted_by"


@admin.register(ExternalTopic)
class ExternalTopicAdmin(admin.ModelAdmin):
    """
    Admin configuration for ExternalTopic model to customize the display
    and functionality in the Django admin interface.
    """

    list_display = ("coming_soon", "created_at")
    list_filter = ("created_at",)
    search_fields = ("coming_soon",)
    ordering = ("-created_at",)

admin.site.register(CompanyProfile)