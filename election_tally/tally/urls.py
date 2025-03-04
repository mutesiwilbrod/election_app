
from django.urls import path
from .views import login, submit_results_view
from rest_framework_simplejwt.views import TokenRefreshView
from .views import get_candidates, get_polling_stations

urlpatterns = [
    path('login/', login, name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('submit_results/', submit_results_view, name='submit_results'),
    path('get_candidates/', get_candidates, name='get_candidates'),
    path('get_polling_stations/', get_polling_stations, name='get_polling_stations'),
]


