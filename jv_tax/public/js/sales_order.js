frappe.ui.form.on("Sales Order", {
	// refresh: function (frm) {
	// 	if (frm.doc.docstatus === 1) {
	// 		// Remove the standard broken button slightly delayed to ensure it loaded
	// 		setTimeout(() => {
	// 			frm.remove_custom_button("Update Items");
	// 		}, 500);
	// 		// Add our fixed custom button
	// 		frm.add_custom_button(__("Update Items (Fixed)"), function () {
	// 			open_custom_update_dialog(frm);
	// 		});
	// 	}
	// },
});

function open_custom_update_dialog(frm) {
	let dialog = new frappe.ui.Dialog({
		title: __("Update or Add Items"),
		fields: [
			{
				fieldname: "items",
				fieldtype: "Table",
				label: __("Items"),
				data: frm.doc.items.map((i) => ({
					name: i.name,
					item_code: i.item_code,
					qty: i.qty,
					rate: i.rate,
					uom: i.uom,
				})),
				get_data: () => {
					return frm.doc.items;
				},
				fields: [
					{ fieldtype: "Data", fieldname: "name", hidden: 1 },
					{
						fieldtype: "Link",
						fieldname: "item_code",
						options: "Item",
						label: "Item Code",
						in_list_view: 1,
						reqd: 1,
					},
					{
						fieldtype: "Float",
						fieldname: "qty",
						label: "Qty",
						in_list_view: 1,
						reqd: 1,
					},
					{
						fieldtype: "Float",
						fieldname: "rate",
						label: "Rate",
						in_list_view: 1,
						reqd: 1,
					},
					{
						fieldtype: "Link",
						fieldname: "uom",
						options: "UOM",
						label: "UOM",
						in_list_view: 1,
						read_only: 1,
						fetch_from: "item_code.stock_uom",
						onchange: function () {
							frappe.call({
								method: "erpnext.stock.get_item_details.get_item_details",
								args: {
									args: {
										item_code: this.item_code,
										company: frm.doc.company,
										customer: frm.doc.customer,
										currency: frm.doc.currency,
										conversion_rate: frm.doc.conversion_rate,
										price_list: frm.doc.selling_price_list,
										doctype: "Sales Order",
										name: frm.doc.name,
										transaction_date: frm.doc.transaction_date,
										qty: 1,
									},
								},
								callback: function (r) {
									if (r.message) {
										this.rate =
											r.message.price_list_rate || r.message.standard_rate || 0;
										this.uom = r.message.stock_uom;
										this.qty = 1;
										this.refresh();
									}
								},
							});
						},
					},
				],
			},
		],
		primary_action_label: __("Update"),
		primary_action: function (values) {
			frappe.call({
				method: "jv_tax.overrides.api.update_so_items",
				args: {
					docname: frm.doc.name,
					items: values.items,
				},
				freeze: true,
				freeze_message: __("Updating Sales Order..."),
				callback: function (r) {
					if (!r.exc) {
						frm.reload_doc();
						dialog.hide();
						frappe.show_alert({
							message: __("Items Updated Successfully"),
							indicator: "green",
						});
					}
				},
			});
		},
	});

	// The Missing Trigger: Fetch Rate and UOM when Item Code changes
	dialog.$wrapper.on("change", 'input[data-fieldname="item_code"]', function () {
		let $input = $(this);
		let row_name = $input.closest(".grid-row").attr("data-name");
		let grid_row = dialog.fields_dict.items.grid.get_row(row_name);
		let item_code = grid_row.doc.item_code;

		if (item_code) {
			frappe.call({
				method: "erpnext.stock.get_item_details.get_item_details",
				args: {
					args: {
						item_code: item_code,
						company: frm.doc.company,
						customer: frm.doc.customer,
						currency: frm.doc.currency,
						conversion_rate: frm.doc.conversion_rate,
						price_list: frm.doc.selling_price_list,
						doctype: "Sales Order",
						name: frm.doc.name,
						transaction_date: frm.doc.transaction_date,
						qty: 1,
					},
				},
				callback: function (r) {
					if (r.message) {
						// Apply fetched data to the dialog grid
						grid_row.doc.rate =
							r.message.price_list_rate || r.message.standard_rate || 0;
						grid_row.doc.uom = r.message.stock_uom || r.message.sales_uom;
						grid_row.doc.qty = 1;
						grid_row.refresh();
					}
				},
			});
		}
	});

	dialog.show();
}
