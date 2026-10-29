from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

# Create your models here.



class User(AbstractUser):
    pass

class Customer(models.Model):
    name = models.CharField(max_length=200)
    email = models.CharField(max_length=200)
    address = models.CharField(max_length=200)

class SalesAssociate(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    accumulated_commission = models.DecimalField()
    commission_rate = models.DecimalField()
class Quote(models.Model):
    sales_associate = models.ForeignKey(SalesAssociate, on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    status = models.CharField(max_length=200)
    discount_type = models.Choices("percent","flat")
    final_price = models.DecimalField()

class PurchaseOrder(models.Model):
    quote = models.ForeignKey(Quote, on_delete=models.CASCADE)
    final_discount = models.DecimalField()
    final_price = models.DecimalField()
    processing_date = models.DateTimeField()
    commission_rate = models.ForeignKey(SalesAssociate, on_delete=models.CASCADE)
    commission_amount = models.DecimalField()
    def process_date(self):
        return self.processing_date == timezone.now()
    
class LineItem(models.Model):
    quote = models.ForeignKey(Quote, on_delete=models.CASCADE)
    description = models.CharField(max_length=200)
    price = models.DecimalField()

class SecretNote(models.Model):
    quote = models.ForeignKey(Quote, on_delete=models.CASCADE)
    text = models.CharField(max_length=200)
    note_date = models.DateTimeField("Note Added On")
    def noteDate(self):
        return self.note_date == timezone.now()