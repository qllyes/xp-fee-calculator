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

def calc_auto_counts(store_master_df, channel, restricted_xp_code=None, war_zone=None, filters=None):
    """
    Calculates store counts based on the selected channel, prescription restrictions, war zone, and extra filters.
    
    Args:
        store_master_df: DataFrame of the store master data.
        channel: 
            - String: "黄色", "蓝色", "绿色", "自定义" (returns empty if no filters), 
                      or comma-separated types like "小店,成长店".
            - List: A list of store types e.g. ["小店", "成长店"].
        restricted_xp_code: (Optional) The xp_code string to check against store restrictions.
        war_zone: (Optional) The war zone name to filter by.
        filters: (Optional) Dictionary of extra filters. 
                 Keys match column names in store_master_df.
                 Values can be:
                 - List: for isin() filtering (OR logic within list).
                 - String "是"/"否": for boolean filtering.
                 - String "全部": ignored.
    
    Returns:
        dict: A dictionary of {store_type: count}.
    """
    # 如果是纯手动模式的标记且没有过滤器，直接返回空
    if channel == "自定义" and not filters:
        return {} 
    
    # --- 1. 解析需要筛选的门店类型 (valid_types) ---
    valid_types = []
    
    if isinstance(channel, list):
        valid_types = channel
    elif isinstance(channel, str):
        if channel == "自定义":
            # 如果是自定义且有过滤器，默认全选所有类型，后续通过 filters['销售规模'] 进一步筛选
            # 但通常前端会把销售规模放在 filters 里传进来，或者 channel 本身就是 list
            # 这里为了兼容，如果 filters 里有销售规模，就用 filters 里的
            if filters and '销售规模' in filters and filters['销售规模']:
                valid_types = filters['销售规模']
            else:
                valid_types = ["超级旗舰店", "旗舰店", "大店", "中店", "小店", "成长店"]
        elif channel == "超级旗舰店":
            valid_types = ["超级旗舰店"]
        elif channel == "旗舰店及以上":
            valid_types = ["超级旗舰店", "旗舰店"]
        elif channel == "大店及以上":
            valid_types = ["超级旗舰店", "旗舰店", "大店"]
        elif channel == "中店及以上":
            valid_types = ["超级旗舰店", "旗舰店", "大店", "中店"]
        elif channel == "小店及以上":
            valid_types = ["超级旗舰店", "旗舰店", "大店", "中店", "小店"]
        elif channel == "全量门店":
            valid_types = ["超级旗舰店", "旗舰店", "大店", "中店", "小店", "成长店"]
        else:
            parts = channel.replace("，", ",").split(",")
            valid_types = [p.strip() for p in parts if p.strip()]
    
    if not valid_types:
        return {}

    # --- 2. 筛选逻辑开始 ---
    current_df = store_master_df.copy()

    # [新增] 通用过滤器逻辑
    if filters:
        for col, val in filters.items():
            if not val or val == "全部" or col == "销售规模": # 销售规模已在 valid_types 处理
                continue
            
            if col not in current_df.columns:
                continue

            # 特殊处理：客流商圈 (逗号分隔的字符串包含逻辑)
            if col == "客流商圈":
                # val 是用户选中的商圈列表，如 ['社区店', '医院店']
                # 门店的商圈字段可能是 "社区店,其他"
                # 逻辑：只要门店的商圈包含 val 中的任意一个，就保留
                if isinstance(val, list) and val:
                    def has_intersection(cell_val):
                        if pd.isna(cell_val): return False
                        # 分割门店的商圈字符串
                        store_districts = set(str(cell_val).replace("，", ",").split(","))
                        # 检查是否有交集
                        return not set(val).isdisjoint(store_districts)
                    
                    current_df = current_df[current_df[col].apply(has_intersection)]
            
            # 处理布尔/枚举值 (是/否)
            elif isinstance(val, str) and val in ["是", "否"]:
                # 假设 Excel 中存储的是 "是"/"否" 或者 1/0，这里需根据实际数据调整
                # 根据截图，看起来是中文 "是"/"否" 或者空值
                # 尝试匹配字符串
                current_df = current_df[current_df[col].astype(str).str.strip() == val]
            
            # 处理列表多选 (isin)
            elif isinstance(val, list):
                current_df = current_df[current_df[col].isin(val)]

    # [原有] 战区过滤逻辑
    if war_zone and war_zone != "全集团":
        if "提报战区" in current_df.columns:
            # 支持多选战区 (如果 war_zone 是列表)
            if isinstance(war_zone, list):
                current_df = current_df[current_df["提报战区"].isin(war_zone)]
            else:
                current_df = current_df[current_df["提报战区"] == war_zone]

    # --- 3. 受限门店过滤逻辑 ---
    if restricted_xp_code is not None and "受限批文分类编码" in current_df.columns:
        target_code = str(restricted_xp_code).strip()
        if target_code and target_code.lower() != 'nan':
            def is_store_excluded(cell_value):
                if pd.isna(cell_value) or str(cell_value).strip() == "":
                    return False
                val_str = str(cell_value).replace("，", ",")
                codes = [c.strip() for c in val_str.split(',')]
                return target_code in codes

            exclude_mask = current_df["受限批文分类编码"].apply(is_store_excluded)
            current_df = current_df[~exclude_mask]

    # --- 4. 统计指定类型的门店数量 ---
    filtered_df = current_df[current_df["销售规模"].isin(valid_types)]
    counts = filtered_df["销售规模"].value_counts().to_dict()
    
    final_counts = {}
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