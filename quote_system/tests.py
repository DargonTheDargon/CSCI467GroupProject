from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from .models import Customer, Quote, SalesAssociate


class SanctionInterfaceSelectionTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username="associate", password="test-password")
        associate = SalesAssociate.objects.create(user=user)
        customer = Customer.objects.create(name="Test Customer", email="test@example.com", address="Test address")
        self.quote = Quote.objects.create(sales_associate=associate, customer=customer, status=Quote.Status.FINALIZED, final_price="125.00")
        self.client.force_login(user)

    def select_quote(self, quote_id=None):
        session = self.client.session
        if quote_id is None:
            session.pop("sanction_interface_selected_quote_id", None)
        else:
            session["sanction_interface_selected_quote_id"] = quote_id
        session.save()

    def test_action_without_selected_quote_shows_error(self):
        response = self.client.post(reverse("sanction_interface"), {"action": "sanction"})

        self.assertContains(response, "Error: No Quote Selected")

    def test_action_with_selected_quote_hides_error_and_keeps_selection(self):
        self.select_quote(self.quote.pk)
        response = self.client.post(reverse("sanction_interface"), {"action": "sanction"})

        self.assertNotContains(response, "Error: No Quote Selected")
        self.assertContains(response, f'value="{self.quote.pk}"')

    def test_quotes_are_rendered_as_single_selection_toggle_buttons(self):
        second_customer = Customer.objects.create(name="Second Customer", email="second@example.com", address="Second address")
        Quote.objects.create(sales_associate=self.quote.sales_associate, customer=second_customer, status=Quote.Status.FINALIZED, final_price="50.00")

        response = self.client.get(reverse("sanction_interface"))
        page = response.content.decode()

        self.assertEqual(page.count('class="sanction-quote"'), 2)
        self.assertEqual(page.count('value="toggle_quote"'), 2)
        self.assertIn(f'<form id="quote-{self.quote.pk}"', page)
        self.assertNotIn(f'<button id="quote-{self.quote.pk}"', page)

    def test_clicking_quote_selects_it_and_clicking_again_unselects_it(self):
        url = reverse("sanction_interface")

        response = self.client.post(url, {"action": "toggle_quote", "quote_id": self.quote.pk})
        self.assertRedirects(response, f"{url}#quote-{self.quote.pk}")
        self.assertContains(self.client.get(url), 'aria-pressed="true"')

        response = self.client.post(url, {"action": "toggle_quote", "quote_id": self.quote.pk})
        self.assertRedirects(response, f"{url}#quote-{self.quote.pk}")
        self.assertContains(self.client.get(url), 'aria-pressed="false"')

    def test_selecting_another_quote_switches_selection(self):
        second_customer = Customer.objects.create(name="Second Customer", email="second@example.com", address="Second address")
        second_quote = Quote.objects.create(sales_associate=self.quote.sales_associate, customer=second_customer, status=Quote.Status.FINALIZED, final_price="50.00")
        url = reverse("sanction_interface")

        self.client.post(url, {"action": "toggle_quote", "quote_id": self.quote.pk})
        self.client.post(url, {"action": "toggle_quote", "quote_id": second_quote.pk})

        page = self.client.get(url).content.decode()
        self.assertRegex(page, rf'value="{self.quote.pk}"[\s\S]*?aria-pressed="false"')
        self.assertRegex(page, rf'value="{second_quote.pk}"[\s\S]*?aria-pressed="true"')

    def test_sanction_action_shows_confirmation_without_changing_status(self):
        self.select_quote(self.quote.pk)
        response = self.client.post(reverse("sanction_interface"), {"action": "sanction"})

        self.assertContains(response, "Are you sure you want to Sanction this quote?")
        self.quote.refresh_from_db()
        self.assertEqual(self.quote.status, Quote.Status.FINALIZED)

    def test_confirm_sanction_updates_selected_quote(self):
        self.select_quote(self.quote.pk)
        response = self.client.post(reverse("sanction_interface"), {"action": "confirm_sanction"})

        self.quote.refresh_from_db()
        self.assertEqual(self.quote.status, Quote.Status.SANCTIONED)
        self.assertNotContains(response, "Are you sure you want to Sanction this quote?")

    def test_cancel_sanction_closes_confirmation_without_changing_status(self):
        self.select_quote(self.quote.pk)
        response = self.client.post(reverse("sanction_interface"), {"action": "cancel_sanction"})

        self.quote.refresh_from_db()
        self.assertEqual(self.quote.status, Quote.Status.FINALIZED)
        self.assertNotContains(response, "Are you sure you want to Sanction this quote?")

    def test_secret_notes_action_shows_view_and_add_popup(self):
        self.select_quote(self.quote.pk)
        response = self.client.post(reverse("sanction_interface"), {"action": "secret_notes"})

        self.assertContains(response, "secret-notes-modal-title")
        self.assertContains(response, "View")
        self.assertContains(response, "Add")

    def test_secret_notes_action_without_selection_shows_error(self):
        response = self.client.post(reverse("sanction_interface"), {"action": "secret_notes"})

        self.assertContains(response, "Error: No Quote Selected")
        self.assertNotContains(response, "secret-notes-modal-title")

    def test_clicking_secret_notes_backdrop_closes_popup(self):
        self.select_quote(self.quote.pk)
        response = self.client.post(reverse("sanction_interface"), {"action": "close_secret_notes"})

        self.assertNotContains(response, "secret-notes-modal-title")
        self.assertContains(response, f'value="{self.quote.pk}"')

    def test_apply_discount_action_shows_percent_and_amount_popup(self):
        self.select_quote(self.quote.pk)
        response = self.client.post(reverse("sanction_interface"), {"action": "apply_discount"})

        self.assertContains(response, "apply-discount-modal-title")
        self.assertContains(response, "Percent")
        self.assertContains(response, "Amount")

    def test_apply_discount_action_without_selection_shows_error(self):
        response = self.client.post(reverse("sanction_interface"), {"action": "apply_discount"})

        self.assertContains(response, "Error: No Quote Selected")
        self.assertNotContains(response, "apply-discount-modal-title")

    def test_clicking_apply_discount_backdrop_closes_popup(self):
        self.select_quote(self.quote.pk)
        response = self.client.post(reverse("sanction_interface"), {"action": "close_apply_discount"})

        self.assertNotContains(response, "apply-discount-modal-title")
        self.assertContains(response, f'value="{self.quote.pk}"')
