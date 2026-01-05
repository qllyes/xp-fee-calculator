import pandas as pd
import os
from src.core.file_utils import read_excel_safe

def load_config(config_path="config/coefficients.xlsx"):
    """
    Loads the configuration from an Excel file.
    Parses multiple sheets into the expected dictionary structure.
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found at {config_path}")
    
    # Read all sheets
    try:
        # read_excel_safe returns a dict of DataFrames when sheet_name=None is passed
        xls_dict = read_excel_safe(config_path, sheet_name=None)
    except Exception as e:
        raise ValueError(f"Failed to read config file: {e}")

    config = {}

    # 1. Base Fees
    if '基础费用' in xls_dict:
        df = xls_dict['基础费用']
        base_fees = {}
        for _, row in df.iterrows():
            category = row['新品大类']
            # Convert row to dict and remove '新品大类'
            fees = row.to_dict()
            del fees['新品大类']
            base_fees[category] = fees
        config['base_fees'] = base_fees

    # 2. SKU Discounts
    if '单次引入SKU数量折扣' in xls_dict:
        df_sku = xls_dict['单次引入SKU数量折扣']
        sku_discounts_map = {}
        # 按大类分组构建字典
        for category_name, group in df_sku.groupby('新品大类'):
            # 将该大类的所有规则转为 list of dict，并只保留 min, max, discount
            sku_discounts_map[category_name] = group[['min', 'max', 'discount']].to_dict('records')
        config['sku_discounts'] = sku_discounts_map

    # 3. Gross Margin Coeffs
    if '毛利率系数' in xls_dict:
        config['gross_margin_coeffs'] = xls_dict['毛利率系数'].to_dict('records')

    # 4. Payment Coeffs
    if '付款方式系数' in xls_dict:
        df = xls_dict['付款方式系数']
        config['payment_coeffs'] = dict(zip(df['付款方式'], df['系数']))

    # 5. Cost Price Coeffs
    if '底价系数' in xls_dict:
        config['cost_price_coeffs'] = xls_dict['底价系数'].to_dict('records')

    # 6. Return Policy Coeffs (Standard Simple Lookup)
    # 简单的逻辑：直接通过名称查找系数
    if '退货条件系数' in xls_dict:
        df = xls_dict['退货条件系数']
        config['return_policy_coeffs'] = dict(zip(df['退货条件'], df['系数']))
    
    # [新增] 7. Return Ratio Rules (Advanced Logic)
    # 用于处理像 "效期可退" 这样需要根据比例分档的复杂逻辑
    # Excel结构: | 退货条件 | min | max | 系数 |
    config['return_ratio_rules'] = {}
    if '退货比例系数' in xls_dict:
        df_ratio = xls_dict['退货比例系数']
        # 确保必要的列存在
        required_cols = ['退货条件', 'min', 'max', '系数']
        if all(col in df_ratio.columns for col in required_cols):
             for policy_name, group in df_ratio.groupby('退货条件'):
                 config['return_ratio_rules'][policy_name] = group[['min', 'max', '系数']].rename(columns={'系数': 'coeff'}).to_dict('records')
    
    # 8. Supplier Type Coeffs
    if '供应商类型系数' in xls_dict:
        df = xls_dict['供应商类型系数']
        config['supplier_type_coeffs'] = dict(zip(df['供应商类型'], df['系数']))

    # 9. Min Fee Floors
    if '最低保底费' in xls_dict:
        df = xls_dict['最低保底费']
        min_fee_floors = {}
        if not df.empty:
            for _, row in df.iterrows():
                cat = row.get('新品大类')
                if cat:
                    min_fee_floors[cat] = {
                        '统采': row.get('统采保底费', 0),
                        '地采': row.get('地采保底费', 0)
                    }
        config['min_fee_floors'] = min_fee_floors

    # 10. Prescription Categories
    if '处方类别' in xls_dict:
        df = xls_dict['处方类别']
        if not df.empty and df.shape[1] > 0:
            config['prescription_categories'] = df.iloc[:, 0].dropna().astype(str).tolist()
    
    # 11. War Zones
    if '提报战区' in xls_dict:
        df = xls_dict['提报战区']
        if not df.empty and df.shape[1] > 0:
            zones = df.iloc[:, 0].dropna().astype(str).tolist()
            if "全集团" in zones:
                zones.remove("全集团")
            zones.insert(0, "全集团")
            config['war_zones'] = zones
        else:
            config['war_zones'] = ["全集团"]
    else:
        config['war_zones'] = ["全集团"]

    return config