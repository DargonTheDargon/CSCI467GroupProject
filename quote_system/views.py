from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import CharField, Count, F, Q, Value
from django.db.models.functions import Concat
from django.http import HttpResponseBadRequest
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
    # Recognize actions that need a quote to be selected
    actions = {
        'edit', 'confirm_edit', 'apply_discount', 'choose_discount_type',
        'save_sanction_discount', 'secret_notes',
        'view_secret_notes', 'add_secret_note', 'save_secret_note',
        'delete_secret_note', 'confirm_delete_secret_note', 'keep_secret_note',
        'sanction', 'confirm_sanction',
    }
    # Remember the selected quote and show notes once after a redirect
    selection_session_key = 'sanction_interface_selected_quote_id'
    notes_view_session_key = 'sanction_notes_view_after_redirect'

    def build_sanction_interface_url(fragment=None):
        # Keep search and sort, drop the notes parameter, and optionally add an anchor
        query_parameters = request.GET.copy()
        query_parameters.pop('notes', None)
        url = reverse('sanction_interface')
        if query_parameters:
            url = f"{url}?{query_parameters.urlencode()}"
        if fragment:
            url = f"{url}#{fragment}"
        return url

    def redirect_to_secret_notes_view():
        # A one-time flag keeps an old URL from reopening the notes
        request.session[notes_view_session_key] = True
        return redirect(build_sanction_interface_url())

    # Use the supported ID sort options and default to ascending ID
    sort_order = {
        'id': 'pk',
        '-id': '-pk',
    }.get(request.GET.get('sort'), 'pk')
    # Handle selection separately so the page can scroll to that quote
    if request.method == 'POST' and request.POST.get('action') == 'toggle_quote':
        # Clicking the selected quote again clears it
        quote = get_object_or_404(
            Quote, pk=request.POST.get('quote_id'), status=Quote.Status.FINALIZED
        )
        # Clear the selection if this quote is already selected
        if str(request.session.get(selection_session_key)) == str(quote.pk):
            request.session.pop(selection_session_key, None)
            return redirect(build_sanction_interface_url())
        request.session[selection_session_key] = quote.pk
        return redirect(build_sanction_interface_url(fragment=f'quote-{quote.pk}'))

    # Only recognized quote actions can trigger the no-selection error
    action_submitted = request.method == 'POST' and request.POST.get('action') in actions
    selected_quote_id = request.session.get(selection_session_key)
    selected_quote = Quote.objects.select_related('customer').filter(
        pk=selected_quote_id, status=Quote.Status.FINALIZED
    ).first() if selected_quote_id else None
    # Clear the selection if the quote is no longer finalized
    if selected_quote_id and selected_quote is None:
        request.session.pop(selection_session_key, None)
        selected_quote_id = None
    # Show an error when a quote action has no selected quote
    show_no_quote_error = action_submitted and not selected_quote_id
    action = request.POST.get('action') if request.method == 'POST' else None
    # Show the notes list after View or once after a save or delete
    show_notes_after_redirect = (
        request.method == 'GET'
        and request.session.pop(notes_view_session_key, False)
    )
    show_secret_notes_view = bool(selected_quote) and (
        action == 'view_secret_notes'
        or show_notes_after_redirect
    )
    show_add_secret_note = action == 'add_secret_note' and bool(selected_quote)
    secret_note_form = NoteForm()
    # Save a valid note or keep the form open to show its errors
    if action == 'save_secret_note' and selected_quote:
        secret_note_form = NoteForm(request.POST)
        if secret_note_form.is_valid():
            note = secret_note_form.save(commit=False)
            note.quote = selected_quote
            note.save()
            return redirect_to_secret_notes_view()
        else:
            show_add_secret_note = True
    pending_note = None
    show_delete_secret_note_confirmation = False
    # Only allow note actions on notes belonging to the selected quote
    if action in {'delete_secret_note', 'confirm_delete_secret_note', 'keep_secret_note'} and selected_quote:
        pending_note = get_object_or_404(selected_quote.notes, pk=request.POST.get('note_id'))
        # Ask for confirmation before deleting
        if action == 'delete_secret_note':
            show_delete_secret_note_confirmation = True
        # Delete after confirmation or return to the list when kept
        elif action == 'confirm_delete_secret_note':
            pending_note.delete()
            return redirect_to_secret_notes_view()
        else:
            return redirect_to_secret_notes_view()
    # Set which confirmation or popup the template should show
    show_edit_confirmation = request.method == 'POST' and request.POST.get('action') == 'edit' and bool(selected_quote_id)
    show_sanction_confirmation = request.method == 'POST' and request.POST.get('action') == 'sanction' and bool(selected_quote_id)
    show_secret_notes = action == 'secret_notes' and bool(selected_quote)
    show_apply_discount = action in {
        'apply_discount', 'choose_discount_type', 'save_sanction_discount'
    } and bool(selected_quote)
    show_discount_amount_form = action in {
        'choose_discount_type', 'save_sanction_discount'
    } and bool(selected_quote)
    selected_discount_type = None
    sanction_discount_form = DiscountForm(instance=selected_quote) if selected_quote else DiscountForm()
    # Check the discount type before showing the amount field
    if show_discount_amount_form:
        selected_discount_type = request.POST.get('discount_type')
        valid_discount_types = dict(Quote.DiscountType.choices)
        if selected_discount_type not in valid_discount_types:
            return HttpResponseBadRequest('Invalid discount type.')
        # Limit percentage entry in the browser as well as on the server
        if selected_discount_type == Quote.DiscountType.PERCENT:
            sanction_discount_form.fields['discount_amount'].widget.attrs['max'] = '100'
    # Save a valid discount and update the quote total
    if action == 'save_sanction_discount' and selected_quote:
        sanction_discount_form = DiscountForm(request.POST, instance=selected_quote)
        if selected_discount_type == Quote.DiscountType.PERCENT:
            sanction_discount_form.fields['discount_amount'].widget.attrs['max'] = '100'
        # Leave invalid submissions in the dialog so their errors can be shown
        if sanction_discount_form.is_valid():
            discounted_quote = sanction_discount_form.save(commit=False)
            discounted_quote.final_price = discounted_quote.total_price()
            discounted_quote.save(update_fields=[
                'discount_type', 'discount_amount', 'final_price'
            ])
            return redirect(build_sanction_interface_url())
    # Open the quote editor after the user confirms
    if request.method == 'POST' and request.POST.get('action') == 'confirm_edit' and selected_quote_id:
        quote_url = reverse('quote_view', kwargs={'pk': selected_quote_id})
        return redirect(f"{quote_url}?source=sanction")
    # Sanction only a still-finalized quote and clear the selection
    if request.method == 'POST' and request.POST.get('action') == 'confirm_sanction' and selected_quote_id:
        Quote.objects.filter(
            pk=selected_quote_id, status=Quote.Status.FINALIZED
        ).update(status=Quote.Status.SANCTIONED)
        request.session.pop(selection_session_key, None)
        selected_quote_id = None
        selected_quote = None
    # Show only finalized quotes and apply search and sorting
    quotes = Quote.objects.filter(status=Quote.Status.FINALIZED).select_related(
        'customer'
    )
    search = request.GET.get('search')
    # Match the search term against customer, associate, or status
    if search:
        quotes = quotes.annotate(
            sales_associate_name=Concat(
                'sales_associate__user__first_name',
                Value(' '),
                'sales_associate__user__last_name',
                output_field=CharField()
            )
        ).filter(
            Q(sales_associate_name__icontains=search)
            | Q(customer__name__icontains=search)
            | Q(status__icontains=search)
        )
    quotes = quotes.annotate(line_item_count=Count('line_items')).order_by(sort_order)
    secret_notes = selected_quote.notes.order_by('-date_added') if selected_quote and show_secret_notes_view else []
    sanction_interface_url = build_sanction_interface_url()
    return render(request, 'sanction_interface.html', {'show_no_quote_error': show_no_quote_error, 'show_edit_confirmation': show_edit_confirmation, 'show_sanction_confirmation': show_sanction_confirmation, 'show_secret_notes': show_secret_notes, 'show_secret_notes_view': show_secret_notes_view, 'show_add_secret_note': show_add_secret_note, 'show_delete_secret_note_confirmation': show_delete_secret_note_confirmation, 'pending_note': pending_note, 'secret_note_form': secret_note_form, 'selected_quote': selected_quote, 'selected_quote_id': selected_quote_id, 'secret_notes': secret_notes, 'show_apply_discount': show_apply_discount, 'show_discount_amount_form': show_discount_amount_form, 'selected_discount_type': selected_discount_type, 'sanction_discount_form': sanction_discount_form, 'quotes': quotes, 'sanction_interface_url': sanction_interface_url})

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
