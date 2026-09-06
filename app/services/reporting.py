from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

from sqlalchemy import func
from sqlalchemy.orm import joinedload

from app.models import Category, Product, Return, ReturnItem, Sale, SaleItem, StoreInventory
from app.services.product_inventory import (
    PRODUCT_VAT_MULTIPLIER,
    get_customer_gross_amount,
    round_signed_customer_price,
)
from app.utils import end_of_day, parse_iso_date, quantize_amount, start_of_day


ZERO = Decimal("0.00")


def round_report_money(value):
    return round_signed_customer_price(value)


def calculate_rate(numerator, denominator):
    numerator = Decimal(numerator or 0)
    denominator = Decimal(denominator or 0)
    if not denominator:
        return ZERO
    return quantize_amount((numerator / denominator) * Decimal("100"))


def sum_return_items_customer_gross(return_items):
    return quantize_amount(
        sum((get_return_customer_gross(item) for item in return_items), ZERO)
    )


def is_effectively_zero(value):
    return quantize_amount(value or 0) == ZERO


def get_return_quantity_direction(return_item):
    return -1 if Decimal(return_item.refund_amount or 0) > ZERO else 1


def get_return_revenue_delta(return_item):
    return quantize_amount(get_return_customer_gross(return_item) * Decimal("-1"))


def get_return_customer_gross(return_item):
    stored_gross = getattr(return_item, "gross_refund_amount", None)
    if stored_gross is not None:
        return quantize_amount(stored_gross)
    return get_customer_gross_amount(return_item.refund_amount)


def get_return_product_identity(return_item):
    product = return_item.product
    variant = (
        return_item.product_variant_snapshot
        if hasattr(return_item, "product_variant_snapshot")
        else product.variant
    )
    return (
        product.id,
        getattr(return_item, "product_name_snapshot", None) or product.name,
        variant,
    )


def get_return_cost_delta(return_item):
    direction = Decimal(get_return_quantity_direction(return_item))
    unit_cost = getattr(return_item, "unit_cost_snapshot", None)
    if unit_cost is None:
        unit_cost = return_item.product.purchase_price
    return quantize_amount(
        Decimal(unit_cost or 0)
        * Decimal(return_item.quantity or 0)
        * PRODUCT_VAT_MULTIPLIER
        * direction
    )


def consume_return_profiles(profiles, quantity):
    remaining = max(int(quantity or 0), 0)
    totals = {
        "quantity": 0,
        "gross": ZERO,
        "discount": ZERO,
        "net": ZERO,
        "cost": ZERO,
        "revenue": ZERO,
        "revenue_gross": ZERO,
    }

    while remaining and profiles:
        profile = profiles[0]
        take = min(remaining, profile["quantity"])
        factor = Decimal(take)
        totals["quantity"] += take
        for key in ["gross", "discount", "net", "cost", "revenue", "revenue_gross"]:
            if key in profile:
                totals[key] += quantize_amount(profile[key] * factor)

        profile["quantity"] -= take
        remaining -= take
        if profile["quantity"] <= 0:
            profiles.pop(0)

    return totals if totals["quantity"] else None


