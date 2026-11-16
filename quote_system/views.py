

from django.contrib.auth import authenticate, login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, ListView

from .forms import DiscountForm, LineItemForm, NoteForm
from .models import Note, Quote, SalesAssociate


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



        


    
