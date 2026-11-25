from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import CharField, Count, F, Q, Value
from django.db.models.functions import Concat
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format
from django.views.decorators.http import require_POST
from django.db.models.functions import Lower
from django.views.generic import DetailView, ListView
from django.db import transaction

from .forms import DiscountForm, EditAssociateForm, LineItemForm, NoteForm, AddAssociateForm, PurchaseOrderForm
from .models import Customer, PurchaseOrder, Quote, SalesAssociate, User


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
    actions = {
        'edit', 'confirm_edit', 'apply_discount', 'secret_notes',
        'view_secret_notes', 'add_secret_note', 'save_secret_note',
        'delete_secret_note', 'confirm_delete_secret_note', 'keep_secret_note',
        'sanction', 'confirm_sanction',
    }
    selection_session_key = 'sanction_interface_selected_quote_id'
    sort_order = {
        'status': 'status',
        '-status': '-status',
        'id': 'pk',
        '-id': '-pk',
    }.get(request.GET.get('sort'), 'pk')
    if request.method == 'POST' and request.POST.get('action') == 'toggle_quote':
        quote = get_object_or_404(
            Quote, pk=request.POST.get('quote_id'), status=Quote.Status.FINALIZED
        )
        redirect_url = reverse('sanction_interface')
        query_string = request.GET.urlencode()
        if query_string:
            redirect_url = f"{redirect_url}?{query_string}"
        if str(request.session.get(selection_session_key)) == str(quote.pk):
            request.session.pop(selection_session_key, None)
            return redirect(redirect_url)
        request.session[selection_session_key] = quote.pk
        return redirect(f"{redirect_url}#quote-{quote.pk}")

    action_submitted = request.method == 'POST' and request.POST.get('action') in actions
    selected_quote_id = request.session.get(selection_session_key)
    selected_quote = Quote.objects.select_related('customer').filter(
        pk=selected_quote_id, status=Quote.Status.FINALIZED
    ).first() if selected_quote_id else None
    if selected_quote_id and selected_quote is None:
        request.session.pop(selection_session_key, None)
        selected_quote_id = None
    selected_quote_ids = [selected_quote_id] if selected_quote_id else []
    show_no_quote_error = action_submitted and not selected_quote_ids
    action = request.POST.get('action') if request.method == 'POST' else None
    show_secret_notes_view = bool(selected_quote) and (
        action == 'view_secret_notes'
        or request.method == 'GET' and request.GET.get('notes') == 'view'
    )
    show_add_secret_note = action == 'add_secret_note' and bool(selected_quote)
    secret_note_form = NoteForm()
    if action == 'save_secret_note' and selected_quote:
        secret_note_form = NoteForm(request.POST)
        if secret_note_form.is_valid():
            note = secret_note_form.save(commit=False)
            note.quote = selected_quote
            note.save()
            query_parameters = request.GET.copy()
            query_parameters['notes'] = 'view'
            return redirect(f"{reverse('sanction_interface')}?{query_parameters.urlencode()}")
        else:
            show_add_secret_note = True
    pending_note = None
    show_delete_secret_note_confirmation = False
    if action in {'delete_secret_note', 'confirm_delete_secret_note', 'keep_secret_note'} and selected_quote:
        pending_note = get_object_or_404(selected_quote.notes, pk=request.POST.get('note_id'))
        if action == 'delete_secret_note':
            show_delete_secret_note_confirmation = True
        elif action == 'confirm_delete_secret_note':
            pending_note.delete()
            query_parameters = request.GET.copy()
            query_parameters['notes'] = 'view'
            return redirect(f"{reverse('sanction_interface')}?{query_parameters.urlencode()}")
        else:
            query_parameters = request.GET.copy()
            query_parameters['notes'] = 'view'
            return redirect(f"{reverse('sanction_interface')}?{query_parameters.urlencode()}")
    show_edit_confirmation = request.method == 'POST' and request.POST.get('action') == 'edit' and bool(selected_quote_id)
    show_sanction_confirmation = request.method == 'POST' and request.POST.get('action') == 'sanction' and bool(selected_quote_id)
    show_secret_notes = action == 'secret_notes' and bool(selected_quote)
    show_apply_discount = request.method == 'POST' and request.POST.get('action') == 'apply_discount' and bool(selected_quote_id)
    if request.method == 'POST' and request.POST.get('action') == 'confirm_edit' and selected_quote_id:
        quote_url = reverse('quote_view', kwargs={'pk': selected_quote_id})
        return redirect(f"{quote_url}?source=sanction")
    if request.method == 'POST' and request.POST.get('action') == 'confirm_sanction' and selected_quote_ids:
        Quote.objects.filter(
            pk=selected_quote_id, status=Quote.Status.FINALIZED
        ).update(status=Quote.Status.SANCTIONED)
        request.session.pop(selection_session_key, None)
        selected_quote_id = None
        selected_quote_ids = []
        selected_quote = None
    quotes = Quote.objects.filter(status=Quote.Status.FINALIZED).select_related(
        'customer'
    ).annotate(line_item_count=Count('line_items')).order_by(sort_order)
    secret_notes = selected_quote.notes.order_by('-date_added') if selected_quote and show_secret_notes_view else []
    sanction_interface_url = reverse('sanction_interface')
    if request.GET:
        sanction_interface_url = f"{sanction_interface_url}?{request.GET.urlencode()}"
    return render(request, 'sanction_interface.html', {'show_no_quote_error': show_no_quote_error, 'show_edit_confirmation': show_edit_confirmation, 'show_sanction_confirmation': show_sanction_confirmation, 'show_secret_notes': show_secret_notes, 'show_secret_notes_view': show_secret_notes_view, 'show_add_secret_note': show_add_secret_note, 'show_delete_secret_note_confirmation': show_delete_secret_note_confirmation, 'pending_note': pending_note, 'secret_note_form': secret_note_form, 'selected_quote': selected_quote, 'secret_notes': secret_notes, 'show_apply_discount': show_apply_discount, 'quotes': quotes, 'selected_quote_ids': selected_quote_ids, 'sanction_interface_url': sanction_interface_url})

