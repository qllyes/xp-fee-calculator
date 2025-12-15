import pandas as pd

def load_store_master(path="data/store_master.xlsx"):
    return pd.read_excel(path)

def calc_auto_counts(store_master_df, channel):
    """
    Calculates store counts based on the selected channel.
    Returns a dictionary of {store_type: count}.
    """
    if channel == "自定义":
        return {} # Should be handled by manual extraction
    
    # Define channel logic
    # Yellow: Super Flagship, Flagship
    # Blue: Super Flagship, Flagship, Standard
    # Green: All
    
    valid_types = []
    if channel == "黄色":
        valid_types = ["超级旗舰店", "旗舰店"]
    elif channel == "蓝色":
        valid_types = ["超级旗舰店", "旗舰店", "标准店"]
    elif channel == "绿色":
        valid_types = ["超级旗舰店", "旗舰店", "标准店", "普通店"]
    
    filtered_df = store_master_df[store_master_df["门店类型"].isin(valid_types)]
    counts = filtered_df["门店类型"].value_counts().to_dict()
    
    # Ensure all types are present in the dict with 0 if missing, for consistency
    all_types = ["超级旗舰店", "旗舰店", "标准店", "普通店"]
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
        "(自定义)标准店数": "标准店",
        "(自定义)普通店数": "普通店"
    }
    
    for key, store_type in mapping.items():
        val = row_data.get(key)
        if pd.isna(val) or val == "":
            counts[store_type] = 0
        else:
            counts[store_type] = int(val)
            
    return counts
