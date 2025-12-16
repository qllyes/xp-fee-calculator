import pandas as pd
import pymysql
import os
from sqlalchemy import create_engine

# 异步操作脚本，不在main.py内，
# 门店基础表，取上月最后一天的门店表来做门店基础表

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
SELECT DISTINCT 
    t1.shop_code AS `门店sapid`,
    t1.lev3_org_name AS `DHR战区`,
    t1.lev3_org_name_xp AS `提报战区`,
    t1.sales_scan_name AS `销售规模`,
    t2.forbid_goods_aprl_types_code AS `受限批文分类编码`,
    t2.forbid_goods_aprl_types_name AS `受限批文分类名称`
FROM xp_shops_info_qll_dfp t1
LEFT JOIN mid_shop_med_insu_forbid_sale_goodstype_dfn t2
    ON t1.shop_code = t2.shop_code
WHERE t1.shop_age_and_type_code NOT IN ('5', '6', '7', '11')
  AND t1.busi_ascr_code IN ('1', '4')
  AND t1.dt = '2025-12-15'
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
        output_path = os.path.join(current_dir, "data", "store_master.xlsx")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        print(f"💾 Saving to {output_path}...")
        df.to_excel(output_path, index=False, engine='openpyxl')
        
        print("🎉 Sync completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during sync: {e}")

if __name__ == "__main__":
    sync_data()