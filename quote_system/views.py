

from django.contrib.auth import authenticate, login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.db.models import CharField, Q, Value
from django.db.models.functions import Concat
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, ListView

from .forms import DiscountForm, LineItemForm, NoteForm
from .models import Customer, Quote, SalesAssociate, User


@require_POST
def logout_page(request):
    auth_logout(request)
    return redirect('login')

def login_page(request):
    if request.method == 'POST':
        user = authenticate(request, username=request.POST.get('username'), password=request.POST.get('password'))
        if user is not None:
            login(request, user)
            return redirect('quote_list')  # Redirect to the quote list page after successful login
        
        return render(request, 'login.html', {'error': 'Invalid username or password.'})
    
    return render(request, 'login.html')

@login_required
def quote_list(request):
    sales_associates = SalesAssociate.objects.all()
    customers = Customer.objects.all()
    context = {
        'sales_associates':sales_associates,
        'customers':customers
    }
    return render(request, 'quote_list.html',context)

@login_required
def quote_view(request):
    return render(request, 'quote_view.html')

@login_required
def sanction_interface(request):
    return render(request, 'sanction_interface.html')

@login_required
def purchase_orders(request):
    return render(request, 'purchase_orders.html')

@login_required
def associates(request):
    sales_associates = SalesAssociate.objects.select_related('user').order_by('user__username')
    return render(request, 'associates.html', {'sales_associates': sales_associates})

class QuoteListView(ListView):
    template_name = 'quote_list.html'
        
    def get_queryset(self):
        queryset = Quote.objects.all()
        sort = self.request.GET.get('sort')
        if sort:
            if sort == "status":
                queryset = queryset.order_by("status")
            elif sort == "-status":
                queryset = queryset.order_by("-status")
            elif sort == "id":
                queryset = queryset.order_by("id")
            elif sort == "-id":
                queryset = queryset.order_by("-id")

        search = self.request.GET.get('search')
        if search:
            queryset = queryset.annotate(
                sales_associate_name=Concat(
                    'sales_associate__user__first_name',
                    Value(' '),
                    'sales_associate__user__last_name',
                    output_field=CharField()
                )
            )
            queryset = queryset.filter(
                Q(sales_associate_name__icontains=search)
                | Q(customer__name__icontains=search)
                | Q(status__icontains=search)
            )
            if (self.request.user.role == User.Role.SALES_ASSOCIATE):
                queryset = queryset.filter(sales_associate__user=self.request.user)
        return queryset

    def get_context_data(self, **kwargs):
            context = super().get_context_data(**kwargs)
            context['customers'] = Customer.objects.all()
            context['sales_associates'] = SalesAssociate.objects.all()
            return context

    def post(self, request, *args, **kwargs):

        if 'add_quote' in request.POST:
            sales_associate_data = request.POST.get('sales-associate')
            print(sales_associate_data)
            customer_data = request.POST.get('customer')
            quote = Quote(sales_associate_id = sales_associate_data, customer_id = customer_data)
            quote.save()
            
        return redirect('quote_view', pk=quote.pk)
        

class QuoteView(DetailView):
    template_name = 'quote_view.html'

    def get_queryset(self):
        quote_id=self.kwargs.get('pk')
        return Quote.objects.filter(pk=quote_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault('line_item_form',LineItemForm())
        context.setdefault('note_form',NoteForm())
        context.setdefault('discount_form',DiscountForm())
        context['discount_type'] = Quote.DiscountType.choices
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        quote = self.object
        line_item_form = LineItemForm(request.POST)
        note_form = NoteForm(request.POST)
        discount_form = DiscountForm(request.POST, instance=quote)
        line_item_id = request.POST.get('delete_line_item')
        finalize = request.POST.get('finalize')

        if line_item_id:
            line_item = get_object_or_404(quote.line_items,pk=line_item_id)
            line_item.delete()
            return redirect('quote_view', pk=quote.pk)

        if 'add_line_item' in request.POST:
            if line_item_form.is_valid():
                line_item = line_item_form.save(commit=False)
                line_item.quote = quote
                line_item.save()
                return redirect('quote_view', pk=quote.pk)
            return self.render_to_response(self.get_context_data(line_item=line_item))
    
        elif 'add_note' in request.POST:
            if note_form.is_valid():
                note = note_form.save(commit=False)
                note.quote = quote
                note.save()
                return redirect('quote_view', pk=quote.pk)
            return self.render_to_response(self.get_context_data(note_form=note_form))

        elif 'add_discount' in request.POST:
            if discount_form.is_valid():
                discount_form.save()
                return redirect('quote_view', pk=quote.pk)
            return self.render_to_response(self.get_context_data(discount_form=discount_form))

        elif 'finalize' in request.POST:
            if (quote.status == 'draft'):
                quote.status = 'finalized'
                quote.final_price = quote.total_price()
                quote.save()
                return redirect('quote_view', pk=quote.pk)
            
        elif 'unfinalize' in request.POST:
            if (quote.status == 'finalized'):
                quote.status = 'draft'
                quote.save()
                return redirect('quote_view', pk=quote.pk)



        


    
