from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Customer, LineItem, Quote, SalesAssociate, User

admin.site.register(User, UserAdmin)
admin.site.register(Quote)
admin.site.register(Customer)
admin.site.register(SalesAssociate)
admin.site.register(LineItem)