

from django.contrib.auth import authenticate, login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST
from django.views.generic import ListView

from .models import Quote


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
    return render(request, 'sanction_interface.html')

@login_required
def purchase_orders(request):
    return render(request, 'purchase_orders.html')

@login_required
def associates(request):
    return render(request, 'associates.html')

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