def build_profit_product_rows(sales, return_items=None):
    grouped_rows = {}
    return_profiles = {}

    def get_row(product, name=None, variant=None):
        name = name or product.name
        variant = product.variant if variant is None else variant
        key = (product.id, name, variant)
        return grouped_rows.setdefault(
            key,
            {
                "name": name,
                "variant": variant,
                "quantity": 0,
                "gross_revenue_raw": ZERO,
                "discount_amount_raw": ZERO,
                "net_revenue_raw": ZERO,
                "cost_raw": ZERO,
            },
        )

    for sale in sales:
        sale_items = list(sale.items)
        sale_base_net = quantize_amount(
            sum((item.unit_price * item.quantity for item in sale_items), ZERO)
        )
        sale_line_discount = quantize_amount(
            sum((item.discount_amount for item in sale_items), ZERO)
        )
        sale_total_discount = quantize_amount(sale.total_discount or 0)
        sale_footer_discount = quantize_amount(max(sale_total_discount - sale_line_discount, ZERO))
        sale_discountable_base = quantize_amount(max(sale_base_net - sale_line_discount, ZERO))
        sale_gross_before_discount = round_report_money(sale_base_net * PRODUCT_VAT_MULTIPLIER)
        sale_visible_discount = quantize_amount(
            max(sale_gross_before_discount - Decimal(sale.total_amount or 0), ZERO)
        )

        item_discount_weights = []
        for item in sale_items:
            item_base_net = quantize_amount(item.unit_price * item.quantity)
            item_line_discount = quantize_amount(item.discount_amount or 0)
            item_discountable_base = quantize_amount(max(item_base_net - item_line_discount, ZERO))
            footer_share = (
                quantize_amount(sale_footer_discount * item_discountable_base / sale_discountable_base)
                if sale_discountable_base
                else ZERO
            )
            item_discount_net = quantize_amount(item_line_discount + footer_share)
            item_discount_weights.append((item, item_base_net, item_discount_net))

        discount_weight_total = quantize_amount(
            sum((item_discount_net for _, _, item_discount_net in item_discount_weights), ZERO)
        )

        for item, item_base_net, item_discount_net in item_discount_weights:
            product = item.product
            item_name = getattr(item, "product_name_snapshot", None) or product.name
            item_variant = (
                item.product_variant_snapshot
                if hasattr(item, "product_variant_snapshot")
                else product.variant
            )
            row = get_row(product, item_name, item_variant)
            item_gross_revenue = quantize_amount(item_base_net * PRODUCT_VAT_MULTIPLIER)
            item_discount_gross = (
                quantize_amount(sale_visible_discount * item_discount_net / discount_weight_total)
                if discount_weight_total
                else ZERO
            )
            item_net_revenue = quantize_amount(max(item_gross_revenue - item_discount_gross, ZERO))
            unit_cost = getattr(item, "unit_cost_snapshot", None)
            if unit_cost is None:
                unit_cost = product.purchase_price
            item_cost = quantize_amount(Decimal(unit_cost or 0) * item.quantity * PRODUCT_VAT_MULTIPLIER)

            row["quantity"] += item.quantity
            row["gross_revenue_raw"] += item_gross_revenue
            row["discount_amount_raw"] += item_discount_gross
            row["net_revenue_raw"] += item_net_revenue
            row["cost_raw"] += item_cost
            if item.quantity > 0:
                key = (product.id, item_name, item_variant)
                return_profiles.setdefault(key, []).append(
                    {
                        "quantity": int(item.quantity),
                        "gross": quantize_amount(item_gross_revenue / Decimal(item.quantity)),
                        "discount": quantize_amount(item_discount_gross / Decimal(item.quantity)),
                        "net": quantize_amount(item_net_revenue / Decimal(item.quantity)),
                        "cost": quantize_amount(item_cost / Decimal(item.quantity)),
                    }
                )

    for return_item in return_items or []:
        product_id, item_name, item_variant = get_return_product_identity(return_item)
        key = (product_id, item_name, item_variant)
        if Decimal(return_item.refund_amount or 0) > ZERO and key not in grouped_rows:
            continue
        row = get_row(return_item.product, item_name, item_variant)
        if Decimal(return_item.refund_amount or 0) > ZERO:
            reversal = consume_return_profiles(return_profiles.get(key, []), return_item.quantity)
            if reversal:
                row["quantity"] -= reversal["quantity"]
                row["gross_revenue_raw"] -= reversal["gross"]
                row["discount_amount_raw"] -= reversal["discount"]
                row["net_revenue_raw"] -= reversal["net"]
                row["cost_raw"] -= reversal["cost"]
                continue

        revenue_delta = get_return_revenue_delta(return_item)
        row["quantity"] += int(return_item.quantity or 0) * get_return_quantity_direction(return_item)
        row["gross_revenue_raw"] += revenue_delta
        row["net_revenue_raw"] += revenue_delta
        row["cost_raw"] += get_return_cost_delta(return_item)

    rows = []
    for row in grouped_rows.values():
        gross_revenue = round_report_money(row["gross_revenue_raw"])
        discount_amount = round_report_money(row["discount_amount_raw"])
        net_revenue = round_report_money(row["net_revenue_raw"])
        cost = round_report_money(row["cost_raw"])
        if row["quantity"] == 0 and all(is_effectively_zero(value) for value in [gross_revenue, discount_amount, net_revenue, cost]):
            continue
        profit = quantize_amount(net_revenue - cost)
        rows.append(
            SimpleNamespace(
                name=row["name"],
                variant=row["variant"],
                quantity=row["quantity"],
                gross_revenue=gross_revenue,
                discount_amount=discount_amount,
                net_revenue=net_revenue,
                cost=cost,
                profit=profit,
                discount_rate=calculate_rate(discount_amount, gross_revenue),
                cost_profit_rate=calculate_rate(profit, cost),
                sales_margin_rate=calculate_rate(profit, net_revenue),
            )
        )

    return sorted(rows, key=lambda row: ((row.name or "").casefold(), row.variant or ""))


