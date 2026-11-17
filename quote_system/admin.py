from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Customer, LineItem, Note, Quote, SalesAssociate, User


class UserAdmin(BaseUserAdmin):

    def get_list_display(self, request):
        #default_list = super().get_list_display(request)
        #default_list += ('role',)
        #return default_list
        return (
            *super().get_list_display(request),
            "role",
        )
    def get_fieldsets(self, request, obj):
        return (
            *super().get_fieldsets(request, obj),
            ("Role", {"fields":["role"]})
        )

admin.site.register(User, UserAdmin)
admin.site.register(Quote)
admin.site.register(Customer)
admin.site.register(SalesAssociate)
admin.site.register(LineItem)
admin.site.register(Note)