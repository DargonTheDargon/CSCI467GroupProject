from django.urls import path

from quote_system.views import QuoteListView

from . import views

urlpatterns = [
    path('', views.login_page, name='login'),
    path('quotes/', QuoteListView.as_view(), name='quote_list'),
    path('sanction-interface/', views.sanction_interface, name='sanction_interface'),
    path('purchase-orders/', views.purchase_orders, name='purchase_orders'),
    path('associates/', views.associates, name='associates'),
    path('logout/', views.logout_page, name='logout')
]