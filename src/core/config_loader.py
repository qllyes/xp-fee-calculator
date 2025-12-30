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
    if 'SKU数量折扣' in xls_dict:
        config['sku_discounts'] = xls_dict['SKU数量折扣'].to_dict('records')

    # 3. Gross Margin Coeffs
    if '毛利率系数' in xls_dict:
        config['gross_margin_coeffs'] = xls_dict['毛利率系数'].to_dict('records')

    # 4. Payment Coeffs
    if '付款方式系数' in xls_dict:
        df = xls_dict['付款方式系数']
        config['payment_coeffs'] = dict(zip(df['付款方式'], df['系数']))

    # 5. Cost Price Coeffs
    if '进价系数' in xls_dict:
        config['cost_price_coeffs'] = xls_dict['进价系数'].to_dict('records')

    # 6. Return Policy Coeffs
    if '退货条件系数' in xls_dict:
        df = xls_dict['退货条件系数']
        config['return_policy_coeffs'] = dict(zip(df['退货条件'], df['系数']))

    # 7. Supplier Type Coeffs
    if '供应商类型系数' in xls_dict:
        df = xls_dict['供应商类型系数']
        config['supplier_type_coeffs'] = dict(zip(df['供应商类型'], df['系数']))
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
    if 'SKU数量折扣' in xls_dict:
        config['sku_discounts'] = xls_dict['SKU数量折扣'].to_dict('records')

    # 3. Gross Margin Coeffs
    if '毛利率系数' in xls_dict:
        config['gross_margin_coeffs'] = xls_dict['毛利率系数'].to_dict('records')

    # 4. Payment Coeffs
    if '付款方式系数' in xls_dict:
        df = xls_dict['付款方式系数']
        config['payment_coeffs'] = dict(zip(df['付款方式'], df['系数']))

    # 5. Cost Price Coeffs
    if '进价系数' in xls_dict:
        config['cost_price_coeffs'] = xls_dict['进价系数'].to_dict('records')

    # 6. Return Policy Coeffs
    if '退货条件系数' in xls_dict:
        df = xls_dict['退货条件系数']
        config['return_policy_coeffs'] = dict(zip(df['退货条件'], df['系数']))

    # 7. Supplier Type Coeffs
    if '供应商类型系数' in xls_dict:
        df = xls_dict['供应商类型系数']
        config['supplier_type_coeffs'] = dict(zip(df['供应商类型'], df['系数']))

    # 8. Min Fee Floors
    if '最低保底费' in xls_dict:
        df = xls_dict['最低保底费']
        config['min_fee_floors'] = dict(zip(df['新品大类'], df['保底费']))

    # 9. Prescription Categories (New)
    # 假设 '处方类别' sheet页有一列叫 '处方类别'
    if '处方类别' in xls_dict:
        df = xls_dict['处方类别']
        if not df.empty and df.shape[1] > 0:
            # 默认取第一列作为选项列表
            config['prescription_categories'] = df.iloc[:, 0].dropna().astype(str).tolist()
        else:
            config['prescription_categories'] = []
    else:
        config['prescription_categories'] = []

    # 10. 提报战区 (New)
    if '提报战区' in xls_dict:
        df = xls_dict['提报战区']
        if not df.empty and df.shape[1] > 0:
            # 默认取第一列作为选项列表
            zones = df.iloc[:, 0].dropna().astype(str).tolist()
            # 确保 "全集团" 在列表中，且在第一个位置
            if "全集团" in zones:
                zones.remove("全集团")
            zones.insert(0, "全集团")
            config['war_zones'] = zones
        else:
            config['war_zones'] = ["全集团"]
    else:
        config['war_zones'] = ["全集团"]

    return config