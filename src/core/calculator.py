import math

def get_coefficient(value, ranges, default=1.0):
    """
    Helper to find a coefficient from a range list.
    辅助函数：根据数值在区间列表中查找对应的系数。
    """
    for item in ranges:
        if item['min'] <= value < item['max']:
            if 'discount' in item:
                return item['discount']
            return item['coeff']
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
        dict: detailed calculation result containing 'final_fee', 'theoretical_fee', etc.
    """
    category = row_data.get("新品大类")
    sku_count = row_data.get("同一供应商单次引进SKU数", 0)
    
    # 获取采购类型，默认为 '统采' (兼容旧数据或未选择的情况)
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
    
    # SKU Discount (SKU数量折扣)
    all_sku_config = config.get("sku_discounts", {})
    # 新逻辑：按大类取
    sku_rules = all_sku_config.get(category, {})
    sku_discount = get_coefficient(sku_count, sku_rules, default=1.0) # 默认系数1.0
    coeffs.append(("SKU数量折扣", sku_discount))
    
    # Gross Margin (毛利率系数)
    margin = row_data.get("预估毛利率(%)", 0)
    margin_coeff = get_coefficient(margin, config.get("gross_margin_coeffs", []))
    coeffs.append(("毛利率系数", margin_coeff))
    
    # Payment Terms (付款方式系数)
    payment = row_data.get("付款方式")
    payment_coeff = config.get("payment_coeffs", {}).get(payment, 1.0)
    coeffs.append(("付款方式系数", payment_coeff))
    
    # Cost Price (底价系数)
    cost = row_data.get("底价", 0)
    cost_coeff = get_coefficient(cost, config.get("cost_price_coeffs", []))
    coeffs.append(("底价系数", cost_coeff))
    
    # Return Policy (退货条件系数)
    ret_policy = row_data.get("退货条件")
    ret_coeff = config.get("return_policy_coeffs", {}).get(ret_policy, 1.0)
    coeffs.append(("退货条件系数", ret_coeff))
    
    # Supplier Type (供应商类型系数)
    supp_type = row_data.get("供应商类型")
    supp_coeff = config.get("supplier_type_coeffs", {}).get(supp_type, 1.0)
    coeffs.append(("供应商类型系数", supp_coeff))
    
    # 3. Final Calculation (最终计算)
    discount_factor = 1.0
    
    breakdown.append(f"\n--- 系数调整 ---")
    for name, val in coeffs:
        discount_factor *= val
        breakdown.append(f"{name}: x{val}")
    
    # 养生中药且毛利率>=65%,折扣设为0，不收取铺货费    
    is_exempt_from_floor = False  # 初始化免单标记
    if category == "养生中药" and margin >= 65:
        discount_factor = 0
        is_exempt_from_floor = True
        breakdown.append("🚀 满足(养生中药 & 毛利率>=65%)：折扣置0，且免收保底费")

    # 先对折扣系数四舍五入保留2位小数
    discount_factor = round(discount_factor, 2)
    raw_final_fee = total_base_fee * discount_factor
    
    # 取整逻辑：先取整，若个位数不为0则向上取整到10的倍数
    # 例如：121 -> 130, 129 -> 130, 120 -> 120
    final_fee = math.ceil(int(raw_final_fee) / 10) * 10
        
    # 4. Minimum Floor (最低保底费逻辑)
    # 获取该大类的保底配置
    # config_loader 应该返回类似: {'中西成药': {'统采': 7500, '地采': 2000}, ...}
    category_floors = config.get("min_fee_floors", {}).get(category, 0)
    
    min_floor = 0
    floor_source_desc = "未知标准"

    if is_exempt_from_floor:
        min_floor = 0
        floor_source_desc = "特殊免单(养生中药>=65%)"
    elif isinstance(category_floors, dict):
        # 新逻辑：根据采购类型取值
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
        "store_details": store_counts ,
        "procurement_type":procurement_type
    }