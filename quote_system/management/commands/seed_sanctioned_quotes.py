"""Seed sample sales associates, customers, and sanctioned quotes for development.

Usage: python manage.py seed_sanctioned_quotes

Safe to run more than once: associates and customers are reused, and a quote
is only created if that customer does not already have a seeded quote.
"""
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from quote_system.models import Customer, LineItem, Note, Quote, SalesAssociate, User

DEFAULT_PASSWORD = "password123"

ASSOCIATES = [
    # username, first, last, email, commission rate (%)
    ("jsmith", "Jane", "Smith", "jane.smith@example.com", "5.00"),
    ("mlopez", "Marco", "Lopez", "marco.lopez@example.com", "7.50"),
    ("akim", "Alice", "Kim", "alice.kim@example.com", "6.25"),
]

CUSTOMERS = [
    # name, email, address
    ("Greenfield Power Plant", "orders@greenfieldpower.example.com", "1200 Industrial Pkwy, DeKalb, IL 60115"),
    ("Riverside Water Treatment", "maint@riversidewater.example.com", "45 River Rd, Sycamore, IL 60178"),
    ("Midwest Steel Works", "purchasing@midweststeel.example.com", "880 Foundry Ave, Rockford, IL 61101"),
    ("Prairie Chemical Co.", "ops@prairiechem.example.com", "17 Commerce Dr, Aurora, IL 60504"),
    ("Lakeside Paper Mill", "facilities@lakesidepaper.example.com", "300 Mill St, Elgin, IL 60120"),
    ("Northern Grain Processing", "service@northerngrain.example.com", "52 Elevator Ln, Belvidere, IL 61008"),
]

QUOTES = [
    # customer index, associate index, discount type, discount amount, line items (desc, qty, price), notes
    (0, 0, Quote.DiscountType.PERCENT, "10", [
        ("Boiler feed pump rebuild", 1, "4850.00"),
        ("Replace pump seals", 4, "215.00"),
        ("Vibration analysis", 1, "650.00"),
    ], ["Customer is a repeat client; approved 10% loyalty discount."]),
    (1, 1, Quote.DiscountType.FLAT, "250", [
        ("Clarifier drive gearbox repair", 1, "3200.00"),
        ("Valve actuator replacement", 2, "780.00"),
    ], ["Plant manager wants work done before spring runoff."]),
    (2, 2, Quote.DiscountType.FLAT, "0", [
        ("Overhead crane hoist inspection", 1, "1150.00"),
        ("Hydraulic press cylinder reseal", 2, "1675.00"),
        ("Conveyor belt splice", 3, "420.00"),
    ], []),
    (3, 0, Quote.DiscountType.PERCENT, "5", [
        ("Heat exchanger tube cleaning", 1, "2900.00"),
        ("Pressure relief valve testing", 6, "135.00"),
    ], ["Competitor quoted ~8% lower; matched with 5% discount.", "Requires confined-space crew."]),
    (4, 1, Quote.DiscountType.FLAT, "500", [
        ("Paper machine dryer bearing replacement", 8, "395.00"),
        ("Steam trap survey", 1, "1800.00"),
        ("Motor rewind (75 HP)", 1, "3450.00"),
    ], ["Large order; extra $500 off approved by regional manager."]),
    (5, 2, Quote.DiscountType.PERCENT, "12.5", [
        ("Grain dryer burner service", 2, "960.00"),
        ("Bucket elevator chain replacement", 1, "5200.00"),
    ], []),
]


class Command(BaseCommand):
    help = "Create sample sales associates, customers, and sanctioned quotes."

    @transaction.atomic
    def handle(self, *args, **options):
        associates = []
        for username, first, last, email, rate in ASSOCIATES:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={"first_name": first, "last_name": last, "email": email,
                          "role": User.Role.SALES_ASSOCIATE},
            )
            if created:
                user.set_password(DEFAULT_PASSWORD)
                user.save()
            associate, _ = SalesAssociate.objects.get_or_create(
                user=user, defaults={"commission_rate": Decimal(rate)}
            )
            associates.append(associate)

        customers = [
            Customer.objects.get_or_create(name=name, defaults={"email": email, "address": address})[0]
            for name, email, address in CUSTOMERS
        ]

        created_count = 0
        for cust_i, assoc_i, discount_type, discount_amount, items, notes in QUOTES:
            customer = customers[cust_i]
            if Quote.objects.filter(customer=customer).exists():
                continue
            quote = Quote.objects.create(
                sales_associate=associates[assoc_i],
                customer=customer,
                status=Quote.Status.SANCTIONED,
                discount_type=discount_type,
                discount_amount=Decimal(discount_amount),
            )
            for description, quantity, price in items:
                LineItem.objects.create(quote=quote, description=description,
                                        quantity=quantity, price=Decimal(price))
            for text in notes:
                Note.objects.create(quote=quote, text=text)
            quote.final_price = quote.total_price()
            quote.save(update_fields=["final_price"])
            created_count += 1
            self.stdout.write(f"Created Quote #{quote.pk} for {customer.name}: ${quote.final_price}")

        self.stdout.write(self.style.SUCCESS(
            f"Done. {created_count} sanctioned quote(s) created. "
            f"Associate logins use password '{DEFAULT_PASSWORD}'."
        ))
