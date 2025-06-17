from django.contrib import admin

from .models import Plan, UserSubscription
admin.site.register(Plan)
admin.site.register(UserSubscription)
