import streamlit as st
import pandas as pd
import base64
import os
import sys
from io import BytesIO
from datetime import datetime

# --- Path Setup ---
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
                pass

            st.markdown("---")
            
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

        if st.button("计算费用", type="primary", use_container_width=True):
            if store_master_df is None and channel != "自定义":
                st.error("请先加载门店主数据！")
            else:
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
                    if channel == "自定义":
                        store_counts = extract_manual_counts(row_data)
                    else:
                        store_counts = calc_auto_counts(store_master_df, channel)
                    
                    result = calculate_fee(row_data, store_counts, config)

                    st.markdown("### 通道计算器--输出信息")

                    st.markdown(
                        f"""
                        <div style="background-color: #1ABC9C; padding: 15px; border-radius: 8px 8px 0 0; 
                                    color: white; margin-bottom: 0;">
                            <h4 style="margin:0;">计算结果：{channel}通道</h4>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

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
                        
                        st.markdown(
                            f"""
                            <div style="margin: 30px 0 20px 0; font-size: 1.8em; color: #D32F2F; font-weight: bold;">
                                折后总新品铺货费 (元): {int(result['final_fee']):,}
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

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
                        
                        total_stores = sum(result['store_details'].values())
                        st.caption(f"计算池中的门店数量: {total_stores:,} (全集团)")

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

    # --- Tab 2: 批量计算器（结果仅预览前5条）---
    with tab2:
        st.header("📂 批量费用计算")
        st.markdown(
    "<p style='color: gray; font-size: 0.95em; margin-top: -10px; margin-bottom: 20px;'>"
    "快速为多款新品一次性计算铺货费用，支持黄色/蓝色/绿色/自定义通道混合计算"
    "</p>",
    unsafe_allow_html=True
)

        with st.expander("📥 需要模板？点这里下载（可选）", expanded=False):
            template_path = os.path.join(project_root, "data", "batch_template.xlsx")
            if os.path.exists(template_path):
                with open(template_path, "rb") as f:
                    st.download_button(
                        "下载导入模板",
                        f,
                        file_name="新品铺货费_批量模板.xlsx",
                        use_container_width=True,
                        type="primary"
                    )
                #st.info("💡 如果你已有填写好的文件，可直接上传并计算。")
            else:
                st.warning("未找到模板文件")

        st.markdown("---")

        st.markdown("#### 📤 上传批量文件")
        uploaded_batch = st.file_uploader(
            "支持Excel 文件（.xlsx 格式）",
            type=["xlsx"],
            help="上传后即可一键计算"
        )

        if uploaded_batch:
            st.markdown("#### 🚀 开始计算")
            if st.button("开始批量计算", type="primary", use_container_width=True):
                if store_master_df is None:
                    st.error("❌ 请先在左侧边栏加载门店主数据！")
                else:
                    try:
                        df = read_excel_safe(uploaded_batch)

                        with st.spinner("正在批量计算，请稍等..."):
                            results = []
                            logs = []
                            progress_bar = st.progress(0)
                            status_text = st.empty()

                            for index, row in df.iterrows():
                                status_text.text(f"处理中：第 {index + 1}/{len(df)} 行 - {row.get('商品名称', '未知商品')}")
                                
                                row_dict = row.to_dict()

                                try:
                                    channel_name = row_dict.get('铺货通道')
                                    if channel_name == "自定义":
                                        store_counts = extract_manual_counts(row_dict)
                                    else:
                                        store_counts = calc_auto_counts(store_master_df, channel_name)
                                    
                                    result = calculate_fee(row_dict, store_counts, config)

                                    row_dict['理论总新品铺货费 (元)'] = int(result['theoretical_fee'])
                                    row_dict['折扣'] = result['discount_factor']
                                    row_dict['折后总新品铺货费 (元)'] = int(result['final_fee'])

                                    store_desc = []
                                    for store_type, count in result['store_details'].items():
                                        if count > 0:
                                            store_desc.append(f"{store_type}: {count}")
                                    row_dict['铺货门店数量'] = ", ".join(store_desc) if store_desc else "无铺货门店"

                                except Exception as e:
                                    row_dict['理论总新品铺货费 (元)'] = None
                                    row_dict['折扣'] = None
                                    row_dict['折后总新品铺货费 (元)'] = None
                                    row_dict['铺货门店数量'] = f"错误: {str(e)}"
                                    logs.append(f"第 {index+1} 行 ({row.get('商品名称','未知')}): {e}")
                                
                                results.append(row_dict)
                                progress_bar.progress((index + 1) / len(df))

                            result_df = pd.DataFrame(results)
                            status_text.success("🎉 批量计算完成！")

                        st.markdown(
                            """
                            #### 📊 计算结果 <span style="color: gray; font-size: 0.9em;">（仅预览前5条）</span>
                            """,
                            unsafe_allow_html=True
                        )

                        # 推荐列顺序 + 排除 channel
                        cols_order = ['商品名称', '商品品类', 'SKU数', '铺货通道', '理论总新品铺货费 (元)', '折扣', '折后总新品铺货费 (元)', '铺货门店数量']
                        remaining_cols = [col for col in result_df.columns if col not in cols_order]
                        display_cols = cols_order + remaining_cols
                        display_cols = [col for col in display_cols if col.lower() != 'channel']

                        # 仅显示前5条预览
                        preview_df = result_df[display_cols].head(5)
                        st.dataframe(
                            preview_df,
                            use_container_width=True,
                            hide_index=False
                        )

                        # 当数据超过5条时提示用户
                        if len(result_df) > 5:
                            st.info(f"💡 共计算 **{len(result_df)}** 款新品，仅显示前5条预览。完整结果请点击下方导出按钮获取。")

                        # 总费用汇总
                        valid_fees = result_df['折后总新品铺货费 (元)'].dropna()
                        if not valid_fees.empty:
                            total_fee = int(valid_fees.sum())
                            st.success(f"🎯 本次批量计算 **{len(valid_fees)}** 款新品，总新品铺货费：**{total_fee:,} 元**")

                        # 导出完整结果（包含所有记录）
                        output = BytesIO()
                        with pd.ExcelWriter(output, engine='openpyxl') as writer:
                            result_df.to_excel(writer, index=False, sheet_name='计算结果')
                        
                        st.download_button(
                            "📤 导出完整结果",
                            output.getvalue(),
                            file_name=f"新品铺货费_批量结果_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )

                        if logs:
                            with st.expander("⚠️ 查看错误日志"):
                                st.write(logs)

                    except Exception as e:
                        st.error(f"处理文件失败：{e}")
        else:
            st.info("👆 请上传批量新品文件，上传后即可一键计算全部新品费用。")

if __name__ == "__main__":
    main()