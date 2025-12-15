import streamlit as st
import pandas as pd
import base64
import os
import sys

# --- Path Setup ---
# Calculate project root absolute path (2 levels up from src/ui/app.py)
# This ensures paths work regardless of where the command is run from
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))

# Add project root to python path to allow imports from src
if project_root not in sys.path:
    sys.path.append(project_root)

from src.core.config_loader import load_config
from src.core.store_manager import load_store_master, calc_auto_counts, extract_manual_counts
from src.core.calculator import calculate_fee

# Page Config
st.set_page_config(page_title="新品铺货费计算器", page_icon="💰", layout="wide")

# Load Config
try:
    # Use absolute path for config file
    config_path = os.path.join(project_root, "config", "coefficients.yaml")
    config = load_config(config_path)
except Exception as e:
    st.error(f"无法加载配置文件: {e}")
    st.stop()

def main():
    st.title("💰 新品铺货费计算器")

    # --- Sidebar ---
    st.sidebar.header("全局配置")
    
    # Store Master Loader
    # Use absolute path for data file
    store_master_path = os.path.join(project_root, "data", "store_master.xlsx")
    uploaded_master = st.sidebar.file_uploader("上传门店主数据 (覆盖默认)", type=["xlsx"])
    
    if uploaded_master:
        try:
            store_master_df = pd.read_excel(uploaded_master)
            st.sidebar.success(f"已加载: {len(store_master_df)} 家门店")
        except Exception as e:
            st.sidebar.error(f"加载失败: {e}")
            store_master_df = None
    else:
        if os.path.exists(store_master_path):
            store_master_df = load_store_master(store_master_path)
            st.sidebar.info(f"使用默认数据: {len(store_master_df)} 家门店")
        else:
            st.sidebar.warning(f"未找到默认门店数据: {store_master_path}")
            store_master_df = None

    # --- Tabs ---
    tab1, tab2 = st.tabs(["📝 单品计算器", "📂 批量计算器"])

    # --- Tab 1: Single Calculator ---
    with tab1:
        with st.container(border=True):
            st.markdown("#### 📝 通道计算器 -- 输入信息")
            
            # Row 1
            c1, c2 = st.columns(2)
            with c1:
                category = st.selectbox("新品大类", list(config["base_fees"].keys()))
            with c2:
                sku_count = st.number_input("同一供应商单次引进SKU数", min_value=1, value=1)
                
            # Row 2
            c3, c4 = st.columns(2)
            with c3:
                return_policy = st.selectbox("退货条件", list(config["return_policy_coeffs"].keys()))
            with c4:
                payment = st.selectbox("付款方式", list(config["payment_coeffs"].keys()))
                
            # Row 3
            c5, c6 = st.columns(2)
            with c5:
                cost_price = st.number_input("进价 (元)", min_value=0.0, value=10.0)
            with c6:
                gross_margin = st.number_input("预估成交综合毛利率 (%)", min_value=0.0, max_value=100.0, value=40.0)
                
            # Row 4
            c7, c8 = st.columns(2)
            with c7:
                supplier_type = st.selectbox("供应商类型", list(config["supplier_type_coeffs"].keys()))
            with c8:
                pass # Empty for balance or future field
                
            st.markdown("---")
            
            # Channel Selection Section
            st.markdown("**通道选择**")
            channel_mode = st.radio(
                "通道模式", 
                ["标准通道 (按黄/蓝/绿通道选择门店)", "自定义通道 (按标签选择门店)"],
                label_visibility="collapsed"
            )
            
            channel = "自定义" # Default
            manual_counts = {}
            
            if "标准通道" in channel_mode:
                st.write("手动选择三色通道:")
                color_selection = st.radio(
                    "选择颜色",
                    ["🟡 黄色", "🔵 蓝色", "🟢 绿色"],
                    label_visibility="collapsed"
                )
                channel = color_selection.split(" ")[1] # Extract "黄色" from "🟡 黄色"
                
            else: # Custom Channel
                channel = "自定义"
                st.caption("请输入各类型门店数量:")
                cc1, cc2, cc3, cc4 = st.columns(4)
                with cc1:
                    manual_counts["超级旗舰店"] = st.number_input("超级旗舰", min_value=0, key="custom_super")
                with cc2:
                    manual_counts["旗舰店"] = st.number_input("旗舰", min_value=0, key="custom_flag")
                with cc3:
                    manual_counts["标准店"] = st.number_input("标准", min_value=0, key="custom_std")
                with cc4:
                    manual_counts["普通店"] = st.number_input("普通", min_value=0, key="custom_norm")

        if st.button("计算费用", type="primary", use_container_width=True):
            if store_master_df is None and channel != "自定义":
                st.error("请先加载门店主数据！")
            else:
                # Prepare Data
                row_data = {
                    "商品品类": category,
                    "SKU数": sku_count,
                    "channel": channel,
                    "预估毛利率(%)": gross_margin,
                    "付款方式": payment,
                    "供应商类型": supplier_type,
                    "进价": cost_price,
                    "退货条件": return_policy
                }
                
                # Merge manual counts if custom
                if channel == "自定义":
                    for k, v in manual_counts.items():
                        row_data[f"(自定义){k}数"] = v
                
                # Calculate
                try:
                    if channel == "自定义":
                        store_counts = extract_manual_counts(row_data)
                    else:
                        store_counts = calc_auto_counts(store_master_df, channel)
                    
                    result = calculate_fee(row_data, store_counts, config)
                    
                    # --- Output Section ---
                    st.markdown("### 通道计算器--输出信息")
                    
                    # Green Header
                    channel_color_map = {
                        "黄色": "#FFD700", # Gold
                        "蓝色": "#1E90FF", # DodgerBlue
                        "绿色": "#2E8B57", # SeaGreen
                        "自定义": "#808080" # Grey
                    }
                    bg_color = "#1ABC9C" # The specific green from the image (approx)
                    
                    # Generate Table HTML first
                    store_details_df = pd.DataFrame(
                        list(result['store_details'].items()), 
                        columns=['销售规模', '门店数']
                    )
                    table_html = store_details_df.to_html(
                        index=False, 
                        classes='table table-bordered', 
                        border=0, 
                        justify='left'
                    ).replace('\n', '') # Remove newlines to prevent Markdown issues
                    
                    # Construct HTML string WITHOUT indentation to prevent Markdown code block interpretation
                    html_content = f"""
<div style="background-color: {bg_color}; padding: 10px; border-radius: 5px 5px 0 0; color: white;">
    <h4 style="margin:0;">计算结果：{channel}通道</h4>
</div>
<div style="border: 1px solid #ddd; border-top: none; padding: 20px; border-radius: 0 0 5px 5px;">
    <p style="color: gray; margin-bottom: 5px;">预估新品铺货费</p>
    <div style="margin-bottom: 15px;">
        <span style="font-weight: bold; font-size: 1.1em; color: #555;">理论总新品铺货费 (元)：</span>
        <span style="font-weight: bold; font-size: 1.1em; color: #333;">{int(result['theoretical_fee'])}</span>
    </div>
    <div style="margin-bottom: 15px;">
        <span style="font-weight: bold; font-size: 1.1em; color: #555;">折扣：</span>
        <span style="font-weight: bold; font-size: 1.1em; color: #333;">{result['discount_factor']:.2f}</span>
    </div>
    <div style="margin-bottom: 20px;">
        <span style="font-weight: bold; font-size: 1.5em; color: #555;">折后总新品铺货费 (元)：</span>
        <span style="font-weight: bold; font-size: 1.8em; color: #D32F2F;">{int(result['final_fee'])}</span>
    </div>
    <p style="color: gray; margin-bottom: 10px;">铺货门店</p>
    {table_html}
    <div style="margin-top: 10px; color: gray;">
        计算池中的门店数量: {sum(result['store_details'].values())} (全集团)
    </div>
</div>
"""
                    st.markdown(html_content, unsafe_allow_html=True)
                    
                    # Debug/Detailed breakdown (Hidden by default but available)
                    with st.expander("规则说明"):
                        rule_pdf_path = os.path.join(project_root, "data", "rule_description.pdf")
                        if os.path.exists(rule_pdf_path):
                            with open(rule_pdf_path, "rb") as f:
                                base64_pdf = base64.b64encode(f.read()).decode('utf-8')
                            # Embedding PDF in HTML
                            pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf"></iframe>'
                            st.markdown(pdf_display, unsafe_allow_html=True)
                        else:
                            st.info("暂无规则说明文档 (请在 data 目录下放置 rule_description.pdf)")
                        
                except Exception as e:
                    st.error(f"计算出错: {e}")

    # --- Tab 2: Batch Calculator ---
    with tab2:
        st.header("批量费用计算")
        
        # Template Download
        # Use absolute path for template file
        template_path = os.path.join(project_root, "data", "batch_template.xlsx")
        
        if os.path.exists(template_path):
            with open(template_path, "rb") as f:
                st.download_button("📥 下载导入模板", f, file_name="batch_template.xlsx")
        else:
            st.warning("未找到模板文件 (请先运行 setup_data.py 生成)")
            
        uploaded_batch = st.file_uploader("上传填写好的 Excel 文件", type=["xlsx"])
        
        if uploaded_batch and st.button("开始批量计算"):
            if store_master_df is None:
                st.error("请先加载门店主数据（用于非自定义通道）！")
            else:
                try:
                    df = pd.read_excel(uploaded_batch)
                    results = []
                    logs = []
                    
                    progress_bar = st.progress(0)
                    
                    for index, row in df.iterrows():
                        row_dict = row.to_dict()
                        # Map '铺货通道' to 'channel' for logic compatibility
                        row_dict['channel'] = row_dict.get('铺货通道')
                        
                        try:
                            if row_dict['channel'] == "自定义":
                                store_counts = extract_manual_counts(row_dict)
                            else:
                                store_counts = calc_auto_counts(store_master_df, row_dict['channel'])
                            
                            result = calculate_fee(row_dict, store_counts, config)
                            
                            row_dict['计算结果费用'] = result['final_fee']
                            row_dict['费用说明'] = result['breakdown_str']
                            results.append(row_dict)
                            
                        except Exception as e:
                            row_dict['计算结果费用'] = "Error"
                            row_dict['费用说明'] = str(e)
                            results.append(row_dict)
                            logs.append(f"Row {index+1} Error: {e}")
                        
                        progress_bar.progress((index + 1) / len(df))
                        
                    # Result DF
                    result_df = pd.DataFrame(results)
                    st.dataframe(result_df)
                    
                    # Download
                    # Convert to bytes
                    # We need to save to a buffer
                    from io import BytesIO
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        result_df.to_excel(writer, index=False)
                    
                    st.download_button(
                        "📤 导出计算结果", 
                        output.getvalue(), 
                        file_name="calculation_results.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    
                    if logs:
                        st.warning("部分行计算出错，请检查导出文件或下方日志")
                        st.write(logs)
                        
                except Exception as e:
                    st.error(f"处理文件失败: {e}")

if __name__ == "__main__":
    main()