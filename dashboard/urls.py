from django.urls import path
from . import views

urlpatterns = [
    # Dashboard Home
    path('', views.dashboard_home, name='admin_dashboard'),
    path('api/dashboard-stats/', views.dashboard_stats_api, name='dashboard_stats_api'),

    # Product CRUD
    path('products/', views.product_list, name='product_list'),
    path('products/add/', views.add_product, name='add_product'),
    path('products/<int:pk>/edit/', views.edit_product, name='edit_product'),
    path('products/<int:pk>/delete/', views.delete_product, name='delete_product'),

    # Baaki ke views: orders, customers, search, export
    path('orders/', views.order_list, name='order_list'),
    path('orders/<int:pk>/status/', views.update_order_status, name='update_order_status'),
    path('orders/search/', views.search_orders, name='search_orders'),
    path('customers/', views.customer_list, name='customer_list'),
    path('orders/export/', views.export_orders, name='export_orders'),
    path('orders/download/', views.download_orders_csv, name='download_orders_csv'),

]
