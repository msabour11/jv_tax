import frappe


def before_uninstall():
    """Runs ONCE when the app is uninstalled"""
    delete_custom_fields()
    frappe.clear_cache()
    print("🗑️ JV Tax Custom Fields removed successfully!")


def delete_custom_fields():
    """Delete custom fields to clean up the database"""
    fields_to_remove = {
        "Journal Entry": ["custom_tax_template", "custom_total_taxes_and_charges"],
        "Journal Entry Account": [
            "custom_tax_included",
            "custom_is_tax_row",
            "custom_gross_amount",
        ],
    }

    for doctype, fieldnames in fields_to_remove.items():
        for fieldname in fieldnames:
            if frappe.db.exists(
                "Custom Field", {"dt": doctype, "fieldname": fieldname}
            ):
                # Delete the custom field record
                frappe.db.delete(
                    "Custom Field", {"dt": doctype, "fieldname": fieldname}
                )
                print(f"Deleted field: {doctype} -> {fieldname}")
