import pandas as pd
import os
from src.core.file_utils import read_excel_safe

def load_store_master(path="data/store_master.xlsx"):
    return pd.read_excel(path)

def load_xp_mapping(path="data/处方类别与批文分类表.xlsx"):
    """
    加载处方类别与批文分类的映射表。
    返回一个字典: {'处方类别名称': 'xp_code'}
    """
    if not os.path.exists(path):
        print(f"Warning: Mapping file not found at {path}")
        return {}
    
    try:
        df = read_excel_safe(path)
        # 确保列名存在 (根据需求：【处方类别、批文分类编码】)
        if '处方类别' not in df.columns or '批文分类编码' not in df.columns:
            print("Warning: Mapping file columns mismatch. Expected '处方类别' and '批文分类编码'")
            return {}

        # 清洗数据：去除空值，确保都为字符串格式以便对比
        df = df.dropna(subset=['处方类别', '批文分类编码'])
        # 去除两端空格，防止匹配失败
        keys = df['处方类别'].astype(str).str.strip()
        values = df['批文分类编码'].astype(str).str.strip()
        
        mapping = dict(zip(keys, values))
        return mapping
    except Exception as e:
        print(f"Error loading xp mapping: {e}")
        return {}

def calc_auto_counts(store_master_df, channel, restricted_xp_code=None):
    """
    Calculates store counts based on the selected channel and prescription restrictions.
    
    Args:
        store_master_df: DataFrame of the store master data.
        channel: The selected channel color ("黄色", "蓝色", "绿色") or "自定义".
        restricted_xp_code: (Optional) The xp_code string to check against store restrictions.
                            e.g., "5". If a store has "5" in its restricted list, it will be excluded.
    
    Returns:
        dict: A dictionary of {store_type: count}.
    """
    if channel == "自定义":
        return {} # Should be handled by manual extraction
    
    # --- 受限门店过滤逻辑 ---
    # 只有当传入了限制编码，且DataFrame中有'受限批文分类编码'这一列时才执行
    current_df = store_master_df
    
    if restricted_xp_code is not None and "受限批文分类编码" in current_df.columns:
        target_code = str(restricted_xp_code).strip()
        
        # 如果 target_code 是无效值（如 nan），则不进行过滤
        if target_code and target_code.lower() != 'nan':
            
            def is_store_excluded(cell_value):
                """
                判断门店是否应该被剔除。
                规则：
                1. cell_value 为空 -> 不受限 -> 不剔除 (Return False)
                2. cell_value 包含 target_code -> 受限 -> 剔除 (Return True)
                """
                if pd.isna(cell_value) or str(cell_value).strip() == "":
                    return False # 空值表示无限制，不剔除
                
                # 将 "5,6,10" 分割为 ["5", "6", "10"]
                # 兼容中文逗号，以防万一
                val_str = str(cell_value).replace("，", ",")
                codes = [c.strip() for c in val_str.split(',')]
                
                # 如果目标代码在列表中，则该门店受限，需要剔除
                return target_code in codes

            # 找出需要剔除的行 (True 表示需要剔除)
            exclude_mask = current_df["受限批文分类编码"].apply(is_store_excluded)
            
            # 保留 不需要剔除 (~exclude_mask) 的行
            current_df = current_df[~exclude_mask].copy()
            
            # Debug info (optional)
            # print(f"Filtered out {exclude_mask.sum()} stores due to restricted code: {target_code}")

    # --- 通道筛选逻辑 ---
    # Yellow: Super Flagship, Flagship
    # Blue: Super Flagship, Flagship, Standard
    # Green: All
    
    valid_types = []
    if channel == "黄色":
        valid_types = ["超级旗舰店", "旗舰店", "大店"]
    elif channel == "蓝色":
        valid_types = ["超级旗舰店", "旗舰店", "大店", "中店","小店"]
    elif channel == "绿色":
        valid_types = ["超级旗舰店", "旗舰店", "大店", "中店","小店","成长店"]
    
    filtered_df = current_df[current_df["销售规模"].isin(valid_types)]
    counts = filtered_df["销售规模"].value_counts().to_dict()
    
    # Ensure all types are present in the dict with 0 if missing, for consistency
    all_types = ["超级旗舰店", "旗舰店", "大店", "中店","小店","成长店"]
    for t in all_types:
        if t not in counts:
            counts[t] = 0
            
    # Filter out types not in the channel (though value_counts handles this, we want to be explicit about what we return)
    return {k: v for k, v in counts.items() if k in valid_types}

def extract_manual_counts(row_data):
    """
    Extracts manual store counts from a row of data (dict or Series).
    Expected keys: "(自定义)超级旗舰店数", etc.
    """
    counts = {}
    mapping = {
        "(自定义)超级旗舰店数": "超级旗舰店",
        "(自定义)旗舰店数": "旗舰店",
        "(自定义)大店数": "大店",
        "(自定义)中店数": "中店",
        "(自定义)小店数": "小店",
        "(自定义)成长店数": "成长店"
    }
    
    for key, store_type in mapping.items():
        val = row_data.get(key)
        if pd.isna(val) or val == "":
            counts[store_type] = 0
        else:
            counts[store_type] = int(val)
            
    return counts