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
from src.core.store_manager import load_store_master, calc_auto_counts, extract_manual_counts, load_xp_mapping
from src.core.calculator import calculate_fee
from src.core.file_utils import read_excel_safe

# Page Config
st.set_page_config(page_title="新品铺货费计算器", page_icon="💰", layout="wide")

# Load Config with Cache
@st.cache_data
def get_config(path):
    return load_config(path)

@st.cache_data
def get_store_master(path):
    return load_store_master(path)

@st.cache_data
def get_xp_mapping(path):
    return load_xp_mapping(path)

try:
    config_path = os.path.join(project_root, "config", "coefficients.xlsx")
    config = get_config(config_path)
except Exception as e:
    st.error(f"无法加载配置文件: {e}")
    st.stop()

def main():
    # --- Custom CSS to adjust top padding and remove header ---
    # --- 紧凑型计算器专用样式 ---
    st.markdown("""
        <style>
        /* 1. 限制最大宽度：像一个真正的计算器窗口一样居中显示 */
        .block-container {
            max-width: 1000px;       /* 核心：限制宽度 */
            padding-top: 2rem !important;
            padding-bottom: 2rem !important;
            margin: auto;           /* 居中 */
        }
        
        /* 2. 压缩垂直间距：让输入框排列更紧密，减少滚动 */
        div[data-testid="stVerticalBlock"] > div {
            gap: 0.5rem !important; /* 默认是 1rem，这里减半 */
        }
        
        /* 3. 压缩输入框本身的高度和边距 */
        .stNumberInput, .stSelectbox, .stTextInput {
            margin-bottom: -5px !important; /* 进一步拉近上下距离 */
        }
        
        /* 4. 隐藏无关元素 */
        header[data-testid="stHeader"] { display: none; }
        footer { display: none; }
        
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<h2 style='text-align: center;'>新品铺货费计算器</h2>", unsafe_allow_html=True)

    # --- Data Loading (Auto) ---
    store_master_path = os.path.join(project_root, "data", "store_master.xlsx")
    store_master_df = None
    update_time = "未知"

    if os.path.exists(store_master_path):
        try:
            store_master_df = get_store_master(store_master_path)
            if "门店表更新时间" in store_master_df.columns:
                # 取第一行的更新时间作为显示值
                update_time = str(store_master_df["门店表更新时间"].iloc[0])
        except Exception as e:
            st.error(f"加载门店数据失败: {e}")
    
    # Load XP Mapping
    xp_mapping_path = os.path.join(project_root, "data", "处方类别与批文分类表.xlsx")
    xp_map = get_xp_mapping(xp_mapping_path)

    # 显示隐藏式更新时间
    st.markdown(
        f"<p style='color: #BDC3C7; font-size: 0.8em; text-align: right; margin-top: -20px;'>"
        f"门店表更新于: {update_time}</p>",
        unsafe_allow_html=True
    )

    # --- Tabs ---
    tab1, tab2 = st.tabs(["📝 单品计算器", "📂 批量计算器"])

    # --- Tab 1: 单品计算器 ---
    with tab1:
        with st.container(border=True):
            st.markdown("<div style='font-size: 18px; font-weight: bold; margin-bottom: 10px;'>📝 通道计算器 -- 输入信息</div>", unsafe_allow_html=True)
            
            c1, c2 = st.columns(2)
            with c1:
                category = st.selectbox("新品大类", list(config["base_fees"].keys()))
            with c2:
                supplier_type = st.selectbox("供应商类型", list(config["supplier_type_coeffs"].keys()))

            c3, c4 = st.columns(2)
            with c3:
                sku_count = st.number_input("同一供应商单次引进SKU数", min_value=1, value=1)
            with c4:
                return_policy = st.selectbox("退货条件", list(config["return_policy_coeffs"].keys()))
                
            c5, c6 = st.columns(2)
            with c5:
                cost_price = st.number_input("进价 (元)", min_value=0.0, value=10.0)
            with c6:
                gross_margin = st.number_input("预估成交综合毛利率 (%)", min_value=0.0, max_value=100.0, value=40.0)
                
            c7, c8 = st.columns(2)
            with c7:
                payment = st.selectbox("付款方式", list(config["payment_coeffs"].keys()))
            with c8:
                # 处方类别选择
                xp_options = config.get("prescription_categories", [])
                if not xp_options and xp_map:
                    xp_options = list(xp_map.keys())
                
                if not xp_options:
                    xp_options = ["无 (未配置处方类别)"]

                selected_xp_category = st.selectbox("处方类别 (筛选受限门店)", xp_options)

            # 获取选中的处方类别对应的批文编码
            target_xp_code = xp_map.get(selected_xp_category) if xp_map else None
            st.markdown("---")
            
            st.markdown("**通道选择**")
            channel_mode = st.radio(
                "通道模式",
                ["标准通道 (按黄/蓝/绿通道选择门店)", "自定义通道 (按标签选择门店)"],
                label_visibility="collapsed"
            )
            
            channel = "自定义"
            custom_sub_mode = "手动输入" # 默认为手动
            manual_counts = {}
            selected_custom_types = []
            
            if "标准通道" in channel_mode:
                color_selection = st.radio(
                    "选择颜色",
                    ["🟡 黄色", "🔵 蓝色", "🟢 绿色"],
                    label_visibility="collapsed"
                )
                channel = color_selection.split(" ")[1]
            else:
                channel = "自定义"
                # 自定义模式下的两种子模式选择
                custom_sub_mode = st.radio(
                    "自定义输入方式:",
                    ["手动输入门店数", "自定义销售规模"],
                    horizontal=True
                )
                
                if "手动输入" in custom_sub_mode:
                    st.caption("请输入各销售规模门店数量:")
                    # 创建一行 6 列的布局
                    col_inputs = st.columns(6)
                    
                    # 依次在每一列中放置输入框
                    with col_inputs[0]:
                        manual_counts["超级旗舰店"] = st.number_input("超级旗舰店", min_value=0, key="custom_super")
                    with col_inputs[1]:
                        manual_counts["旗舰店"] = st.number_input("旗舰店", min_value=0, key="custom_flag")
                    with col_inputs[2]:
                        manual_counts["大店"] = st.number_input("大店", min_value=0, key="custom_big")
                    with col_inputs[3]:
                        manual_counts["中店"] = st.number_input("中店", min_value=0, key="custom_mid")
                    with col_inputs[4]:
                        manual_counts["小店"] = st.number_input("小店", min_value=0, key="custom_small")
                    with col_inputs[5]:
                        manual_counts["成长店"] = st.number_input("成长店", min_value=0, key="custom_grow")
                else:
                    # 勾选规模模式
                    st.caption("请选择需要铺货的销售规模")
                    all_types = ["超级旗舰店", "旗舰店", "大店", "中店", "小店", "成长店"]
                    selected_custom_types = st.multiselect(
                        "销售规模",
                        all_types,
                        default=["小店"],
                        label_visibility="collapsed"
                    )
                    if not selected_custom_types:
                        st.warning("⚠️ 请至少选择一种销售规模")

        if st.button("开始计算", type="primary", use_container_width=True):
            # 校验数据源
            # 注意：如果是自定义-勾选模式，也需要store_master_df
            needs_master_data = (channel != "自定义") or ("自定义销售规模" in custom_sub_mode)
            
            if needs_master_data and store_master_df is None:
                st.error("❌ 未找到门店主数据，无法进行自动计算（请检查 data/store_master.xlsx）！")
            elif channel == "自定义" and "自定义销售规模" in custom_sub_mode and not selected_custom_types:
                st.error("❌ 请至少勾选一种销售规模！")
            else:
                row_data = {
                    "新品大类": category,
                    "处方类别": selected_xp_category,
                    "SKU数": sku_count,
                    "channel": channel,
                    "预估毛利率(%)": gross_margin,
                    "付款方式": payment,
                    "供应商类型": supplier_type,
                    "进价": cost_price,
                    "退货条件": return_policy
                }
                
                # 如果是手动输入模式，把手动数据填进去
                if channel == "自定义" and "手动输入" in custom_sub_mode:
                    for k, v in manual_counts.items():
                        row_data[f"(自定义){k}数"] = v

                try:
                    store_counts = {}
                    excluded_count = 0
                    is_auto_calc_mode = False

                    # 分支逻辑：决定如何获取 store_counts
                    if channel == "自定义" and "手动输入" in custom_sub_mode:
                        # 1. 纯手动模式
                        store_counts = extract_manual_counts(row_data)
                        st.info("💡 自定义(手动)模式：不进行'受限批文'门店剔除，按输入数量计算。")
                        
                    elif channel == "自定义" and "自定义销售规模" in custom_sub_mode:
                        # 2. 自定义(勾选)模式 -> 走自动计算逻辑
                        is_auto_calc_mode = True
                        # 直接把选中的类型列表传给计算函数
                        store_counts = calc_auto_counts(
                            store_master_df, 
                            selected_custom_types, # 传入列表
                            restricted_xp_code=target_xp_code
                        )
                        
                        # 计算剔除数量
                        if target_xp_code:
                            raw_counts = calc_auto_counts(
                                store_master_df, 
                                selected_custom_types, 
                                restricted_xp_code=None
                            )
                            excluded_count = sum(raw_counts.values()) - sum(store_counts.values())
                            
                    else:
                        # 3. 标准通道模式 (黄/蓝/绿)
                        is_auto_calc_mode = True
                        store_counts = calc_auto_counts(
                            store_master_df, 
                            channel, 
                            restricted_xp_code=target_xp_code
                        )
                        # 计算剔除数量
                        if target_xp_code:
                            raw_counts = calc_auto_counts(
                                store_master_df, 
                                channel, 
                                restricted_xp_code=None
                            )
                            excluded_count = sum(raw_counts.values()) - sum(store_counts.values())
                    
                    # 执行费用计算
                    result = calculate_fee(row_data, store_counts, config)

                    # --- 展示结果 ---
                    
                    with st.container(border=True):
                        st.markdown("<div style='font-size: 18px; font-weight: bold; margin-bottom: 10px;'>📝 通道计算器 -- 输出信息</div>", unsafe_allow_html=True)
                        
                        # 1. 费用概览区域 (Top Level Stats)
                        col_res1, col_res2, col_res3 = st.columns([1, 1, 1.5])
                        with col_res1:
                            st.metric("理论总新品铺货费(元)", f"{int(result['theoretical_fee']):,}")
                        with col_res2:
                            st.metric("折扣", f"{result['discount_factor']:.2f}")
                        with col_res3:
                            # 醒目的最终金额
                            st.markdown(
                                f"""
                                <div style="font-size: 1rem; color: #555;">折后总新品铺货费(元)</div>
                                <div style="font-size: 2.25rem; color: #D32F2F; font-weight: bold;">
                                    {int(result['final_fee']):,}
                                </div>
                                """, 
                                unsafe_allow_html=True
                            )
                            
                        if result.get('is_floor_triggered'):
                            st.caption(f"⚠️ 已触发最低兜底费用: {result['min_floor']}元")

                        st.divider() # 分割线

                        # 2. 详细数据展示 (Split Tables)
                        
                        # 使用 Expander (折叠面板) 实现“低调隐秘”
                        # expanded=False 确保默认是收起的，不喧宾夺主
                        with st.expander("👁️ 查看计算过程详情 (门店分布&系数)", expanded=False):
                            
                            # 创建左右两列，左边放系数，右边放门店，显得紧凑规整
                            col_detail_2, col_detail_1 = st.columns(2)
                            
                            # --- 左侧：计算系数 (转置为垂直列表) ---
                            with col_detail_1:
                                st.markdown("📉 计算系数")
                                # 将原始数据转换为 "项目 - 数值" 的垂直表格
                                coeffs_data = {
                                    "项目": [name for name, _ in result['coefficients']],
                                    "系数": [val for _, val in result['coefficients']]
                                }
                                df_coeffs_vertical = pd.DataFrame(coeffs_data)
                                
                                st.dataframe(
                                    df_coeffs_vertical,
                                    use_container_width=True,
                                    hide_index=True,
                                    column_config={
                                        "项目": st.column_config.TextColumn("影响因素", width="medium"),
                                        "系数": st.column_config.NumberColumn("数值", format="%.2f", width="small")
                                    }
                                )

                            # --- 右侧：门店分布 (转置为垂直列表) ---
                            with col_detail_2:
                                st.markdown("🏬 门店分布")
                                
                                # 按照固定顺序展示，哪怕数量为0也显示，保持整齐
                                store_order = ["超级旗舰店", "旗舰店", "大店", "中店", "小店", "成长店"]
                                store_data = {
                                    "门店类型": store_order,
                                    "数量": [result['store_details'].get(t, 0) for t in store_order]
                                }
                                df_stores_vertical = pd.DataFrame(store_data)
                                
                                st.dataframe(
                                    df_stores_vertical,
                                    use_container_width=True,
                                    hide_index=True,
                                    column_config={
                                        "门店类型": st.column_config.TextColumn("销售规模", width="medium"),
                                        "数量": st.column_config.NumberColumn("门店数", format="%d")
                                    }
                                )

                            # 底部的统计说明文字放在展开框内部或者紧挨着底部
                            total_stores = sum(result['store_details'].values())
                            # 构建底部统计文案
                            footer_text = f"计算池中的门店数量: {total_stores:,}"
                            if is_auto_calc_mode and target_xp_code:
                                # 场景1：自动计算模式 且 存在受限批文代码 -> 显示剔除数量
                                footer_text += f" | 剔除受限门店数: {excluded_count}"
                            elif is_auto_calc_mode:
                                # 场景2：自动计算模式 但 无受限批文代码 -> 显示无剔除
                                footer_text += f" | 无受限门店剔除"
                            else:
                                # 场景3：手动输入模式 -> 显示手动模式提示
                                footer_text += " (手动输入模式)"
                            
                            st.caption(footer_text)

                    with st.expander("规则说明"):
                        rule_pdf_path = os.path.join(project_root, "data", "rule_description.pdf")
                        if os.path.exists(rule_pdf_path):
                            with open(rule_pdf_path, "rb") as f:
                                base64_pdf = base64.b64encode(f.read()).decode('utf-8')
                            pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf"></iframe>'
                            st.markdown(pdf_display, unsafe_allow_html=True)
                        else:
                            st.info("暂无规则说明文档")

                except Exception as e:
                    st.error(f"计算出错: {e}")

    # --- Tab 2: 批量计算器 ---
    with tab2:
        st.header("📂 批量费用计算")
        st.markdown(
            "<p style='color: gray; font-size: 0.95em; margin-top: -10px; margin-bottom: 20px;'>"
            "快速为多款新品一次性计算铺货费用"
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
            else:
                st.warning("未找到模板文件")

        st.markdown("---")
        uploaded_batch = st.file_uploader("上传批量Excel文件", type=["xlsx"])

        if uploaded_batch:
            if st.button("开始批量计算", type="primary", use_container_width=True):
                if store_master_df is None:
                    st.error("❌ 未找到门店主数据，请检查 data/store_master.xlsx 文件！")
                else:
                    try:
                        df = read_excel_safe(uploaded_batch)
                        with st.spinner("正在批量计算..."):
                            results = []
                            logs = []
                            progress_bar = st.progress(0)
                            
                            for index, row in df.iterrows():
                                row_dict = row.to_dict()
                                try:
                                    channel_name = row_dict.get('铺货通道')
                                    batch_xp_cat = row_dict.get('处方类别')
                                    batch_target_code = xp_map.get(str(batch_xp_cat).strip()) if (batch_xp_cat and xp_map) else None

                                    # 批量计算这里主要支持标准通道和旧的自定义模式
                                    # 如果在Excel里填了 "自定义"，则走手动提取
                                    # 如果想在Excel里支持"小店,成长店"这种筛选，calc_auto_counts已经支持了解析逗号分隔符
                                    
                                    if channel_name == "自定义":
                                        store_counts = extract_manual_counts(row_dict)
                                    else:
                                        # 这里 channel_name 可以是 "黄色" 也可以是 "小店,成长店"
                                        store_counts = calc_auto_counts(
                                            store_master_df, 
                                            channel_name,
                                            restricted_xp_code=batch_target_code
                                        )
                                    
                                    result = calculate_fee(row_dict, store_counts, config)
                                    
                                    row_dict['理论总新品铺货费 (元)'] = int(result['theoretical_fee'])
                                    row_dict['折扣'] = result['discount_factor']
                                    row_dict['折后总新品铺货费 (元)'] = int(result['final_fee'])
                                    if batch_target_code:
                                        row_dict['备注'] = f"已按类别[{batch_xp_cat}]剔除受限门店"

                                    results.append(row_dict)
                                except Exception as e:
                                    row_dict['备注'] = f"Error: {e}"
                                    results.append(row_dict)
                                
                                progress_bar.progress((index + 1) / len(df))
                            
                            result_df = pd.DataFrame(results)
                            st.success("批量计算完成！")
                            st.dataframe(result_df.head())
                            
                            output = BytesIO()
                            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                                result_df.to_excel(writer, index=False)
                            
                            st.download_button(
                                "导出结果", 
                                output.getvalue(), 
                                file_name="批量计算结果.xlsx", 
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )

                    except Exception as e:
                        st.error(f"处理文件失败: {e}")

if __name__ == "__main__":
    main()