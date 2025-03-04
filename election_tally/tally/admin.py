
# Register your models here.
from django.contrib import admin
from .models import User, ElectionPosition, Candidate, PollingStation, Result

admin.site.register(User)
admin.site.register(ElectionPosition)
admin.site.register(Candidate)
admin.site.register(PollingStation)
admin.site.register(Result)
