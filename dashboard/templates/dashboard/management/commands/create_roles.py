from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from dashboard.models import Product, Order

class Command(BaseCommand):
    help = 'Create user roles and assign permissions'

    def handle(self, *args, **kwargs):
        # Create groups
        admin_group, _ = Group.objects.get_or_create(name='Admin')
        manager_group, _ = Group.objects.get_or_create(name='Manager')
        support_group, _ = Group.objects.get_or_create(name='Support')

        # Get content types for your models
        product_ct = ContentType.objects.get_for_model(Product)
        order_ct = ContentType.objects.get_for_model(Order)

        # Admin: full permissions
        admin_perms = Permission.objects.filter(content_type__in=[product_ct, order_ct])
        admin_group.permissions.set(admin_perms)

        # Manager: Can view and change
        manager_perms = Permission.objects.filter(
            content_type__in=[product_ct, order_ct],
            codename__in=[
                'view_product', 'change_product',
                'view_order', 'change_order'
            ]
        )
        manager_group.permissions.set(manager_perms)

        # Support: Can view only
        support_perms = Permission.objects.filter(
            content_type__in=[product_ct, order_ct],
            codename__in=[
                'view_product', 'view_order'
            ]
        )
        support_group.permissions.set(support_perms)

        self.stdout.write(self.style.SUCCESS("✅ Roles and permissions created successfully!"))
