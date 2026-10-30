from django.db import models

class Customer(models.Model):
    customer_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200)
    address = models.CharField(max_length=200)
    email = models.CharField(max_length=200)

    class Meta:
        db_table = 'customer'

    def __str__(self):
        return self.name

class User(models.Model):
    user_id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=200, unique=True)
    password = models.CharField(max_length=200)
    class Role(models.TextChoices):
        SALES_ASSOCIATE = 'sales_associate', 'Sales Associate'
        ADMIN = 'admin', 'Admin'

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.SALES_ASSOCIATE)

    class Meta:
        db_table = 'user'

    def __str__(self):
            return self.username
    
class SalesAssociate(models.Model):
    # Extra data for users whose role is SALES_ASSOCIATE
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True,
    )
    name = models.CharField(max_length=200)
    accumulated_commission = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    # Commission rate is stored as a decimal, e.g. 5.00 for 5%
    class Meta:
        db_table = 'sales_associate'

    def __str__(self):
        return self.name

class Quote(models.Model):
    quote_id = models.AutoField(primary_key=True)
    sales_associate = models.ForeignKey(SalesAssociate, on_delete=models.PROTECT, related_name='quotes')
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='quotes')
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        FINALIZED = 'finalized', 'Finalized'
        SANCTIONED = 'sanctioned', 'Sanctioned'
        ORDERED = 'ordered', 'Ordered'

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    class DiscountType(models.TextChoices):
        PERCENTAGE = 'percentage', 'Percentage'
        AMOUNT = 'amount', 'Amount'

    discount_type = models.CharField(max_length=20, choices=DiscountType.choices, default=DiscountType.PERCENTAGE)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    final_price = models.DecimalField(max_digits=10, decimal_places=2)
    date_finalized = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'quote'

    def __str__(self):
        return f'Quote #{self.quote_id}'

class LineItem(models.Model):
    line_item_id = models.AutoField(primary_key=True)
    quote = models.ForeignKey(Quote, on_delete=models.CASCADE, related_name='line_items')
    description = models.CharField(max_length=500)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = 'line_item'

    def __str__(self):
        return self.description

class SecretNote(models.Model):
    note_id = models.AutoField(primary_key=True)
    quote = models.ForeignKey(Quote, on_delete=models.CASCADE, related_name='secret_notes')
    note_text = models.TextField(max_length=500)
    date_added = models.DateField(auto_now_add=True)

    class Meta:
        db_table = 'secret_note'

    def __str__(self):
        return self.note_text

class PurchaseOrder(models.Model):
    po_id = models.AutoField(primary_key=True)
    quote = models.OneToOneField(Quote, on_delete=models.PROTECT, related_name='purchase_order')
    discount_type = models.CharField(max_length=20, choices=Quote.DiscountType.choices, default=Quote.DiscountType.PERCENTAGE)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    processing_date = models.DateField(auto_now_add=True)
    final_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'purchase_order'

    def __str__(self):
        return f'PO #{self.po_id}'
