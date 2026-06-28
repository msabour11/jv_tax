import frappe

logger = frappe.logger("doc_events", allow_site=True)


# def set_profit_on_update_after_submit(doc, method):
#     # Server Script: Before Save on Sales Order

#     total_cost = 0.0

#     for item in doc.items:
#         is_stock_item = frappe.db.get_value("Item", item.item_code, "is_stock_item")
#         if not is_stock_item:
#             continue

#         qty = item.get("qty")
#         if not qty:
#             qty = 0

#         valuation_rate = item.get("valuation_rate")
#         if not valuation_rate:
#             valuation_rate = frappe.db.get_value("Item", item.item_code, "last_purchase_rate")
#             item.valuation_rate = valuation_rate

#         item_cost = valuation_rate

#         if not item_cost:
#             item_price = frappe.db.get_value(
#                 "Item Price",
#                 {"item_code": item.item_code, "price_list": "شراء القياسية"},
#                 "price_list_rate",
#             )
#             if item_price:
#                 item_cost = item_price
#             else:
#                 item_cost = 0
#         # calculate line cost

#         line_cost = float(qty) * float(item_cost)

#         total_cost = float(total_cost) + float(line_cost)

#     # Retrieve base_net_total from the document; if not set, default to 0
#     base_net_total = doc.get("base_net_total")
#     if not base_net_total:
#         base_net_total = 0

#     profit = float(base_net_total) - float(total_cost)

#     if float(base_net_total) > 0:
#         custom_profit_percentage = (profit / float(total_cost)) * 100
#     else:
#         custom_profit_percentage = 0

#     doc.db_set("custom_profit_percentage", custom_profit_percentage)
#     # Logging to file: sites/{site}/logs/doc_events.log
#     logger.warning(
#         f"Sales Order {doc.name}: Profit={profit}, Percentage={custom_profit_percentage}%"
#     )


############################### refacor
def set_profit_on_update_after_submit(doc, method):
    total_cost = 0.0

    for item in doc.items:
        is_stock_item = frappe.db.get_value("Item", item.item_code, "is_stock_item")
        if not is_stock_item:
            continue

        qty = float(item.get("qty") or 0)
        valuation_rate = float(item.get("valuation_rate") or 0)

        # 1: Last Purchase Rate
        if not valuation_rate:
            valuation_rate = float(
                frappe.db.get_value("Item", item.item_code, "last_purchase_rate") or 0
            )
            item.valuation_rate = valuation_rate  # Sets it in memory for the doc save
            frappe.db.set_value(
                "Sales Order Item", item.name, "valuation_rate", valuation_rate
            )

        # 2: Standard Purchase Price List
        if not valuation_rate:
            item_price = frappe.db.get_value(
                "Item Price",
                {"item_code": item.item_code, "price_list": "شراء القياسية"},
                "price_list_rate",
            )
            valuation_rate = float(item_price or 0)

        # Calculate line cost and accumulate
        line_cost = qty * valuation_rate
        total_cost += line_cost

    base_net_total = float(doc.get("base_net_total") or 0)
    profit = base_net_total - total_cost

    # Safe division check against total_cost, not base_net_total
    if total_cost > 0:
        custom_profit_percentage = (profit / total_cost) * 100
    else:
        custom_profit_percentage = 0.0

    doc.custom_profit_percentage = custom_profit_percentage

    doc.db_set("custom_profit_percentage", custom_profit_percentage)

    # Logging to sites/{site}/logs/frappe.log
    frappe.logger("sales_order_profit").warning(
        f"Sales Order {doc.name}: Profit={profit}, Percentage={custom_profit_percentage}%"
    )
