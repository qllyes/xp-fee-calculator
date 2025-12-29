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
        channel: 
            - String: "黄色", "蓝色", "绿色", "自定义" (returns empty), 
                      or comma-separated types like "小店,成长店".
            - List: A list of store types e.g. ["小店", "成长店"].
        restricted_xp_code: (Optional) The xp_code string to check against store restrictions.
                            e.g., "5". If a store has "5" in its restricted list, it will be excluded.
    
    Returns:
        dict: A dictionary of {store_type: count}.
    """
    # 如果是纯手动模式的标记，直接返回空，交由手动提取函数处理
    if channel == "自定义":
        return {} 
    
    # --- 1. 解析需要筛选的门店类型 (valid_types) ---
    valid_types = []
    
    if isinstance(channel, list):
        # 情况A: 直接传入了列表 (来自UI的多选框)
        valid_types = channel
    elif isinstance(channel, str):
        # 情况B: 传入了预定义颜色通道或逗号分隔字符串
        if channel == "黄色":
            valid_types = ["超级旗舰店", "旗舰店", "大店"]
        elif channel == "蓝色":
            valid_types = ["超级旗舰店", "旗舰店", "大店", "中店", "小店"]
        elif channel == "绿色":
            valid_types = ["超级旗舰店", "旗舰店", "大店", "中店", "小店", "成长店"]
        else:
            # 尝试解析 "小店,成长店" 这种格式 (为批量导入预留灵活性)
            # 替换中文逗号并分割
            parts = channel.replace("，", ",").split(",")
            valid_types = [p.strip() for p in parts if p.strip()]
    
    # 如果解析不出有效类型，返回空
    if not valid_types:
        return {}

    # --- 2. 受限门店过滤逻辑 (Restricted Store Filtering) ---
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
                # 兼容中文逗号
                val_str = str(cell_value).replace("，", ",")
                codes = [c.strip() for c in val_str.split(',')]
                
                # 如果目标代码在列表中，则该门店受限，需要剔除
                return target_code in codes

            # 找出需要剔除的行 (True 表示需要剔除)
            exclude_mask = current_df["受限批文分类编码"].apply(is_store_excluded)
            
            # 保留 不需要剔除 (~exclude_mask) 的行
            current_df = current_df[~exclude_mask].copy()

    # --- 3. 统计指定类型的门店数量 ---
    # 筛选出属于 valid_types 的门店
    filtered_df = current_df[current_df["销售规模"].isin(valid_types)]
    counts = filtered_df["销售规模"].value_counts().to_dict()
    
    # 补全字典，确保所有可能的Key都存在(即使数量为0)，方便前端展示
    all_possible_types = ["超级旗舰店", "旗舰店", "大店", "中店", "小店", "成长店"]
    final_counts = {}
    
    # 这里我们只返回用户选中的那些类型，未选中的不返回或设为0
    # 但为了UI统一展示，建议只保留在 valid_types 里的 key
    for t in valid_types:
        final_counts[t] = counts.get(t, 0)
            
    return final_counts

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
            try:
                counts[store_type] = int(val)
            except ValueError:
                counts[store_type] = 0
            
    return counts