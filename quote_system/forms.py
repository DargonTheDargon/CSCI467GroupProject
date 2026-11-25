from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import LineItem, Note, PurchaseOrder, Quote, User


class LineItemForm(forms.ModelForm):
    class Meta:
        model = LineItem
        fields = ['description','quantity','price']

class NoteForm(forms.ModelForm):
    class Meta:
        model = Note
        fields = ['text']
        error_messages = {'text': {'required': 'Please Fill Out This Field.'}}

class DiscountForm(forms.ModelForm):
    class Meta:
        model = Quote
        fields = ['discount_type','discount_amount']
        widgets = {
            'discount_type':forms.RadioSelect()
        }

class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = ['discount_type', 'discount_amount']
        labels = {
            'discount_type': 'Final Discount Type',
            'discount_amount': 'Final Discount',
        }
    # validate that the discount is not negative and that a percentage discount is not more than 100%
    def clean(self):
        cleaned_data = super().clean()
        discount_type = cleaned_data.get('discount_type')
        discount_amount = cleaned_data.get('discount_amount')
        if discount_amount is not None:
            if discount_amount < 0:
                self.add_error('discount_amount', 'The discount cannot be negative.')
            elif discount_type == Quote.DiscountType.PERCENT and discount_amount > 100:
                self.add_error('discount_amount', 'A percentage discount cannot be more than 100%.')
        return cleaned_data

class AddAssociateForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ['first_name', 'last_name', 'email', 'username']

class EditAssociateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'username']