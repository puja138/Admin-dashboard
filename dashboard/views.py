# dashboard/views.py
import csv, json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import user_passes_test, login_required
from django.db.models import Count, Sum, F, ExpressionWrapper, DecimalField, Min
from django.db.models.functions import TruncMonth, TruncDay
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.models import User

from .models import Product, Order, Notification
from .forms import ProductForm, OrderStatusForm

LOW_STOCK_THRESHOLD = 10

def home_redirect(request):
    return redirect('admin_dashboard')

def staff_check(user):
    return user.is_staff


# ------------------- Dashboard -------------------
@user_passes_test(staff_check)
def dashboard_home(request):
    total_products = Product.objects.count()
    total_orders = Order.objects.count()
    confirmed_orders = Order.objects.filter(status='Confirmed').count()
    cancelled_orders = Order.objects.filter(status='Cancelled').count()

    # Monthly orders & revenue
    orders_by_month = (
        Order.objects
        .annotate(month=TruncMonth('order_date'))
        .values('month')
        .annotate(
            count=Count('id'),
            revenue=Sum(ExpressionWrapper(
                F('quantity') * F('product__price'),
                output_field=DecimalField()
            ))
        ).order_by('month')
    )
    months = [o['month'].strftime('%B') for o in orders_by_month]
    order_counts = [o['count'] for o in orders_by_month]
    revenues = [float(o['revenue'] or 0) for o in orders_by_month]

    # Top products
    top_products = (
        Order.objects
        .values('product__name')
        .annotate(total_sold=Sum('quantity'))
        .order_by('-total_sold')[:5]
    )
    product_names = [p['product__name'] for p in top_products]
    product_counts = [p['total_sold'] for p in top_products]

    # Order status breakdown
    status_counts = Order.objects.values('status').annotate(count=Count('id'))
    statuses = [s['status'] for s in status_counts]
    status_values = [s['count'] for s in status_counts]

    # Daily unique customers
    daily_traffic = (
        Order.objects
        .annotate(day=TruncDay('order_date'))
        .values('day')
        .annotate(unique_customers=Count('customer_email', distinct=True))
        .order_by('day')[:30]
    )
    days = [d['day'].strftime('%Y-%m-%d') for d in daily_traffic]
    daily_users = [d['unique_customers'] for d in daily_traffic]

    unread_count = 0
    if request.user.is_authenticated:
        unread_count = Notification.objects.filter(user=request.user, is_read=False).count()

    return render(request, 'dashboard/admin_dashboard.html', {
        'total_products': total_products,
        'total_orders': total_orders,
        'confirmed_orders': confirmed_orders,
        'cancelled_orders': cancelled_orders,
        'months': json.dumps(months),
        'counts': json.dumps(order_counts),
        'revenues': json.dumps(revenues),
        'product_names': json.dumps(product_names),
        'product_counts': json.dumps(product_counts),
        'statuses': json.dumps(statuses),
        'status_values': json.dumps(status_values),
        'days': json.dumps(days),
        'daily_users': json.dumps(daily_users),
        'unread_count': unread_count,  # 👈 pass to template
    })


# ------------------- Product Management -------------------
@user_passes_test(staff_check)
def product_list(request):
    q = request.GET.get('search', '')
    qs = Product.objects.all()
    if q:
        qs = qs.filter(name__icontains=q)
    return render(request, 'dashboard/product_list.html', {'products': qs})

@user_passes_test(staff_check)
def add_product(request):
    form = ProductForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('product_list')
    return render(request, 'dashboard/add_product.html', {'form': form})

@user_passes_test(staff_check)
def edit_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form = ProductForm(request.POST or None, request.FILES or None, instance=product)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('product_list')
    return render(request, 'dashboard/add_product.html', {
        'form': form,
        'is_edit': True,
        'product': product
    })

@user_passes_test(staff_check)
def delete_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.delete()
    return redirect('product_list')


# ------------------- Order Management -------------------
@user_passes_test(staff_check)
def order_list(request):
    status = request.GET.get('status', '')
    qs = Order.objects.all().order_by('-order_date')
    if status:
        qs = qs.filter(status=status)
    return render(request, 'dashboard/order_list.html', {
        'orders': qs,
        'current_status': status,
    })

@user_passes_test(staff_check)
def update_order_status(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if request.method == 'POST':
        form = OrderStatusForm(request.POST, instance=order)
        if form.is_valid():
            form.save()
    return redirect('order_list')

@user_passes_test(staff_check)
def search_orders(request):
    return render(request, 'dashboard/search_orders.html')


# ------------------- Customer List -------------------
@user_passes_test(staff_check)
def customer_list(request):
    customers = (
        Order.objects
        .values('customer_email', 'customer_name')
        .annotate(
            total_orders=Count('id'),
            first_order=Min('order_date')
        )
        .order_by('-total_orders')
    )
    return render(request, 'dashboard/customer_list.html', {'customers': customers})


# ------------------- Export / CSV -------------------
@user_passes_test(staff_check)
def export_orders(request):
    return render(request, 'dashboard/export_orders.html')

@user_passes_test(staff_check)
def download_orders_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="orders.csv"'
    writer = csv.writer(response)
    writer.writerow(['Order ID', 'Customer Name', 'Customer Email', 'Product', 'Quantity', 'Status', 'Order Date'])

    for o in Order.objects.select_related('product').all().order_by('-order_date'):
        writer.writerow([
            o.id,
            o.customer_name,
            o.customer_email,
            o.product.name,
            o.quantity,
            o.status,
            o.order_date.strftime('%Y-%m-%d %H:%M'),
        ])
    return response


# ------------------- AJAX API -------------------
@user_passes_test(staff_check)
def dashboard_stats_api(request):
    data = {
        'total_products': Product.objects.count(),
        'total_orders': Order.objects.count(),
        'confirmed_orders': Order.objects.filter(status='Confirmed').count(),
        'cancelled_orders': Order.objects.filter(status='Cancelled').count(),
    }
    return JsonResponse(data)


# ------------------- Notifications -------------------
@receiver(post_save, sender=Product)
def check_inventory(sender, instance, **kwargs):
    if instance.stock <= LOW_STOCK_THRESHOLD:
        admins = User.objects.filter(is_staff=True)
        for admin in admins:
            Notification.objects.create(
                notif_type='inventory',
                message=f"Inventory low for product {instance.name}: only {instance.stock} left.",
                user=admin
            )
            send_mail(
                subject="Inventory Low Alert",
                message=f"Inventory for product {instance.name} is low ({instance.stock} remaining).",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[admin.email],
            )

@receiver(post_save, sender=Order)
def new_order_notification(sender, instance, created, **kwargs):
    admins = User.objects.filter(is_staff=True)
    if created:
        for admin in admins:
            Notification.objects.create(
                notif_type='order',
                message=f"New order #{instance.id} placed by {instance.customer_name}.",
                user=admin
            )
            send_mail(
                subject="New Order Alert",
                message=f"A new order #{instance.id} has been placed.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[admin.email],
            )
    elif instance.status == 'payment_failed':
        for admin in admins:
            Notification.objects.create(
                notif_type='payment',
                message=f"Payment failed for order #{instance.id}.",
                user=admin
            )
            send_mail(
                subject="Payment Failed Alert",
                message=f"Payment failed for order #{instance.id}.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[admin.email],
            )


# ------------------- Notification Center -------------------
@login_required
def notification_center(request):
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    notifications.filter(is_read=False).update(is_read=True)
    return render(request, 'dashboard/notification_center.html', {
        'notifications': notifications,
    })
