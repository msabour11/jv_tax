import frappe

logger = frappe.logger("doc_events", allow_site=True)


def set_profit_on_update_after_submit(doc, method):
    # Server Script: Before Save on Sales Order

    total_cost = 0.0

    for item in doc.items:
        qty = item.get("qty")
        if not qty:
            qty = 0

        valuation_rate = item.get("valuation_rate")
        if not valuation_rate:
            valuation_rate = 0

        item_cost = valuation_rate

        if not item_cost:
            item_price = frappe.db.get_value(
                "Item Price",
                {"item_code": item.item_code, "price_list": "شراء القياسية"},
                "price_list_rate",
            )
            if item_price:
                item_cost = item_price
            else:
                item_cost = 0
        # calculate line cost

        line_cost = float(qty) * float(item_cost)

        total_cost = float(total_cost) + float(line_cost)

    # Retrieve base_net_total from the document; if not set, default to 0
    base_net_total = doc.get("base_net_total")
    if not base_net_total:
        base_net_total = 0

    profit = float(base_net_total) - float(total_cost)

    if float(base_net_total) > 0:
        custom_profit_percentage = (profit / float(base_net_total)) * 100
    else:
        custom_profit_percentage = 0

    doc.db_set("custom_profit_percentage", custom_profit_percentage)
    # Logging to file: sites/{site}/logs/doc_events.log
    logger.warning(
        f"Sales Order {doc.name}: Profit={profit}, Percentage={custom_profit_percentage}%"
    )

    print(custom_profit_percentage)
