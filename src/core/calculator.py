import math

def get_coefficient(value, ranges, default=1.0):
    """
    Helper to find a coefficient from a range list.
    辅助函数：根据数值在区间列表中查找对应的系数。
    """
    for item in ranges:
        # 使用 safe get 兼容不同的 key 名称 (有的配置叫 discount 有的叫 coeff)
        coeff_val = item.get('discount') if 'discount' in item else item.get('coeff', 1.0)
        
        if item['min'] <= value < item['max']:
            return coeff_val
            
    return default

def calculate_fee(row_data, store_counts, config):
    """
    Calculates the total fee and returns a breakdown.
    计算总费用并返回详细的拆解过程。
    
    Args:
        row_data: dict containing business terms (category, sku_count, procurement_type, etc.)
        store_counts: dict of {store_type: count}
        config: loaded configuration dict
        
    Returns:
        dict: detailed calculation result
    """
    category = row_data.get("新品大类")
    sku_count = row_data.get("同一供应商单次引进SKU数", 1)
    procurement_type = row_data.get("统采or地采", "统采")
    
    # 1. Base Fee Calculation (基础费用计算)
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
    
    # 2. Coefficients (系数获取)
    coeffs = []
    
    # SKU Discount
    all_sku_config = config.get("sku_discounts", {})
    sku_rules = all_sku_config.get(category, {})
    sku_discount = get_coefficient(sku_count, sku_rules, default=1.0)
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
    cost = row_data.get("底价", 0)
    cost_coeff = get_coefficient(cost, config.get("cost_price_coeffs", []))
    coeffs.append(("底价系数", cost_coeff))
    
    # --- [修改点] Return Policy Logic (退货条件系数) ---
    ret_policy = row_data.get("退货条件")
    ret_ratio_rules = config.get("return_ratio_rules", {})
    
    # 优先判断是否存在复杂的比例规则 (如：效期可退, 效期可退+破损可退)
    if ret_policy in ret_ratio_rules:
        # 获取用户输入的退货比例 (默认为0)
        ret_ratio_val = row_data.get("退货比例(%)", 0.0)
        # 使用通用辅助函数根据比例查找区间系数
        ret_coeff = get_coefficient(ret_ratio_val, ret_ratio_rules[ret_policy], default=1.0)
        coeffs.append((f"退货条件系数({ret_policy} @ {ret_ratio_val}%)", ret_coeff))
    else:
        # 否则使用简单的字典查找 (普通退货条件)
        ret_coeff = config.get("return_policy_coeffs", {}).get(ret_policy, 1.0)
        coeffs.append((f"退货条件系数({ret_policy})", ret_coeff))
    
    # Supplier Type
    supp_type = row_data.get("供应商类型")
    supp_coeff = config.get("supplier_type_coeffs", {}).get(supp_type, 1.0)
    coeffs.append(("供应商类型系数", supp_coeff))
    
    # 3. Final Calculation (最终计算)
    discount_factor = 1.0
    
    breakdown.append(f"\n--- 系数调整 ---")
    for name, val in coeffs:
        discount_factor *= val
        breakdown.append(f"{name}: x{val}")
    
    # 特殊免单逻辑
    is_exempt_from_floor = False
    if category == "养生中药" and margin >= 65:
        discount_factor = 0
        is_exempt_from_floor = True
        breakdown.append("🚀 满足(养生中药 & 毛利率>=65%)：折扣置0，且免收保底费")

    discount_factor = round(discount_factor, 2)
    raw_final_fee = total_base_fee * discount_factor
    
    final_fee = math.ceil(int(raw_final_fee) / 10) * 10
        
    # 4. Minimum Floor Logic
    category_floors = config.get("min_fee_floors", {}).get(category, 0)
    min_floor = 0
    floor_source_desc = "未知标准"

    if is_exempt_from_floor:
        min_floor = 0
        floor_source_desc = "特殊免单(养生中药>=65%)"
    elif isinstance(category_floors, dict):
        min_floor = category_floors.get(procurement_type, 0)
        floor_source_desc = f"{procurement_type}保底"

    breakdown.append(f"\n--- 最终核算 ---")
    breakdown.append(f"计算金额: {final_fee:.2f}元")
    
    is_floor_triggered = False
    if final_fee < min_floor:
        breakdown.append(f"触发最低兜底 ({floor_source_desc}): {min_floor}元")
        final_fee = min_floor
        is_floor_triggered = True
    else:
        breakdown.append(f"未触发兜底 (当前{floor_source_desc}线: {min_floor}元)")
        
    return {
        "final_fee": final_fee,
        "theoretical_fee": total_base_fee,
        "discount_factor": discount_factor,
        "coefficients": coeffs,
        "breakdown_str": "\n".join(breakdown),
        "is_floor_triggered": is_floor_triggered,
        "min_floor": min_floor,
        "floor_source_desc": floor_source_desc,
        "store_details": store_counts,
        "procurement_type": procurement_type
    }