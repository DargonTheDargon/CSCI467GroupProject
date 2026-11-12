from django import forms

from .models import LineItem, Note, Quote


class LineItemForm(forms.ModelForm):
    class Meta:
        model = LineItem
        fields = ['description','quantity','price']

class NoteForm(forms.ModelForm):
    class Meta:
        model = Note
        fields = ['text']

class DiscountForm(forms.ModelForm):
    class Meta:
        model = Quote
        fields = ['discount_type','discount_amount']
        widgets = {
            'discount_type':forms.RadioSelect()
        }