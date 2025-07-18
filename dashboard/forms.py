# dashboard/forms.py

from django import forms
from .models import Product, Order

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = '__all__'

class OrderStatusForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['status']
