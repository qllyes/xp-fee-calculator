import math

def get_coefficient(value, ranges, default=1.0):
    """Helper to find a coefficient from a range list."""
    for item in ranges:
        if item['min'] <= value < item['max']:
            if 'discount' in item:
                return item['discount']
            return item['coeff']
    return default

def calculate_fee(row_data, store_counts, config):
    """
    Calculates the total fee and returns a breakdown.
    
    Args:
        row_data: dict containing business terms (category, sku_count, etc.)
        store_counts: dict of {store_type: count}
        config: loaded configuration dict
        
    Returns:
        dict: detailed calculation result containing 'final_fee', 'theoretical_fee', etc.
    """
    category = row_data.get("新品大类")
    sku_count = row_data.get("同一供应商单次引进SKU数", 0)
    
    # 1. Base Fee Calculation
    base_fees_config = config.get("base_fees", {}).get(category, {})
    total_base_fee = 0
    breakdown = []
    
    breakdown.append(f"--- 基础费用 ---")
    for store_type, count in store_counts.items():
        if count > 0:
            unit_fee = base_fees_config.get(store_type, 0)
            subtotal = unit_fee * count
            total_base_fee += subtotal
            breakdown.append(f"{store_type}: {count}家 * {unit_fee}元 = {subtotal}元")
            
    breakdown.append(f"基础费用合计: {total_base_fee}元")
    
    # 2. Coefficients
    coeffs = []
    
    # SKU Discount
    sku_discount = get_coefficient(sku_count, config.get("sku_discounts", []))
    coeffs.append(("SKU数量折扣", sku_discount))
    
    # Gross Margin
    margin = row_data.get("预估毛利率(%)", 0)
    margin_coeff = get_coefficient(margin, config.get("gross_margin_coeffs", []))
    coeffs.append(("毛利率系数", margin_coeff))
    
    # Payment Terms
    payment = row_data.get("付款方式")
    payment_coeff = config.get("payment_coeffs", {}).get(payment, 1.0)
    coeffs.append(("付款方式系数", payment_coeff))
    
    # Cost Price
    cost = row_data.get("进价", 0)
    cost_coeff = get_coefficient(cost, config.get("cost_price_coeffs", []))
    coeffs.append(("进价系数", cost_coeff))
    
    # Return Policy
    ret_policy = row_data.get("退货条件")
    ret_coeff = config.get("return_policy_coeffs", {}).get(ret_policy, 1.0)
    coeffs.append(("退货条件系数", ret_coeff))
    
    # Supplier Type
    supp_type = row_data.get("供应商类型")
    supp_coeff = config.get("supplier_type_coeffs", {}).get(supp_type, 1.0)
    coeffs.append(("供应商类型系数", supp_coeff))
    
    # 3. Final Calculation
    discount_factor = 1.0
    
    breakdown.append(f"\n--- 系数调整 ---")
    for name, val in coeffs:
        discount_factor *= val
        breakdown.append(f"{name}: x{val}")
        
    # 先对折扣系数四舍五入保留2位小数
    discount_factor = round(discount_factor, 2)
    raw_final_fee = total_base_fee * discount_factor
    
    # 取整逻辑：先取整，若个位数不为0则向上取整到10的倍数
    final_fee = math.ceil(int(raw_final_fee) / 10) * 10
        
    # 4. Minimum Floor
    min_floor = config.get("min_fee_floors", {}).get(category, 0)
    breakdown.append(f"\n计算金额: {final_fee:.2f}元")
    
    is_floor_triggered = False
    if final_fee < min_floor:
        breakdown.append(f"触发最低兜底: {min_floor}元")
        final_fee = min_floor
        is_floor_triggered = True
        
    return {
        "final_fee": final_fee,
        "theoretical_fee": total_base_fee,
        "discount_factor": discount_factor,
        "coefficients": coeffs,
        "breakdown_str": "\n".join(breakdown),
        "is_floor_triggered": is_floor_triggered,
        "min_floor": min_floor,
        "store_details": store_counts 
    }