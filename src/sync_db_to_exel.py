import pandas as pd
import pymysql
import os
from sqlalchemy import create_engine
import json

# 异步操作脚本，不在main.py内，
# 门店基础表，取上月最后一天的门店表来做门店基础表，
# 从数据库加载到本地excel，提高前端响应速度

# --- Database Configuration ---
DB_CONFIG = {
    "host": "10.243.0.221",
    "port": 3306,
    "user": "xinpin",
    "password": "xinpin",
    "database": "new_goods_manage"
}

# --- SQL Query ---
SQL_QUERY = """
SELECT  shop_code                    AS `门店sapid`
       ,lev3_org_name                AS `DHR战区`
       ,lev3_org_name_xp             AS `提报战区`
       ,sales_scan_name              AS `销售规模`
       ,forbid_goods_aprl_types_code AS `受限批文分类编码`
       ,forbid_goods_aprl_types_name AS `受限批文分类名称`
       ,shop_update_time             AS `门店表更新时间`
       ,company_name                 AS `省公司`
       ,city_name                    AS `城市`
       ,prov_name                    AS `省份`
       ,shop_age_and_type_name       AS `店龄店型`
       ,busi_district_type_name      AS `客流商圈`
       ,admin_area_name              AS `行政区划等级`
       ,shop_o2o_type                AS `公域O2O店型`
       ,is_focus_shop_o2o            AS `是否O2O门店`
       ,is_med_insu_shop             AS `是否医保店`
       ,is_op_coor_shop              AS `是否统筹店`
FROM xp_dist_fee_shop_tag_dfp
WHERE dt = LAST_DAY(DATE_SUB(CURDATE(), INTERVAL 1 MONTH)) 
"""

def sync_data():
    """
    Connects to MySQL, executes the query, and saves the result to an Excel file.
    """
    print("🚀 Starting database sync...")
    
    # 1. Create SQLAlchemy Engine
    connection_str = f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
    
    try:
        engine = create_engine(connection_str)
        
        # 2. Execute Query & Load into DataFrame
        print("📥 Fetching data from MySQL...")
        df = pd.read_sql(SQL_QUERY, engine)
        
        # 3. Data Transformation (Optional)
        row_count = len(df)
        print(f"✅ Fetched {row_count} rows.")

        # 4. Save to Excel
        # Ensure the data directory exists
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        data_dir = os.path.join(current_dir, "data")
        os.makedirs(data_dir, exist_ok=True)
        
        # 表1：门店信息表
        output_path = os.path.join(data_dir, "store_master.xlsx")
        print(f"💾 Saving to {output_path}...")
        df.to_excel(output_path, index=False, engine='openpyxl')
        
        # 5. 表2：Generate Region Map (Unique combinations of Company/Province/City)
        region_map_path = os.path.join(data_dir, "region_map.xlsx")
        print(f"💾 Generating region map to {region_map_path}...")
        region_df = df[['省公司', '省份', '城市']].dropna().drop_duplicates().sort_values(['省公司', '省份', '城市'])
        region_df.to_excel(region_map_path, index=False, engine='openpyxl')
        
        # 6. Generate Dimension Metadata (JSON for UI dropdowns)
        metadata_path = os.path.join(data_dir, "dim_metadata.json")
        print(f"💾 Generating dimension metadata to {metadata_path}...")
        
        # 表3：自定义筛选条件字段都存为一个元数据
        metadata = {
            "店龄店型": sorted(df["店龄店型"].dropna().unique().tolist()),
            "行政区划等级": sorted(df["行政区划等级"].dropna().unique().tolist()),
            "公域O2O店型": sorted(df["公域O2O店型"].dropna().unique().tolist()),
            # 特殊处理：客流商圈 (逗号分隔)
            "客流商圈": sorted(list(set([
                p.strip() 
                for val in df["客流商圈"].dropna().astype(str) 
                for p in val.replace("，", ",").split(",") if p.strip()
            ]))),
            "销售规模": ["超级旗舰店", "旗舰店", "大店", "中店", "小店", "成长店"],
            # 新增：业务属性布尔值提取
            "是否医保店": sorted(df["是否医保店"].dropna().unique().tolist()),
            "是否O2O门店": sorted(df["是否O2O门店"].dropna().unique().tolist()),
            "是否统筹店": sorted(df["是否统筹店"].dropna().unique().tolist()),
            "更新时间": str(df["门店表更新时间"].iloc[0]) if "门店表更新时间" in df.columns else "未知"
        }
        
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        print("🎉 Sync completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during sync: {e}")

if __name__ == "__main__":
    sync_data()
