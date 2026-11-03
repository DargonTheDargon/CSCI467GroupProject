from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    class Role(models.TextChoices):
        SALES_ASSOCIATE = "sales_associate", "Sales Associate"
        HQ_EMPLOYEE = "hq_employee", "HQ Employee"
        ADMIN = "admin", "Admin"

    role = models.CharField(
        max_length=32, choices=Role.choices, default=Role.SALES_ASSOCIATE
    )


class SalesAssociate(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    accumulated_commission = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    commission_rate = models.DecimalField(max_digits=5, decimal_places=4, default=0)

    def __str__(self):
        return str(self.user)


class Customer(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField()
    address = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class Quote(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        FINALIZED = "finalized", "Finalized"
        SANCTIONED = "sanctioned", "Sanctioned"
        ORDERED = "ordered", "Ordered"

    class DiscountType(models.TextChoices):
        PERCENT = "percent", "Percent"
        FLAT = "flat", "Flat"

    sales_associate = models.ForeignKey(
        SalesAssociate, on_delete=models.PROTECT, related_name="quotes"
    )  # sales_associate.quote_set -> sales_associate.quotes
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT)
    status = models.CharField(max_length=32, choices=Status, default=Status.DRAFT)
    discount_type = models.CharField(choices=DiscountType, default=DiscountType.FLAT)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    final_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"Quote #{self}"


class PurchaseOrder(models.Model):
    quote = models.OneToOneField(Quote, on_delete=models.CASCADE, primary_key=True)
    discount_type = models.CharField(
        choices=Quote.DiscountType, default=Quote.DiscountType.FLAT
    )
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    final_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    # The time a quote was converted to a purchase order
    processing_date = models.DateTimeField(default=timezone.now)
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"PO #{self}"


class LineItem(models.Model):
    quote = models.ForeignKey(
        Quote, on_delete=models.CASCADE, related_name="line_items"
    )
    description = models.CharField(max_length=200)
    price = models.DecimalField()

    def __str__(self):
        return self.description


class Note(models.Model):
    quote = models.ForeignKey(Quote, on_delete=models.CASCADE, related_name="notes")
    text = models.TextField(max_length=200)
    date_added = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.text
