frappe.ui.form.on("Journal Entry", {
	custom_tax_template: function (frm) {
		calculate_and_apply_taxes(frm);
	},

	// validate: function (frm) {
	// 	if (frm.doc.custom_tax_template) {
	// 		calculate_and_apply_taxes(frm);
	// 	}
	// },
});

frappe.ui.form.on("Journal Entry Account", {
	custom_tax_included: function (frm, cdt, cdn) {
		let row = locals[cdt][cdn];

		if (row.custom_tax_included) {
			// Snapshot the gross amount NOW before any reduction happens
			// Only snapshot if not already snapshotted (gross_amount = 0 means not set yet)
			if (!row.custom_gross_amount) {
				let current_amount =
					flt(row.debit_in_account_currency) || flt(row.credit_in_account_currency);
				frappe.model.set_value(cdt, cdn, "custom_gross_amount", current_amount);
			}
		} else {
			// Restore original gross amount when unchecked
			if (row.custom_gross_amount) {
				if (row.debit_in_account_currency || row.debit) {
					frappe.model.set_value(
						cdt,
						cdn,
						"debit_in_account_currency",
						row.custom_gross_amount,
					);
					frappe.model.set_value(cdt, cdn, "debit", row.custom_gross_amount);
				} else {
					frappe.model.set_value(
						cdt,
						cdn,
						"credit_in_account_currency",
						row.custom_gross_amount,
					);
					frappe.model.set_value(cdt, cdn, "credit", row.custom_gross_amount);
				}
				frappe.model.set_value(cdt, cdn, "custom_gross_amount", 0);
			}
			// Remove tax rows and recalculate
			if (frm.doc.custom_tax_template) {
				calculate_and_apply_taxes(frm);
			}
			return;
		}

		if (frm.doc.custom_tax_template) {
			calculate_and_apply_taxes(frm);
		}
	},

	debit_in_account_currency: function (frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.custom_tax_included && !row.custom_is_tax_row) {
			// User manually changed the amount — re-snapshot gross
			frappe.model.set_value(
				cdt,
				cdn,
				"custom_gross_amount",
				flt(row.debit_in_account_currency),
			);
			if (frm.doc.custom_tax_template) {
				calculate_and_apply_taxes(frm);
			}
		}
	},

	credit_in_account_currency: function (frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.custom_tax_included && !row.custom_is_tax_row) {
			frappe.model.set_value(
				cdt,
				cdn,
				"custom_gross_amount",
				flt(row.credit_in_account_currency),
			);
			if (frm.doc.custom_tax_template) {
				calculate_and_apply_taxes(frm);
			}
		}
	},

	accounts_remove: function (frm) {
		if (frm.doc.custom_tax_template) {
			calculate_and_apply_taxes(frm);
		}
	},
});

/**
 * Main calculation function.
 *
 * KEY DESIGN DECISIONS:
 * 1. Always use custom_gross_amount (not current debit) as the tax base
 *    → prevents compounding reduction on each save
 * 2. Identify injected tax rows via custom_is_tax_row = 1
 *    → survives page reload unlike in-memory flags
 * 3. Set debit = gross - tax on the base row
 *    → reduction happens exactly once, derived from gross
 */