def build_daily_distribution_rows(sales, return_items=None):
    grouped_rows = {}
    return_profiles = {}

    def get_row(product, name=None, variant=None):
        name = name or product.name
        variant = product.variant if variant is None else variant
        key = (product.id, name, variant)
        return grouped_rows.setdefault(
            key,
            {
                "name": name,
                "variant": variant,
                "quantity": 0,
                "revenue": ZERO,
                "revenue_gross": ZERO,
            },
        )

    for sale in sales:
        sale_items = list(sale.items)
        line_revenues = [quantize_amount(item.line_total) for item in sale_items]
        line_revenue_total = quantize_amount(sum(line_revenues, ZERO))
        line_discount_total = quantize_amount(
            sum((Decimal(getattr(item, "discount_amount", 0) or 0) for item in sale_items), ZERO)
        )
        sale_total_discount = quantize_amount(
            getattr(sale, "total_discount", line_discount_total) or line_discount_total
        )
        footer_discount = quantize_amount(max(sale_total_discount - line_discount_total, ZERO))

        allocated_net_revenues = []
        remaining_footer_discount = footer_discount
        for index, line_revenue in enumerate(line_revenues):
            if index == len(line_revenues) - 1:
                footer_share = remaining_footer_discount
            elif line_revenue_total:
                footer_share = quantize_amount(footer_discount * line_revenue / line_revenue_total)
                remaining_footer_discount -= footer_share
            else:
                footer_share = ZERO
            allocated_net_revenues.append(quantize_amount(max(line_revenue - footer_share, ZERO)))

        allocated_net_total = quantize_amount(sum(allocated_net_revenues, ZERO))
        stored_gross_total = getattr(sale, "total_amount", None)
        gross_total = (
            quantize_amount(stored_gross_total)
            if stored_gross_total is not None
            else quantize_amount(sum((get_customer_gross_amount(value) for value in allocated_net_revenues), ZERO))
        )
        allocated_gross_revenues = []
        remaining_gross_total = gross_total
        for index, net_revenue in enumerate(allocated_net_revenues):
            if index == len(allocated_net_revenues) - 1:
                gross_revenue = remaining_gross_total
            elif allocated_net_total:
                gross_revenue = quantize_amount(gross_total * net_revenue / allocated_net_total)
                remaining_gross_total -= gross_revenue
            else:
                gross_revenue = ZERO
            allocated_gross_revenues.append(quantize_amount(max(gross_revenue, ZERO)))

        for item, item_revenue, item_revenue_gross in zip(
            sale_items,
            allocated_net_revenues,
            allocated_gross_revenues,
        ):
            item_name = getattr(item, "product_name_snapshot", None) or item.product.name
            item_variant = (
                item.product_variant_snapshot
                if hasattr(item, "product_variant_snapshot")
                else item.product.variant
            )
            row = get_row(item.product, item_name, item_variant)
            row["quantity"] += item.quantity
            row["revenue"] += item_revenue
            row["revenue_gross"] += item_revenue_gross
            if item.quantity > 0:
                key = (item.product.id, item_name, item_variant)
                return_profiles.setdefault(key, []).append(
                    {
                        "quantity": int(item.quantity),
                        "revenue": quantize_amount(item_revenue / Decimal(item.quantity)),
                        "revenue_gross": quantize_amount(item_revenue_gross / Decimal(item.quantity)),
                    }
                )

    for return_item in return_items or []:
        product_id, item_name, item_variant = get_return_product_identity(return_item)
        key = (product_id, item_name, item_variant)
        if Decimal(return_item.refund_amount or 0) > ZERO and key not in grouped_rows:
            continue
        row = get_row(return_item.product, item_name, item_variant)
        if Decimal(return_item.refund_amount or 0) > ZERO:
            reversal = consume_return_profiles(return_profiles.get(key, []), return_item.quantity)
            if reversal:
                row["quantity"] -= reversal["quantity"]
                row["revenue"] -= reversal["revenue"]
                row["revenue_gross"] -= reversal["revenue_gross"]
                continue

        row["quantity"] += int(return_item.quantity or 0) * get_return_quantity_direction(return_item)
        row["revenue"] += quantize_amount(Decimal(return_item.refund_amount or 0) * Decimal("-1"))
        row["revenue_gross"] += get_return_revenue_delta(return_item)

    rows = []
    for row in grouped_rows.values():
        revenue = quantize_amount(row["revenue"])
        revenue_gross = quantize_amount(row["revenue_gross"])
        if row["quantity"] == 0 and is_effectively_zero(revenue) and is_effectively_zero(revenue_gross):
            continue
        rows.append(
            SimpleNamespace(
                name=row["name"],
                variant=row["variant"],
                quantity=row["quantity"],
                revenue=revenue,
                revenue_gross=revenue_gross,
            )
        )

    return sorted(rows, key=lambda row: (-row.quantity, (row.name or "").casefold(), row.variant or ""))


