import frappe
from frappe import _
from frappe.utils import flt
from erpnext.accounts.doctype.journal_entry.journal_entry import JournalEntry


class CustomJournalEntry(JournalEntry):
    """
    KEY FIX: Always derive tax from custom_gross_amount, never from
    the current debit/credit value (which may already be reduced).
    Uses custom_is_tax_row (DB field) to identify injected rows reliably
    across page reloads — unlike the previous user_remark prefix approach.
    """

    def before_save(self):
        self.apply_custom_taxes()
        # super().before_save()

    def validate(self):
        self.apply_custom_taxes()
        super().validate()

    def apply_custom_taxes(self):
        if not self.custom_tax_template:
            self._restore_gross_amounts()
            self.custom_total_taxes_and_charges = 0
            return

        tax_rows = self._get_tax_template_rows()
        if not tax_rows:
            return

        # Step 1 — Remove previously injected tax rows
        self.accounts = [row for row in self.accounts if not row.custom_is_tax_row]

        # Step 2 — Identify base rows
        base_rows = [row for row in self.accounts if row.custom_tax_included]

        if not base_rows:
            self.custom_total_taxes_and_charges = 0
            return

        total_tax = 0.0
        new_rows = []

        for row in base_rows:
            # Use gross amount as stable base for tax calculation, not current debit/credit
            # If custom_gross_amount was never set, snapshot it from current debit
            gross = flt(row.custom_gross_amount)
            if not gross:
                gross = flt(row.debit_in_account_currency) or flt(
                    row.credit_in_account_currency
                )
                row.custom_gross_amount = gross  # persist the snapshot

            if not gross:
                continue

            total_rate = sum(
                flt(t.get("rate")) for t in tax_rows if t.get("account_head")
            )
            if total_rate:
                net = flt(gross / (1 + total_rate / 100), 2)
            else:
                net = gross

            row_tax_total = 0.0
            valid_tax_rows = [
                t for t in tax_rows if flt(t.get("rate")) and t.get("account_head")
            ]

            for i, tax in enumerate(valid_tax_rows):
                rate = flt(tax["rate"])

                if i == len(valid_tax_rows) - 1:
                    # For the last tax row, we adjust to avoid rounding drift
                    tax_amount = flt(gross - net - row_tax_total, 2)
                else:
                    tax_amount = flt(net * rate / 100, 2)

                if not tax_amount:
                    continue

                row_tax_total += tax_amount
                total_tax += tax_amount

                new_rows.append(
                    {
                        "account": tax["account_head"],
                        "debit_in_account_currency": tax_amount,
                        "debit": tax_amount,
                        "credit_in_account_currency": 0,
                        "credit": 0,
                        "custom_is_tax_row": 1,
                        "custom_tax_included": 0,
                        "custom_gross_amount": 0,
                        "user_remark": (
                            f"{tax.get('description') or tax['account_head']} @ {rate}%"
                        ),
                    }
                )

            # ── Reduce base row: net = gross − tax ───────────────────────
            # net is already calculated above as gross / (1 + total_rate / 100)

            if flt(row.debit_in_account_currency) or flt(row.debit):
                row.debit_in_account_currency = net
                row.debit = net
            else:
                row.credit_in_account_currency = net
                row.credit = net

        # Step 3 — Append tax rows
        for row_data in new_rows:
            self.append("accounts", row_data)

        self.custom_total_taxes_and_charges = flt(total_tax, 2)

    def _get_tax_template_rows(self):
        try:
            template = frappe.get_doc(
                "Purchase Taxes and Charges Template", self.custom_tax_template
            )
            return [
                {
                    "account_head": t.account_head,
                    "rate": t.rate,
                    "description": t.description,
                }
                for t in template.taxes
            ]
        except frappe.DoesNotExistError:
            frappe.throw(
                _("Tax Template {0} not found.").format(self.custom_tax_template)
            )

    def _restore_gross_amounts(self):
        """Restore base rows to gross when template is removed."""
        for row in self.accounts:
            if row.custom_tax_included and flt(row.custom_gross_amount):
                gross = flt(row.custom_gross_amount)
                if flt(row.debit_in_account_currency) or flt(row.debit):
                    row.debit_in_account_currency = gross
                    row.debit = gross
                else:
                    row.credit_in_account_currency = gross
                    row.credit = gross
                row.custom_gross_amount = 0


@frappe.whitelist()
def get_tax_details(tax_template):
    if not tax_template:
        return []
    template = frappe.get_doc("Purchase Taxes and Charges Template", tax_template)
    return [
        {
            "account_head": t.account_head,
            "rate": t.rate,
            "description": t.description or t.account_head,
        }
        for t in template.taxes
    ]
