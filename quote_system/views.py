

from django.contrib.auth import authenticate, login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.db.models.functions import Lower
from django.views.generic import DetailView, ListView
from django.db import transaction

from .forms import DiscountForm, EditAssociateForm, LineItemForm, NoteForm, AddAssociateForm
from .models import Quote, SalesAssociate


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
    return render(request, 'quote_list.html')

@login_required
def quote_view(request):
    return render(request, 'quote_view.html')

@login_required
def sanction_interface(request):
    return render(request, 'sanction_interface.html')

@login_required
def purchase_orders(request):
    return render(request, 'purchase_orders.html')

def is_admin(user): # checks if the user is an admin
    return user.role == 'admin'

@login_required 
@user_passes_test(is_admin) # checks if the user is an admin before allowing access to the view
def associates(request): # renders the associates page and allows sorting of the sales associates based on the query parameters
    sort_options = {
        'first_name': Lower('user__first_name'),
        'last_name': Lower('user__last_name'),
        '-first_name': Lower('user__first_name').desc(),
        '-last_name': Lower('user__last_name').desc(),
        "accumulated_commission": ("accumulated_commission"),
        "-accumulated_commission": ("-accumulated_commission"),
    }
    sort = request.GET.get('sort')
    ordering = sort_options.get(sort, Lower('user__first_name'))  # Default ordering by first name

    sales_associates = SalesAssociate.objects.select_related('user').order_by(ordering, 'user__last_name')  # Secondary ordering by last name
    return render(request, 'associates.html', {'sales_associates': sales_associates})

@login_required
@user_passes_test(is_admin)
def add_associate(request): # view to add a new sales associate. Only accessible by admin users.
    if request.method == 'POST': # If the request method is POST, it means the form has been submitted. We need to process the form data.
        form = AddAssociateForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                user = form.save(commit=False)
                user.role = 'sales_associate'  # Set the role to 'sales_associate'
                user.save()
                SalesAssociate.objects.create(user=user, accumulated_commission=0)
            return redirect('associates')
    else:
        form = AddAssociateForm() # If the request method is GET, create an empty form instance to be rendered in the template.
    return render(request, 'add_associate.html', {'form': form})

@login_required
@user_passes_test(is_admin)
def edit_associate(request, pk): # view to edit an existing sales associate. Only accessible by admin users.
    associate = get_object_or_404(SalesAssociate, pk=pk)
    if request.method == 'POST':
        form = EditAssociateForm(request.POST, instance=associate.user)
        if form.is_valid():
            form.save()
            return redirect('associates')
    else:
        form = EditAssociateForm(instance=associate.user)
    return render(request, 'edit_associate.html', {'form': form, 'associate': associate})

@login_required
@user_passes_test(is_admin)
def delete_associate(request, pk): # view to delete an existing sales associate. Only accessible by admin users.
    associate = get_object_or_404(SalesAssociate, pk=pk)
    if request.method == 'POST':
        user = associate.user
        associate.delete()
        user.delete()
        return redirect('associates')
    return render(request, 'delete_associate.html', {'associate': associate})

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
        return queryset

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



        


    