def get_return_records_for_sales(start, end, sale_ids):
    sale_ids = [sale_id for sale_id in sale_ids if sale_id]
    if not sale_ids:
        return []

    return (
        Return.query.options(joinedload(Return.items).joinedload(ReturnItem.product))
        .filter(
            Return.return_date >= start,
            Return.return_date <= end,
            Return.original_sale_id.in_(sale_ids),
        )
        .all()
    )


def get_low_stock_products(threshold):
    products = (
        Product.query.join(StoreInventory, StoreInventory.product_id == Product.id)
        .order_by(StoreInventory.stock_quantity.asc(), Product.name.asc())
        .all()
    )
    attach_stock_thresholds(products, threshold)
    return [product for product in products if product.stock_quantity <= product.effective_low_stock_threshold]


def build_category_threshold_map():
    return {
        category.name: category.critical_stock_level
        for category in Category.query.order_by(Category.name.asc()).all()
    }


def get_effective_low_stock_threshold(product, fallback_threshold, category_thresholds=None):
    if getattr(product, "critical_stock_level", None) is not None:
        return int(product.critical_stock_level)

    category_thresholds = category_thresholds or build_category_threshold_map()
    category_threshold = category_thresholds.get(product.category)
    if category_threshold is not None:
        return int(category_threshold)

    return int(fallback_threshold)


def attach_stock_thresholds(products, fallback_threshold, category_thresholds=None):
    category_thresholds = category_thresholds or build_category_threshold_map()
    for product in products:
        effective_threshold = get_effective_low_stock_threshold(
            product,
            fallback_threshold,
            category_thresholds=category_thresholds,
        )
        product.effective_low_stock_threshold = effective_threshold
        product.effective_critical_stock_threshold = effective_threshold * 2
        product.threshold_source = (
            "product"
            if getattr(product, "critical_stock_level", None) is not None
            else "category"
            if category_thresholds.get(product.category) is not None
            else "global"
        )
    return category_thresholds


