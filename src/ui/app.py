import streamlit as st
import pandas as pd
import base64
import os
import sys

# --- Path Setup ---
# 计算项目根目录绝对路径，确保在任何运行位置都能正确导入模块
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))

if project_root not in sys.path:
    sys.path.append(project_root)

from src.core.config_loader import load_config
from src.core.store_manager import load_store_master, calc_auto_counts, extract_manual_counts
from src.core.calculator import calculate_fee
from src.core.file_utils import read_excel_safe

# Page Config
st.set_page_config(page_title="新品铺货费计算器", page_icon="💰", layout="wide")

# Load Config
try:
    config_path = os.path.join(project_root, "config", "coefficients.yaml")
    config = load_config(config_path)
except Exception as e:
    st.error(f"无法加载配置文件: {e}")
    st.stop()

def main():
    st.title("💰 新品铺货费计算器")

    # --- Sidebar: 全局配置 ---
    st.sidebar.header("全局配置")
    
    store_master_path = os.path.join(project_root, "data", "store_master.xlsx")
    uploaded_master = st.sidebar.file_uploader("上传门店主数据 (覆盖默认)", type=["xlsx"])
    
    if uploaded_master:
        try:
            store_master_df = pd.read_excel(uploaded_master, engine='openpyxl')
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

    # --- Tab 1: 单品计算器 ---
    with tab1:
        with st.container(border=True):
            st.markdown("#### 📝 通道计算器 -- 输入信息")
            
            # 输入区域布局
            c1, c2 = st.columns(2)
            with c1:
                category = st.selectbox("新品大类", list(config["base_fees"].keys()))
            with c2:
                sku_count = st.number_input("同一供应商单次引进SKU数", min_value=1, value=1)
                
            c3, c4 = st.columns(2)
            with c3:
                return_policy = st.selectbox("退货条件", list(config["return_policy_coeffs"].keys()))
            with c4:
                payment = st.selectbox("付款方式", list(config["payment_coeffs"].keys()))
                
            c5, c6 = st.columns(2)
            with c5:
                cost_price = st.number_input("进价 (元)", min_value=0.0, value=10.0)
            with c6:
                gross_margin = st.number_input("预估成交综合毛利率 (%)", min_value=0.0, max_value=100.0, value=40.0)
                
            c7, c8 = st.columns(2)
            with c7:
                supplier_type = st.selectbox("供应商类型", list(config["supplier_type_coeffs"].keys()))
            with c8:
                pass  # 保留空列以保持对齐

            st.markdown("---")
            
            # 通道选择
            st.markdown("**通道选择**")
            channel_mode = st.radio(
                "通道模式",
                ["标准通道 (按黄/蓝/绿通道选择门店)", "自定义通道 (按标签选择门店)"],
                label_visibility="collapsed"
            )
            
            channel = "自定义"
            manual_counts = {}
            
            if "标准通道" in channel_mode:
                color_selection = st.radio(
                    "选择颜色",
                    ["🟡 黄色", "🔵 蓝色", "🟢 绿色"],
                    label_visibility="collapsed"
                )
                channel = color_selection.split(" ")[1]
            else:
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

        # 计算按钮
        if st.button("计算费用", type="primary", use_container_width=True):
            if store_master_df is None and channel != "自定义":
                st.error("请先加载门店主数据！")
            else:
                # 构造计算所需的数据字典
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
                
                if channel == "自定义":
                    for k, v in manual_counts.items():
                        row_data[f"(自定义){k}数"] = v

                try:
                    # 获取门店数量
                    if channel == "自定义":
                        store_counts = extract_manual_counts(row_data)
                    else:
                        store_counts = calc_auto_counts(store_master_df, channel)
                    
                    result = calculate_fee(row_data, store_counts, config)

                    # ==================== 输出区域：严格按照你的截图布局 ====================
                    st.markdown("### 通道计算器--输出信息")

                    # 绿色标题栏
                    st.markdown(
                        f"""
                        <div style="background-color: #1ABC9C; padding: 15px; border-radius: 8px 8px 0 0; 
                                    color: white; margin-bottom: 0;">
                            <h4 style="margin:0;">计算结果：{channel}通道</h4>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    # 带边框的内容卡片
                    with st.container(border=True):
                        st.markdown("**预估新品铺货费**")
                        
                        st.markdown(
                            f"**理论总新品铺货费 (元)**: <span style='font-size:1.2em; color:#333;'>{int(result['theoretical_fee']):,}</span>",
                            unsafe_allow_html=True
                        )
                        
                        st.markdown(
                            f"**折扣**: <span style='font-size:1.2em; color:#333;'>{result['discount_factor']:.2f}</span>",
                            unsafe_allow_html=True
                        )
                        
                        # 大红色重点结果
                        st.markdown(
                            f"""
                            <div style="margin: 30px 0 20px 0; font-size: 1.8em; color: #D32F2F; font-weight: bold;">
                                折后总新品铺货费 (元): {int(result['final_fee']):,}
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                        # 紧接着下方显示铺货门店明细表格
                        st.markdown("**铺货门店**")
                        
                        store_details_df = pd.DataFrame(
                            list(result['store_details'].items()),
                            columns=['销售规模', '门店数']
                        )
                        
                        st.dataframe(
                            store_details_df,
                            use_container_width=True,
                            hide_index=True
                        )
                        
                        # 门店总数说明
                        total_stores = sum(result['store_details'].values())
                        st.caption(f"计算池中的门店数量: {total_stores:,} (全集团)")

                    # 规则说明（保持在最下方）
                    with st.expander("规则说明"):
                        rule_pdf_path = os.path.join(project_root, "data", "rule_description.pdf")
                        if os.path.exists(rule_pdf_path):
                            with open(rule_pdf_path, "rb") as f:
                                base64_pdf = base64.b64encode(f.read()).decode('utf-8')
                            pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf"></iframe>'
                            st.markdown(pdf_display, unsafe_allow_html=True)
                        else:
                            st.info("暂无规则说明文档 (请在 data 目录下放置 rule_description.pdf)")

                except Exception as e:
                    st.error(f"计算出错: {e}")

    # --- Tab 2: 批量计算器（保持原有逻辑，仅小优化）---
    with tab2:
        st.header("批量费用计算")
        
        template_path = os.path.join(project_root, "data", "batch_template.xlsx")
        if os.path.exists(template_path):
            with open(template_path, "rb") as f:
                st.download_button("📥 下载导入模板", f, file_name="batch_template.xlsx")
        else:
            st.warning("未找到模板文件 (请先运行 setup_data.py 生成)")

        uploaded_batch = st.file_uploader("上传填写好的 Excel 文件", type=["xlsx"])
        
        if uploaded_batch and st.button("开始批量计算", type="primary"):
            if store_master_df is None:
                st.error("请先加载门店主数据（用于非自定义通道）！")
            else:
                try:
                    df = read_excel_safe(uploaded_batch)
                    results = []
                    logs = []
                    progress_bar = st.progress(0)

                    for index, row in df.iterrows():
                        row_dict = row.to_dict()
                        row_dict['channel'] = row_dict.get('铺货通道')

                        try:
                            if row_dict['channel'] == "自定义":
                                store_counts = extract_manual_counts(row_dict)
                            else:
                                store_counts = calc_auto_counts(store_master_df, row_dict['channel'])
                            
                            result = calculate_fee(row_dict, store_counts, config)
                            row_dict['计算结果费用'] = result['final_fee']
                            row_dict['费用说明'] = result['breakdown_str']
                        except Exception as e:
                            row_dict['计算结果费用'] = "Error"
                            row_dict['费用说明'] = str(e)
                            logs.append(f"Row {index+1} Error: {e}")
                        
                        results.append(row_dict)
                        progress_bar.progress((index + 1) / len(df))

                    result_df = pd.DataFrame(results)
                    st.dataframe(result_df, use_container_width=True)

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
                        with st.expander("错误日志"):
                            st.write(logs)

                except Exception as e:
                    st.error(f"处理文件失败: {e}")

if __name__ == "__main__":
    main()