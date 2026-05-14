import frappe


def after_install():
    add_custom_fields()
    frappe.clear_cache()
    print("✅ JV Tax Custom Fields created successfully!")


def add_custom_fields():
    # Fields for Journal Entry
    je_fields = [
        {
            "fieldname": "custom_tax_template",
            "label": "Tax Template",
            "fieldtype": "Link",
            "options": "Purchase Taxes and Charges Template",
            "insert_after": "tax_withholding_category",
        },
        {
            "fieldname": "custom_total_taxes_and_charges",
            "label": "Total Taxes and Charges",
            "fieldtype": "Currency",
            "insert_after": "total_amount",
            "read_only": 1,
        },
    ]

    # Child Table Fields for Journal Entry Account
    jea_fields = [
        {
            "fieldname": "custom_tax_included",
            "label": "Tax Included",
            "fieldtype": "Check",
            "insert_after": "debit",
        },
        {
            "fieldname": "custom_is_tax_row",
            "label": "Is Tax Row",
            "fieldtype": "Check",
            "hidden": 1,
            "insert_after": "custom_tax_included",
        },
        {
            "fieldname": "custom_gross_amount",
            "label": "Gross Amount",
            "fieldtype": "Currency",
            "hidden": 1,
            "insert_after": "custom_is_tax_row",
        },
    ]

    create_custom_fields("Journal Entry", je_fields)
    create_custom_fields("Journal Entry Account", jea_fields)


def create_custom_fields(doctype, fields):
    for field in fields:
        # Check if field exists
        if not frappe.db.exists(
            "Custom Field", {"dt": doctype, "fieldname": field["fieldname"]}
        ):
            custom_field = frappe.get_doc(
                {"doctype": "Custom Field", "dt": doctype, **field}
            )
            custom_field.insert(ignore_permissions=True)
            print(f"Created field: {doctype} -> {field['fieldname']}")