def get_dashboard_metrics(today=None):
    today = today or date.today()
    start = start_of_day(today)
    end = end_of_day(today)

    sales = (
        Sale.query.options(joinedload(Sale.items).joinedload(SaleItem.product))
        .filter(Sale.sale_date >= start, Sale.sale_date <= end)
        .all()
    )
    return_records = get_return_records_for_sales(start, end, [sale.id for sale in sales])
    return_items = [item for record in return_records for item in record.items]
    product_rows = build_profit_product_rows(sales, return_items)
    returned_by_sale = {}
    for record in return_records:
        returned_by_sale.setdefault(record.original_sale_id, ZERO)
        returned_by_sale[record.original_sale_id] += sum_return_items_customer_gross(record.items)

    total_sales = sum(
        1 for sale in sales if quantize_amount(Decimal(sale.total_amount or 0) - returned_by_sale.get(sale.id, ZERO)) > ZERO
    )
    revenue = quantize_amount(sum((row.net_revenue for row in product_rows), ZERO))
    discount = quantize_amount(sum((row.discount_amount for row in product_rows), ZERO))
    profit = quantize_amount(sum((row.profit for row in product_rows), ZERO))

    return {
        "total_sales": total_sales,
        "revenue": quantize_amount(revenue),
        "discount": quantize_amount(discount),
        "profit": profit,
    }


def get_last_7_days_sales():
    today = date.today()
    rows = []
    for offset in range(6, -1, -1):
        current_day = today - timedelta(days=offset)
        start = start_of_day(current_day)
        end = end_of_day(current_day)
        revenue = (
            Sale.query.with_entities(func.coalesce(func.sum(Sale.total_amount), 0))
            .filter(Sale.sale_date >= start, Sale.sale_date <= end)
            .scalar()
        )
        rows.append(
            {
                "label": current_day.strftime("%d.%m"),
                "value": float(quantize_amount(revenue or 0)),
            }
        )
    return rows


def get_top_products(limit=5):
    rows = (
        SaleItem.query.with_entities(
            Product.name,
            Product.variant,
            func.sum(SaleItem.quantity).label("quantity"),
            func.sum((SaleItem.unit_price * SaleItem.quantity) - SaleItem.discount_amount).label(
                "total"
            ),
        )
        .join(Product, Product.id == SaleItem.product_id)
        .group_by(Product.id, Product.name, Product.variant)
        .order_by(func.sum(SaleItem.quantity).desc(), Product.name.asc())
        .limit(limit)
        .all()
    )
    return rows


def get_daily_report(start_date, end_date=None):
    start_date = parse_iso_date(start_date, fallback=date.today()) if isinstance(start_date, str) else start_date
    end_date = parse_iso_date(end_date, fallback=start_date) if isinstance(end_date, str) else (end_date or start_date)
    if end_date < start_date:
        start_date, end_date = end_date, start_date

    start = start_of_day(start_date)
    end = end_of_day(end_date)

    sales = (
        Sale.query.options(joinedload(Sale.items).joinedload(SaleItem.product))
        .filter(Sale.sale_date >= start, Sale.sale_date <= end)
        .all()
    )
    return_records = get_return_records_for_sales(start, end, [sale.id for sale in sales])
    return_items = [item for record in return_records for item in record.items]
    distribution = build_daily_distribution_rows(sales, return_items)
    profit_rows = build_profit_product_rows(sales, return_items)

    returned_by_sale = {}
    for record in return_records:
        returned_by_sale.setdefault(record.original_sale_id, ZERO)
        returned_by_sale[record.original_sale_id] += sum_return_items_customer_gross(record.items)

    revenue_gross = quantize_amount(sum((row.revenue_gross for row in distribution), ZERO))
    revenue_net = quantize_amount(sum((row.revenue for row in distribution), ZERO))
    summary = {
        "start_date": start_date,
        "end_date": end_date,
        "total_sales": sum(
            1 for sale in sales if quantize_amount(Decimal(sale.total_amount or 0) - returned_by_sale.get(sale.id, ZERO)) > ZERO
        ),
        "revenue": revenue_gross,
        "revenue_net": revenue_net,
        "revenue_gross": revenue_gross,
        "discount": quantize_amount(sum((row.discount_amount for row in profit_rows), ZERO)),
        "sold_units": sum((row.quantity for row in distribution), 0),
    }

    return summary, distribution


