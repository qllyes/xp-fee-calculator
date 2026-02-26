import pandas as pd
import os
from src.core.file_utils import read_excel_safe


def load_store_master(path="data/store_master.xlsx"):
    return pd.read_excel(path)


def load_xp_mapping(path="data/处方类别与批文分类表.xlsx"):
    """
    加载处方类别与批文分类的映射表。
    只支持读取 '处方类别' (如 10-处方药) 作为 Key，用于前端规范展示与后台受限剔除校验。
    返回一个字典: {'10-处方药': '13', ...}
    """
    if not os.path.exists(path):
        print(f"Warning: Mapping file not found at {path}")
        return {}
    
    try:
        df = read_excel_safe(path)
        # 确保必需的列存在
        required_cols = ['处方类别', '批文分类编码']
        if not all(col in df.columns for col in required_cols):
            print(f"Warning: Mapping file columns mismatch. Expected {required_cols}")
            return {}

        # 清洗数据：去除空值
        df = df.dropna(subset=['批文分类编码'])
        
        mapping = {}
        for _, row in df.iterrows():
            target_code = str(row['批文分类编码']).strip()
            
            # 处理 '处方类别' (如: 10-处方药)
            val_a = str(row['处方类别']).strip()
            if val_a and val_a.lower() != 'nan':
                mapping[val_a] = target_code
            
        return mapping
    except Exception as e:
        print(f"Error loading xp mapping: {e}")
        return {}


def load_store_blacklist(path: str = "data/新品费剔除门店黑名单.xlsx") -> pd.DataFrame | None:
    """
    加载门店黑名单文件。

    文件结构: 两列 ['门店sapid', '处方类别or新品大类']
    
    Returns:
        DataFrame 或 None（文件不存在时）
    """
    if not os.path.exists(path):
        print(f"Warning: Blacklist file not found at {path}")
        return None

    try:
        df = read_excel_safe(path, dtype_spec={"门店sapid": str})
        required_cols = ["门店sapid", "处方类别or新品大类"]
        if not all(col in df.columns for col in required_cols):
            print(f"Warning: Blacklist file columns mismatch. Expected {required_cols}, got {list(df.columns)}")
            return None
        # 清洗：去除空值、统一类型
        df = df.dropna(subset=required_cols)
        df["门店sapid"] = df["门店sapid"].astype(str).str.strip()
        df["处方类别or新品大类"] = df["处方类别or新品大类"].astype(str).str.strip()
        return df
    except Exception as e:
        print(f"Error loading store blacklist: {e}")
        return None


def _get_blacklisted_sapids(
    blacklist_df: pd.DataFrame | None,
    selected_xp_category: str | None,
    category: str | None,
) -> set[str]:
    """
    根据前端选择的处方类别和新品大类，从黑名单中提取需要剔除的门店sapid集合。

    匹配规则：模糊包含匹配。
    黑名单中的类别值（如 '处方药'）只要被包含在前端值（如 '10-处方药'）中，即视为命中。

    Args:
        blacklist_df: 黑名单 DataFrame
        selected_xp_category: 前端选择的处方类别 (如 '10-处方药')
        category: 前端选择的新品大类 (如 '养生中药')

    Returns:
        需要剔除的门店sapid集合
    """
    if blacklist_df is None or blacklist_df.empty:
        return set()

    # 收集前端有效值
    front_values: list[str] = []
    if selected_xp_category and str(selected_xp_category).strip().lower() != "nan":
        front_values.append(str(selected_xp_category).strip())
    if category and str(category).strip().lower() != "nan":
        front_values.append(str(category).strip())

    if not front_values:
        return set()

    # 获取黑名单中所有不重复的类别
    blacklist_categories = blacklist_df["处方类别or新品大类"].unique()

    # 模糊匹配：黑名单值 是否被包含在 任一前端值中
    matched_categories = [
        bl_cat
        for bl_cat in blacklist_categories
        if any(bl_cat in fv for fv in front_values)
    ]

    if not matched_categories:
        return set()

    return set(
        blacklist_df.loc[
            blacklist_df["处方类别or新品大类"].isin(matched_categories), "门店sapid"
        ]
    )


def calc_auto_counts(
    store_master_df,
    channel,
    restricted_xp_code=None,
    war_zone=None,
    filters=None,
    blacklist_df: pd.DataFrame | None = None,
    selected_xp_category: str | None = None,
    category: str | None = None,
):
    """
    根据选择的通道、处方限制、战区和额外过滤器计算门店数量。
    
    Args:
        store_master_df: 门店主数据 DataFrame。
        channel: 
            - 字符串: "超级旗舰店", "旗舰店及以上", "全量门店", "自定义" 等。
            - 列表: 门店类型列表，例如 ["小店", "成长店"]。
        restricted_xp_code: (可选) 用于检查门店限制的 xp_code 字符串。
        war_zone: (可选) 战区名称。
        filters: (可选) 额外过滤器的字典。
        blacklist_df: (可选) 门店黑名单 DataFrame。
        selected_xp_category: (可选) 前端选择的处方类别，用于黑名单匹配。
        category: (可选) 前端选择的新品大类，用于黑名单匹配。
    
    Returns:
        dict: {门店类型: 数量} 的字典。
    """
    
    # --- 1. 解析需要筛选的门店类型 (valid_types) ---
    valid_types = []
    
    if isinstance(channel, list):
        valid_types = channel
    elif isinstance(channel, str):
        if channel == "自定义":
            # 如果是自定义且有过滤器，默认全选所有类型，后续通过 filters['销售规模'] 进一步筛选
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

    # 通用过滤器逻辑
    if filters:
        for col, val in filters.items():
            if not val or val == "全部" or col == "销售规模": # 销售规模已在 valid_types 处理
                continue
            
            if col not in current_df.columns:
                continue

            # 特殊处理：客流商圈 (逗号分隔的字符串包含逻辑)
            if col == "客流商圈":
                if isinstance(val, list) and val:
                    def has_intersection(cell_val):
                        if pd.isna(cell_val): return False
                        store_districts = set(str(cell_val).replace("，", ",").split(","))
                        return not set(val).isdisjoint(store_districts)
                    
                    current_df = current_df[current_df[col].apply(has_intersection)]
            
            # 处理布尔/枚举值 (是/否)
            elif isinstance(val, str) and val in ["是", "否"]:
                current_df = current_df[current_df[col].astype(str).str.strip() == val]
            
            # 处理列表多选 (isin)
            elif isinstance(val, list):
                current_df = current_df[current_df[col].isin(val)]

    # 战区过滤逻辑
    if war_zone and war_zone != "全集团":
        if "提报战区" in current_df.columns:
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

    # --- 3.5 门店黑名单过滤逻辑 ---
    blacklisted_sapids = _get_blacklisted_sapids(
        blacklist_df, selected_xp_category, category
    )
    if blacklisted_sapids and "门店sapid" in current_df.columns:
        current_df = current_df[
            ~current_df["门店sapid"].astype(str).str.strip().isin(blacklisted_sapids)
        ]

    # --- 4. 统计指定类型的门店数量 ---
    filtered_df = current_df[current_df["销售规模"].isin(valid_types)]
    counts = filtered_df["销售规模"].value_counts().to_dict()
    
    final_counts = {}
    for t in valid_types:
        final_counts[t] = counts.get(t, 0)
            
    return final_counts

def extract_manual_counts(row_data):
    """
    从数据行中提取手动输入的门店数量。
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