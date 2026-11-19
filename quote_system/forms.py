from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import LineItem, Note, Quote, User


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

class AddAssociateForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ['first_name', 'last_name', 'email', 'username']

class EditAssociateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'username']