def get_profit_report(start_date, end_date):
    start_date = parse_iso_date(start_date, fallback=date.today()) if isinstance(start_date, str) else start_date
    end_date = parse_iso_date(end_date, fallback=start_date) if isinstance(end_date, str) else end_date

    start = start_of_day(start_date)
    end = end_of_day(end_date)

    sales = (
        Sale.query.options(joinedload(Sale.items))
        .filter(Sale.sale_date >= start, Sale.sale_date <= end)
        .all()
    )

    return_records = get_return_records_for_sales(start, end, [sale.id for sale in sales])
    return_items = [item for record in return_records for item in record.items]
    returned_by_sale = {}
    for record in return_records:
        returned_by_sale.setdefault(record.original_sale_id, ZERO)
        returned_by_sale[record.original_sale_id] += sum_return_items_customer_gross(record.items)

    gross_before_discount = ZERO
    revenue_after_discount = ZERO
    line_discount_total = ZERO
    sale_discount_amounts = []
    sale_discount_rates = []
    for sale in sales:
        if quantize_amount(Decimal(sale.total_amount or 0) - returned_by_sale.get(sale.id, ZERO)) <= ZERO:
            continue

        sale_base_net = quantize_amount(
            sum((item.unit_price * item.quantity for item in sale.items), ZERO)
        )
        sale_gross_before_discount = round_report_money(sale_base_net * PRODUCT_VAT_MULTIPLIER)
        sale_revenue_after_discount = quantize_amount(sale.total_amount or 0)
        sale_discount_amount = quantize_amount(max(sale_gross_before_discount - sale_revenue_after_discount, ZERO))

        gross_before_discount += sale_gross_before_discount
        revenue_after_discount += sale_revenue_after_discount
        line_discount_total += round_report_money(
            sum((item.discount_amount for item in sale.items), ZERO) * PRODUCT_VAT_MULTIPLIER
        )
        if sale_discount_amount:
            sale_discount_amounts.append(sale_discount_amount)
        if sale_gross_before_discount and sale_discount_amount:
            sale_discount_rates.append((sale_discount_amount / sale_gross_before_discount) * 100)

    product_rows = build_profit_product_rows(sales, return_items)
    cost = round_report_money(sum((row.cost for row in product_rows), ZERO))
    refunded = sum_return_items_customer_gross(return_items)
    gross_before_discount = quantize_amount(sum((row.gross_revenue for row in product_rows), ZERO))
    revenue_after_discount = quantize_amount(sum((row.net_revenue for row in product_rows), ZERO))
    discount = quantize_amount(max(gross_before_discount - revenue_after_discount, ZERO))
    line_discount_total = quantize_amount(line_discount_total)
    footer_discount_total = quantize_amount(max(discount - line_discount_total, ZERO))
    discounted_sales_count = len(sale_discount_amounts)
    weighted_discount_rate = calculate_rate(discount, gross_before_discount)
    average_discount_amount = (
        round_report_money(sum(sale_discount_amounts, ZERO) / discounted_sales_count)
        if discounted_sales_count
        else ZERO
    )
    average_discount_rate = (
        quantize_amount(sum(sale_discount_rates, ZERO) / len(sale_discount_rates))
        if sale_discount_rates
        else ZERO
    )

    return {
        "start_date": start_date,
        "end_date": end_date,
        "revenue": revenue_after_discount,
        "discount": discount,
        "line_discount_total": line_discount_total,
        "footer_discount_total": footer_discount_total,
        "weighted_discount_rate": weighted_discount_rate,
        "average_discount_rate": average_discount_rate,
        "average_discount_amount": average_discount_amount,
        "discounted_sales_count": discounted_sales_count,
        "gross_before_discount": gross_before_discount,
        "revenue_after_discount": revenue_after_discount,
        "cost": cost,
        "refunded": refunded,
        "profit": quantize_amount(revenue_after_discount - cost),
        "products": product_rows,
    }