# list sanctioned quotes
@login_required
def purchase_orders(request): 
    sort_order = {
        'id': 'pk',
        '-id': '-pk',
        'customer': Lower('customer__name'),
        '-customer': Lower('customer__name').desc(),
    }.get(request.GET.get('sort'), 'pk')
    quotes = Quote.objects.filter(status=Quote.Status.SANCTIONED).select_related(
        'customer'
    ).annotate(line_item_count=Count('line_items')).order_by(sort_order)
    return render(request, 'purchase_orders.html', {'quotes': quotes})

# show details and create a purchase order for the selected quote
@login_required
def create_purchase_order(request, pk): 
    quote = get_object_or_404(
        Quote.objects.select_related('customer', 'sales_associate__user'), pk=pk
    )
    purchase_order = PurchaseOrder.objects.filter(quote=quote).first()
    subtotal = quote.subtotal_price()
    quoted_price = quote.total_price()
    context = {
        'quote': quote,
        'purchase_order': purchase_order,
        'line_items': quote.line_items.all(),
        'subtotal': subtotal,
        'quote_discount_total': subtotal - quoted_price,
        'quoted_price': quoted_price,
    }
    if purchase_order:
        context['final_discount_total'] = quoted_price - purchase_order.final_price
    elif quote.status == Quote.Status.SANCTIONED:
        form = PurchaseOrderForm(request.POST or None)
        if request.method == 'POST' and form.is_valid():
            with transaction.atomic():
                # lock the quote so a double submit can't create two purchase orders
                quote = Quote.objects.select_for_update().select_related(
                    'customer', 'sales_associate'
                ).get(pk=quote.pk)
                if quote.status != Quote.Status.SANCTIONED or PurchaseOrder.objects.filter(quote=quote).exists():
                    return redirect('create_purchase_order', pk=quote.pk)

                purchase_order = form.save(commit=False)
                purchase_order.quote = quote
                purchase_order.final_price = max(
                    quoted_price - final_discount(purchase_order, quoted_price), Decimal('0.00')
                )
                # external processing system returns processing date and the associate's commission rate.
                processing_date, commission_rate = process_purchase_order(purchase_order)
                purchase_order.processing_date = processing_date
                purchase_order.commission_amount = (
                    purchase_order.final_price * commission_rate / Decimal(100)
                ).quantize(Decimal('0.01'))
                purchase_order.save()

                SalesAssociate.objects.filter(pk=quote.sales_associate.pk).update(
                    accumulated_commission=F('accumulated_commission') + purchase_order.commission_amount
                )
                quote.status = Quote.Status.ORDERED
                quote.save(update_fields=['status'])

            # success message (no email actually sent)
            messages.success(
                request,
                f"The order was placed on {date_format(timezone.localdate(processing_date), 'F j, Y')} "
                f"and an email was sent to {quote.customer.email}.",
            )
            return redirect('create_purchase_order', pk=quote.pk)
        context['form'] = form
    return render(request, 'create_purchase_order.html', context)

# calculate final discount
def final_discount(purchase_order, base_amount): 
    if purchase_order.discount_type == Quote.DiscountType.PERCENT:
        return (base_amount * purchase_order.discount_amount / Decimal(100)).quantize(Decimal('0.01'))
    return min(purchase_order.discount_amount, base_amount)

# return processing date and commission rate for a purchase order
def process_purchase_order(purchase_order): 
    return timezone.now(), purchase_order.quote.sales_associate.commission_rate

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
@require_POST
@user_passes_test(is_admin)
def delete_associate(request, pk): # view to delete an existing sales associate. Only accessible by admin users.
    associate = get_object_or_404(SalesAssociate, pk=pk)
    if request.method == 'POST':
        user = associate.user
        associate.delete()
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
        context['from_sanction_interface'] = self.request.GET.get('source') == 'sanction'
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