function calculate_and_apply_taxes(frm) {
	if (!frm.doc.custom_tax_template) {
		// No template: restore all base rows to their gross amounts
		_restore_all_gross_amounts(frm);
		frm.set_value("custom_total_taxes_and_charges", 0);
		return;
	}

	frappe.call({
		method: "frappe.client.get",
		args: {
			doctype: "Purchase Taxes and Charges Template",
			name: frm.doc.custom_tax_template,
		},
		callback: function (r) {
			if (!r.message || !r.message.taxes || !r.message.taxes.length) {
				frappe.msgprint(
					__("No tax lines found in template: {0}", [frm.doc.custom_tax_template]),
				);
				return;
			}

			let tax_template_rows = r.message.taxes;

			// ── Step 1: Remove existing injected tax rows ─────────────────
			frm.doc.accounts = (frm.doc.accounts || []).filter((row) => !row.custom_is_tax_row);

			// ── Step 2: Identify base rows (custom_tax_included = 1) ──────
			let base_rows = frm.doc.accounts.filter((row) => row.custom_tax_included);

			if (!base_rows.length) {
				frm.set_value("custom_total_taxes_and_charges", 0);
				frm.refresh_field("accounts");
				return;
			}

			// ── Step 3: Calculate and apply ───────────────────────────────
			let total_tax = 0;
			let new_tax_rows = [];

			base_rows.forEach(function (base_row) {
				// ALWAYS use gross amount as the base — never the current debit
				// If custom_gross_amount not set yet, treat current amount as gross
				let gross = flt(base_row.custom_gross_amount);
				if (!gross) {
					gross =
						flt(base_row.debit_in_account_currency) ||
						flt(base_row.credit_in_account_currency);
					// Auto-save the gross so future recalculations are stable
					base_row.custom_gross_amount = gross;
				}

				if (!gross) return;

				let total_rate = 0;
				tax_template_rows.forEach(function (tax) {
					if (tax.account_head) {
						total_rate += flt(tax.rate);
					}
				});

				let net = gross;
				if (total_rate) {
					net = flt(gross / (1 + total_rate / 100), 2);
				}

				let row_tax_total = 0;
				let valid_tax_rows = tax_template_rows.filter(
					(t) => flt(t.rate) && t.account_head,
				);

				valid_tax_rows.forEach(function (tax, i) {
					let rate = flt(tax.rate);

					let tax_amount = 0;
					if (i === valid_tax_rows.length - 1) {
						tax_amount = flt(gross - net - row_tax_total, 2);
					} else {
						tax_amount = flt((net * rate) / 100, 2);
					}

					if (!tax_amount) return;

					row_tax_total += tax_amount;
					total_tax += tax_amount;

					new_tax_rows.push({
						account: tax.account_head,
						debit_in_account_currency: tax_amount,
						debit: tax_amount,
						credit_in_account_currency: 0,
						credit: 0,
						custom_is_tax_row: 1, // ← DB-persisted flag
						custom_tax_included: 0,
						custom_gross_amount: 0,
						user_remark: `__jv_tax__ ${tax.description || tax.account_head} @ ${rate}%`,
					});
				});

				// Reduce base row: net = gross - tax (which is exactly 'net' as calculated above)
				if (base_row.debit_in_account_currency || base_row.debit) {
					base_row.debit_in_account_currency = net;
					base_row.debit = net;
				} else {
					base_row.credit_in_account_currency = net;
					base_row.credit = net;
				}
			});

			// ── Step 4: Append tax rows ───────────────────────────────────
			new_tax_rows.forEach(function (entry) {
				let new_row = frm.add_child("accounts");
				$.extend(new_row, entry);
			});

			// ── Step 5: Update summary and refresh ────────────────────────
			frm.set_value("custom_total_taxes_and_charges", flt(total_tax, 2));
			frm.refresh_field("accounts");
			frm.refresh_field("custom_total_taxes_and_charges");
		},
	});
}

function _restore_all_gross_amounts(frm) {
	(frm.doc.accounts || []).forEach(function (row) {
		if (row.custom_tax_included && row.custom_gross_amount) {
			if (row.debit_in_account_currency || row.debit) {
				row.debit_in_account_currency = row.custom_gross_amount;
				row.debit = row.custom_gross_amount;
			} else {
				row.credit_in_account_currency = row.custom_gross_amount;
				row.credit = row.custom_gross_amount;
			}
			row.custom_gross_amount = 0;
		}
	});
	// Remove injected tax rows
	frm.doc.accounts = (frm.doc.accounts || []).filter((row) => !row.custom_is_tax_row);
	frm.refresh_field("accounts");
}
