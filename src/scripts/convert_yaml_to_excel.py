import yaml
import pandas as pd
import os
import sys

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
if project_root not in sys.path:
    sys.path.append(project_root)

def load_yaml_config(yaml_path):
    with open(yaml_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def convert_to_excel(config, output_path):
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        
        # 1. Base Fees (2D Table)
        # YAML: {'护肤': {'超级旗舰店': 500, ...}, ...}
        # Excel: Columns=[新品大类, 超级旗舰店, 旗舰店, ...]
        base_fees = config.get('base_fees', {})
        rows = []
        for category, fees in base_fees.items():
            row = {'新品大类': category}
            row.update(fees)
            rows.append(row)
        
        if rows:
            df_base = pd.DataFrame(rows)
            # Ensure column order if possible, but dynamic is fine
            cols = ['新品大类'] + [c for c in df_base.columns if c != '新品大类']
            df_base = df_base[cols]
            df_base.to_excel(writer, sheet_name='基础费用', index=False)
        
        # 2. SKU Discounts (List of dicts)
        sku_discounts = config.get('sku_discounts', [])
        if sku_discounts:
            pd.DataFrame(sku_discounts).to_excel(writer, sheet_name='SKU数量折扣', index=False)
            
        # 3. Gross Margin Coeffs
        gm_coeffs = config.get('gross_margin_coeffs', [])
        if gm_coeffs:
            pd.DataFrame(gm_coeffs).to_excel(writer, sheet_name='毛利率系数', index=False)
            
        # 4. Payment Coeffs (Dict -> Table)
        # YAML: {'现结': 0.9, ...}
        payment_coeffs = config.get('payment_coeffs', {})
        if payment_coeffs:
            df_pay = pd.DataFrame(list(payment_coeffs.items()), columns=['付款方式', '系数'])
            df_pay.to_excel(writer, sheet_name='付款方式系数', index=False)
            
        # 5. Cost Price Coeffs
        cp_coeffs = config.get('cost_price_coeffs', [])
        if cp_coeffs:
            pd.DataFrame(cp_coeffs).to_excel(writer, sheet_name='进价系数', index=False)
            
        # 6. Return Policy Coeffs (Dict -> Table)
        rp_coeffs = config.get('return_policy_coeffs', {})
        if rp_coeffs:
            df_rp = pd.DataFrame(list(rp_coeffs.items()), columns=['退货条件', '系数'])
            df_rp.to_excel(writer, sheet_name='退货条件系数', index=False)
            
        # 7. Supplier Type Coeffs (Dict -> Table)
        st_coeffs = config.get('supplier_type_coeffs', {})
        if st_coeffs:
            df_st = pd.DataFrame(list(st_coeffs.items()), columns=['供应商类型', '系数'])
            df_st.to_excel(writer, sheet_name='供应商类型系数', index=False)
            
        # 8. Min Fee Floors (Dict -> Table)
        min_fees = config.get('min_fee_floors', {})
        if min_fees:
            df_min = pd.DataFrame(list(min_fees.items()), columns=['新品大类', '保底费'])
            df_min.to_excel(writer, sheet_name='最低保底费', index=False)
            
    print(f"✅ Successfully converted YAML to Excel: {output_path}")

def main():
    yaml_path = os.path.join(project_root, 'config', 'coefficients.yaml')
    excel_path = os.path.join(project_root, 'config', 'coefficients.xlsx')
    
    if not os.path.exists(yaml_path):
        print(f"❌ YAML file not found: {yaml_path}")
        return
        
    try:
        config = load_yaml_config(yaml_path)
        convert_to_excel(config, excel_path)
    except Exception as e:
        print(f"❌ Conversion failed: {e}")

if __name__ == "__main__":
    main()
