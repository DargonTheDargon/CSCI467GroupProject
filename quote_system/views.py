from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.template import loader


@login_required
def interface1(request):
    template = loader.get_template("quote_system/interface1.html")
    return HttpResponse(template.render({},request))