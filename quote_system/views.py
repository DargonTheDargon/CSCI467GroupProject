from django.contrib.auth import authenticate, login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
from .models import Quote, SalesAssociate

# Create your views here.

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
def sanction_interface(request):
    actions = {'edit', 'apply_discount', 'secret_notes', 'sanction', 'confirm_sanction'}
    selection_session_key = 'sanction_interface_selected_quote_id'
    if request.method == 'POST' and request.POST.get('action') == 'toggle_quote':
        quote = get_object_or_404(Quote, pk=request.POST.get('quote_id'))
        if str(request.session.get(selection_session_key)) == str(quote.pk):
            request.session.pop(selection_session_key, None)
        else:
            request.session[selection_session_key] = quote.pk
        return redirect(f"{reverse('sanction_interface')}#quote-{quote.pk}")

    action_submitted = request.method == 'POST' and request.POST.get('action') in actions
    selected_quote_id = request.session.get(selection_session_key)
    if selected_quote_id and not Quote.objects.filter(pk=selected_quote_id).exists():
        request.session.pop(selection_session_key, None)
        selected_quote_id = None
    selected_quote_ids = [selected_quote_id] if selected_quote_id else []
    show_no_quote_error = action_submitted and not selected_quote_ids
    show_sanction_confirmation = request.method == 'POST' and request.POST.get('action') == 'sanction' and bool(selected_quote_id)
    show_secret_notes = request.method == 'POST' and request.POST.get('action') == 'secret_notes' and bool(selected_quote_id)
    show_apply_discount = request.method == 'POST' and request.POST.get('action') == 'apply_discount' and bool(selected_quote_id)
    if request.method == 'POST' and request.POST.get('action') == 'confirm_sanction' and selected_quote_ids:
        Quote.objects.filter(pk=selected_quote_id).update(status=Quote.Status.SANCTIONED)
    quotes = Quote.objects.select_related('customer').annotate(line_item_count=Count('line_items')).order_by('pk')
    return render(request, 'sanction_interface.html', {'show_no_quote_error': show_no_quote_error, 'show_sanction_confirmation': show_sanction_confirmation, 'show_secret_notes': show_secret_notes, 'show_apply_discount': show_apply_discount, 'quotes': quotes, 'selected_quote_ids': selected_quote_ids})

@login_required
def purchase_orders(request):
    return render(request, 'purchase_orders.html')

@login_required
def associates(request):
    sales_associates = SalesAssociate.objects.select_related('user').order_by('user__username')
    return render(request, 'associates.html', {'sales_associates': sales_associates})
