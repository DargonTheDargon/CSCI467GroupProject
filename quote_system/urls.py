from django.urls import path

from quote_system.views import QuoteListView, QuoteView

from . import views

urlpatterns = [
    path('', views.login_page, name='login'),
    path('quotes/', QuoteListView.as_view(), name='quote_list'),
    path('quotes/view/<int:pk>/', QuoteView.as_view(), name="quote_view"),
    path('sanction-interface/', views.sanction_interface, name='sanction_interface'),
    path('purchase-orders/', views.purchase_orders, name='purchase_orders'),
    path('associates/', views.associates, name='associates'),
    path('add-associate/', views.add_associate, name='add_associate'),
    path('edit-associate/<int:pk>/', views.edit_associate, name='edit_associate'),
    path('delete-associate/<int:pk>/', views.delete_associate, name='delete_associate'),
    path('logout/', views.logout_page, name='logout')
]