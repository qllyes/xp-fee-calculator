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
# 保持 wide 模式，确保 Tab 栏不跳动
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

@st.cache_data
def get_unique_values(df, column):
    if df is None or column not in df.columns:
        return []
    
    # 特殊处理：客流商圈 (逗号分隔)
    if column == "客流商圈":
        all_vals = []
        for val in df[column].dropna().astype(str):
            parts = val.replace("，", ",").split(",")
            all_vals.extend([p.strip() for p in parts if p.strip()])
        return sorted(list(set(all_vals)))
    
    return sorted(df[column].dropna().unique().tolist())

try:
    config_path = os.path.join(project_root, "config", "coefficients.xlsx")
    config = get_config(config_path)
except Exception as e:
    st.error(f"无法加载配置文件: {e}")
    st.stop()

def main():
    # --- 优化后的混合布局 CSS ---
    st.markdown("""
        <style>
        /* 1. 顶部留白调整 */
        .block-container {
            padding-top: 1.5rem !important;
            padding-bottom: 2rem !important;
        }

        /* 2. 压缩垂直间距 */
        div[data-testid="stVerticalBlock"] > div {
            gap: 0.5rem !important;
        }
        
        /* 3. 压缩输入框本身的高度和边距 */
        .stNumberInput, .stSelectbox, .stTextInput, .stMultiSelect {
            margin-bottom: -5px !important;
        }
        
        /* 4. 隐藏无关元素 */
        header[data-testid="stHeader"] { display: none; }
        footer { display: none; }

        /* 5. 结果文字大号显示 */
        [data-testid="stMetricValue"] {
            font-size: 1.8rem !important;
            font-weight: 700 !important;
        }

        /* 6. 【精准定位】只让 6 个手动输入框的标签和内容居中 */
        div[data-testid="stNumberInput"]:has(input[aria-label="超级旗舰店"]),
        div[data-testid="stNumberInput"]:has(input[aria-label="旗舰店"]),
        div[data-testid="stNumberInput"]:has(input[aria-label="大店"]),
        div[data-testid="stNumberInput"]:has(input[aria-label="中店"]),
        div[data-testid="stNumberInput"]:has(input[aria-label="小店"]),
        div[data-testid="stNumberInput"]:has(input[aria-label="成长店"]) {
            /* 容器样式 */
        }

        /* 让标签居中 */
        div[data-testid="stNumberInput"]:has(input[aria-label="超级旗舰店"]) label[data-testid="stWidgetLabel"],
        div[data-testid="stNumberInput"]:has(input[aria-label="旗舰店"]) label[data-testid="stWidgetLabel"],
        div[data-testid="stNumberInput"]:has(input[aria-label="大店"]) label[data-testid="stWidgetLabel"],
        div[data-testid="stNumberInput"]:has(input[aria-label="中店"]) label[data-testid="stWidgetLabel"],
        div[data-testid="stNumberInput"]:has(input[aria-label="小店"]) label[data-testid="stWidgetLabel"],
        div[data-testid="stNumberInput"]:has(input[aria-label="成长店"]) label[data-testid="stWidgetLabel"] {
            width: 100% !important;
            text-align: center !important;
            justify-content: center !important;
        }
        
        /* 让输入框内的数字居中 */
        div[data-testid="stNumberInput"]:has(input[aria-label="超级旗舰店"]) input,
        div[data-testid="stNumberInput"]:has(input[aria-label="旗舰店"]) input,
        div[data-testid="stNumberInput"]:has(input[aria-label="大店"]) input,
        div[data-testid="stNumberInput"]:has(input[aria-label="中店"]) input,
        div[data-testid="stNumberInput"]:has(input[aria-label="小店"]) input,
        div[data-testid="stNumberInput"]:has(input[aria-label="成长店"]) input {
            text-align: center !important;
        }
        /* 7. 压缩标题 (H2) 的下边距 */
        h2 {
            margin-bottom: 0.2rem !important; /* 原本很大，改为极小 */
            padding-bottom: 0rem !important;
        }

        /* 8. 向上提拉 Tab 栏，消除默认的大间隙 */
        .stTabs {
            margin-top: -1.5rem !important;   /* 核心：负边距把 Tab 往上拉 */
        }

        /* 9. 自定义 secondary 按钮（下载模板按钮）的背景色 */
        button[kind="secondary"] {
            background-color: #F0F2F6 !important; /* 浅灰色背景 */
            border: 1px solid #D1D5DB !important; /* 稍微深一点的边框 */
            color: #31333F !important;
        }
        
        /* 悬停效果 */
        button[kind="secondary"]:hover {
            background-color: #E6E9EF !important;
            border-color: #B0B5BE !important;
        }

        /* 10. 限制多选框最大高度，避免撑开布局 */
        .stMultiSelect div[data-baseweb="select"] > div {
            max-height: 46px !important;
            overflow-y: auto !important;
        }
        
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
                update_time = str(store_master_df["门店表更新时间"].iloc[0])
        except Exception as e:
            st.error(f"加载门店数据失败: {e}")
    
    xp_mapping_path = os.path.join(project_root, "data", "处方类别与批文分类表.xlsx")
    xp_map = get_xp_mapping(xp_mapping_path)

    # 显示隐藏式更新时间
    st.markdown(
        f"""
        <div style="
            text-align: right;
            margin-bottom: -28px; 
            position: relative;
            z-index: 999;
            padding-right: 5px;
            top: 2px;
            pointer-events: none;
        ">
            <span style="color: #BDC3C7; font-size: 0.8em;">门店表更新于: {update_time}</span>
        </div>
        """,
        unsafe_allow_html=True
    )

    # --- Tabs ---
    tab1, tab2 = st.tabs(["🏷️ 单品计算器", "📂 批量计算器"])

    # --- Tab 1: 单品计算器 (居中布局) ---
    with tab1:
        spacer_left, col_center, spacer_right = st.columns([1.5, 7, 1.5]) # 这里调整为 1:3:1 让中间稍微宽一点
        
        with col_center:
            with st.container(border=True):
                st.markdown("<div style='font-size: 18px; font-weight: bold; margin-bottom: 10px;'>📝 通道计算器 -- 输入信息</div>", unsafe_allow_html=True)
                
                # [新增功能] 采购类型选择，独占一行，放在最前面
                # 对应需求：前端新增的【统采or地采】放在【新品大类】前面，独自占一行
                procurement_type = st.selectbox(
                    "统采or地采", 
                    ["统采", "地采"],
                    index=0, # 默认统采
                    # help="选择统采或地采将影响最低保底费用的取值"
                )

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
                    cost_price = st.number_input("底价 (元)", min_value=0.0, value=10.0)
                with c6:
                    gross_margin = st.number_input("预估成交综合毛利率 (%)", min_value=0.0, max_value=100.0, value=40.0)               
                c7, c8 = st.columns(2)
                with c7:
                    payment = st.selectbox("付款方式", list(config["payment_coeffs"].keys()))
                with c8:
                    xp_options = config.get("prescription_categories", [])
                    if not xp_options and xp_map:
                        xp_options = list(xp_map.keys())
                    if not xp_options:
                        xp_options = ["无 (未配置处方类别)"]
                    selected_xp_category = st.selectbox("处方类别", xp_options)

                target_xp_code = xp_map.get(selected_xp_category) if xp_map else None
                #st.markdown("---")
                
                st.markdown("""
                            <div style="
                                font-size: 16px; 
                                font-weight: 600; 
                                margin-bottom: 0px; 
                                color: #31333F;
                            ">
                                通道选择
                            </div>
                        """, unsafe_allow_html=True)
                channel_mode = st.radio(
                    "通道模式",
                    ["标准通道", "自定义通道"],
                    label_visibility="collapsed",
                    horizontal=True # 横向排列
                )
                
                channel = "自定义"
                custom_sub_mode = "手动输入"
                manual_counts = {}
                selected_filters = {}
                
                if "标准通道" in channel_mode:
                    color_selection = st.selectbox(
                        "选择标准通道范围",
                        ["全量门店", "小店及以上", "中店及以上", "大店及以上", "旗舰店及以上", "超级旗舰店"],
                        label_visibility="collapsed" # 保持标签隐藏，与战区选择风格一致
                    )
                    channel = color_selection.split()[-1] 
                else:
                    channel = "自定义"
                    # 使用 segmented_control (如果版本支持) 或 radio
                    try:
                        custom_sub_mode = st.segmented_control(
                            "自定义输入方式",
                            ["标签筛选", "手动输入"],
                            default="标签筛选",
                            label_visibility="collapsed"
                        )
                    except AttributeError:
                        custom_sub_mode = st.radio(
                            "自定义输入方式:",
                            ["标签筛选", "手动输入"],
                            horizontal=True,
                            label_visibility="collapsed"
                        )
                    
                    if custom_sub_mode == "手动输入":
                        st.caption("请输入各销售规模门店数量:")
                        col_inputs = st.columns(6)
                        with col_inputs[0]: manual_counts["超级旗舰店"] = st.number_input("超级旗舰店", min_value=0, key="custom_super")
                        with col_inputs[1]: manual_counts["旗舰店"] = st.number_input("旗舰店", min_value=0, key="custom_flag")
                        with col_inputs[2]: manual_counts["大店"] = st.number_input("大店", min_value=0, key="custom_big")
                        with col_inputs[3]: manual_counts["中店"] = st.number_input("中店", min_value=0, key="custom_mid")
                        with col_inputs[4]: manual_counts["小店"] = st.number_input("小店", min_value=0, key="custom_small")
                        with col_inputs[5]: manual_counts["成长店"] = st.number_input("成长店", min_value=0, key="custom_grow")
                    else:
                        # --- 标签筛选模式 ---
                        st.caption("请选择筛选条件 (为空表示全选)")
                        
                        if store_master_df is not None:
                            # 1. 区域维度 (多选)
                            with st.expander("选择省公司/省份/城市", expanded=True):
                                col_reg1, col_reg2, col_reg3 = st.columns(3)
                                with col_reg1:
                                    opts = get_unique_values(store_master_df, "省公司")
                                    selected_filters["省公司"] = st.multiselect("省公司", opts, placeholder="全部 (默认)")
                                with col_reg2:
                                    opts = get_unique_values(store_master_df, "省份")
                                    selected_filters["省份"] = st.multiselect("省份", opts, placeholder="全部 (默认)")
                                with col_reg3:
                                    opts = get_unique_values(store_master_df, "城市")
                                    selected_filters["城市"] = st.multiselect("城市", opts, placeholder="全部 (默认)")
                            
                            # 2. 门店属性 (包含：销售规模、原有属性、业务属性)
                            with st.expander("门店属性筛选", expanded=True):
                                # Row 1: 销售规模
                                all_types = ["超级旗舰店", "旗舰店", "大店", "中店", "小店", "成长店"]
                                selected_filters["销售规模"] = st.multiselect("销售规模", all_types, default=[], placeholder="全部 (默认)")

                                # Row 2: 店龄店型 & 客流商圈
                                col_attr1, col_attr2 = st.columns(2)
                                with col_attr1:
                                    opts = get_unique_values(store_master_df, "店龄店型")
                                    selected_filters["店龄店型"] = st.multiselect("店龄店型", opts, placeholder="全部 (默认)")
                                with col_attr2:
                                    opts = get_unique_values(store_master_df, "客流商圈")
                                    selected_filters["客流商圈"] = st.multiselect("客流商圈", opts, placeholder="全部 (默认)")
                                
                                # Row 3: 行政区划 & 公域O2O
                                col_attr3, col_attr4 = st.columns(2)
                                with col_attr3:
                                    opts = get_unique_values(store_master_df, "行政区划等级")
                                    selected_filters["行政区划等级"] = st.multiselect("行政区划等级", opts, placeholder="全部 (默认)")
                                with col_attr4:
                                    opts = get_unique_values(store_master_df, "公域O2O店型")
                                    selected_filters["公域O2O店型"] = st.multiselect("公域O2O店型", opts, placeholder="全部 (默认)")

                                # Row 4: 业务属性 (单选: 全部/是/否)
                                st.markdown("---")
                                col_bool1, col_bool2, col_bool3 = st.columns(3)
                                bool_opts = ["全部", "是", "否"]
                                with col_bool1:
                                    selected_filters["是否医保店"] = st.selectbox("是否医保店", bool_opts)
                                with col_bool2:
                                    selected_filters["是否O2O门店"] = st.selectbox("是否O2O门店", bool_opts)
                                with col_bool3:
                                    selected_filters["是否统筹店"] = st.selectbox("是否统筹店", bool_opts)

                # [新增] 提报战区选择 (全局，但不在自定义筛选内)
                st.markdown("""
                            <div style="
                                font-size: 16px; 
                                font-weight: 400; 
                                margin-bottom: 5px; 
                                margin-top: 10px;
                                color: #31333F;
                            ">
                                战区选择(如果选中一个战区，只会计算该战区中的门店)
                            </div>
                        """, unsafe_allow_html=True)
                
                war_zone_options = config.get("war_zones", ["全集团"])
                selected_war_zone = st.selectbox("选择战区", war_zone_options, label_visibility="collapsed")

            if st.button("开始计算", type="primary", use_container_width=True):
                needs_master_data = (channel != "自定义") or (custom_sub_mode == "标签筛选")
                
                if needs_master_data and store_master_df is None:
                    st.error("❌ 未找到门店主数据，无法进行自动计算（请检查 data/store_master.xlsx）！")
                # 移除对销售规模必选的校验，因为现在空代表全选
                # elif channel == "自定义" and custom_sub_mode == "标签筛选" and not selected_filters.get("销售规模"):
                #     st.error("❌ 请至少勾选一种销售规模！")
                else:
                    row_data = {
                        "新品大类": category,
                        "统采or地采": procurement_type,
                        "处方类别": selected_xp_category,
                        "同一供应商单次引进SKU数": sku_count,
                        "channel": channel,
                        "预估毛利率(%)": gross_margin,
                        "付款方式": payment,
                        "供应商类型": supplier_type,
                        "底价": cost_price,
                        "退货条件": return_policy
                    }
                    if channel == "自定义" and custom_sub_mode == "手动输入":
                        for k, v in manual_counts.items():
                            row_data[f"(自定义){k}数"] = v

                    try:
                        store_counts = {}
                        excluded_count = 0
                        is_auto_calc_mode = False

                        if channel == "自定义" and custom_sub_mode == "手动输入":
                            store_counts = extract_manual_counts(row_data)
                            st.info("💡 自定义(手动)模式：不进行'受限批文'门店剔除，按输入数量计算。")
                        elif channel == "自定义" and custom_sub_mode == "标签筛选":
                            is_auto_calc_mode = True
                            #计算最终门店数 (传入了 target_xp_code，会剔除受限门店)
                            store_counts = calc_auto_counts(
                                store_master_df, 
                                channel, # "自定义"
                                restricted_xp_code=target_xp_code,
                                war_zone=selected_war_zone,
                                filters=selected_filters
                            )
                            if target_xp_code:
                                #计算原始门店数 (restricted_xp_code 传了 None，即不进行受限剔除)
                                raw_counts = calc_auto_counts(
                                    store_master_df, 
                                    channel, 
                                    restricted_xp_code=None,
                                    war_zone=selected_war_zone,
                                    filters=selected_filters
                                )
                                excluded_count = sum(raw_counts.values()) - sum(store_counts.values())
                        else:
                            is_auto_calc_mode = True
                            store_counts = calc_auto_counts(
                                store_master_df, 
                                channel, 
                                restricted_xp_code=target_xp_code,
                                war_zone=selected_war_zone
                            )
                            if target_xp_code:
                                raw_counts = calc_auto_counts(
                                    store_master_df, 
                                    channel, 
                                    restricted_xp_code=None,
                                    war_zone=selected_war_zone
                                )
                                excluded_count = sum(raw_counts.values()) - sum(store_counts.values())
                        
                        result = calculate_fee(row_data, store_counts, config)

                        with st.container(border=True):
                            st.markdown("<div style='font-size: 18px; font-weight: bold; margin-bottom: 10px;'>🧾 通道计算器 -- 输出信息</div>", unsafe_allow_html=True)
                            
                            css_style = """
                            <style>
                                .metric-box {
                                    display: flex;
                                    flex-direction: column;
                                    align-items: center;
                                    justify-content: center;
                                    padding: 10px;
                                }
                                .metric-label {
                                    font-size: 0.9rem;
                                    color: #666;
                                    margin-bottom: 5px;
                                }
                                .metric-value {
                                    font-size: 1.8rem;
                                    font-weight: 700;
                                    font-family: 'Source Sans Pro', sans-serif;
                                }
                            </style>
                            """
                            st.markdown(css_style, unsafe_allow_html=True)

                            col_res1, col_res2, col_res3 = st.columns([1, 1, 1.2]) 
                            
                            with col_res1:
                                st.markdown(f"""
                                <div class="metric-box">
                                    <div class="metric-label">理论总新品铺货费(元)</div>
                                    <div class="metric-value" style="color: #333;">{int(result['theoretical_fee']):,}</div>
                                </div>
                                """, unsafe_allow_html=True)
                                
                            with col_res2:
                                st.markdown(f"""
                                <div class="metric-box">
                                    <div class="metric-label">折扣</div>
                                    <div class="metric-value" style="color: #333;">{result['discount_factor']:.2f}</div>
                                </div>
                                """, unsafe_allow_html=True)
                                
                            with col_res3:
                                st.markdown(f"""
                                <div class="metric-box">
                                    <div class="metric-label">折后总新品铺货费(元)</div>
                                    <div class="metric-value" style="color: #D32F2F; ">{int(result['final_fee']):,}</div>
                                </div>
                                """, unsafe_allow_html=True)

                            if result.get('is_floor_triggered'):
                                procurement = result.get('procurement_type', '未知标准')
                                st.caption(f"⚠️ 已触发最低兜底费用 ({procurement}): {result['min_floor']}元")

                            st.divider()

                            with st.expander("👁️ 查看计算过程详情 (门店分布&系数)", expanded=False):
                                col_detail_2, col_detail_1 = st.columns(2)
                                with col_detail_1:
                                    st.markdown("📉 计算系数")
                                    coeffs_data = {
                                        "项目": [name for name, _ in result['coefficients']],
                                        "系数": [val for _, val in result['coefficients']]
                                    }
                                    st.dataframe(pd.DataFrame(coeffs_data), use_container_width=True, hide_index=True)

                                with col_detail_2:
                                    st.markdown("🏬 门店分布")
                                    store_order = ["超级旗舰店", "旗舰店", "大店", "中店", "小店", "成长店"]
                                    store_data = {"销售规模": store_order, "门店数": [result['store_details'].get(t, 0) for t in store_order]}
                                    st.dataframe(pd.DataFrame(store_data), use_container_width=True, hide_index=True)

                                total_stores = sum(result['store_details'].values())
                                footer_text = f"计算池中的门店数量: {total_stores:,}"
                                if is_auto_calc_mode and target_xp_code: footer_text += f" | 剔除受限门店数: {excluded_count}"
                                elif is_auto_calc_mode: footer_text += f" | 无受限门店剔除"
                                else: footer_text += " (手动输入模式)"
                                st.caption(footer_text)

                        with st.expander("规则说明"):
                            rule_pdf_path = os.path.join(project_root, "data", "rule_description.pdf")
                            if os.path.exists(rule_pdf_path):
                                with open(rule_pdf_path, "rb") as f:
                                    base64_pdf = base64.b64encode(f.read()).decode('utf-8')
                                st.markdown(f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf"></iframe>', unsafe_allow_html=True)
                            else:
                                st.info("暂无规则说明文档")

                    except Exception as e:
                        st.error(f"计算出错: {e}")

    # --- Tab 2: 批量计算器 ---
    with tab2:
        st.markdown("<p style='color: gray; font-size: 0.95em; margin-top: -10px; margin-bottom: 20px;'>快速为多款新品一次性计算铺货费用</p>", unsafe_allow_html=True)

        with st.expander("📥 需要导入模板？点这里下载", expanded=True):
            template_path = os.path.join(project_root, "data", "batch_template.xlsx")
            if os.path.exists(template_path):
                with open(template_path, "rb") as f:
                    st.download_button("下载导入模板", f, file_name="新品铺货费_批量导入模板.xlsx", use_container_width=True, type="secondary")
            else:
                st.warning("未找到模板文件")

        st.markdown("---")
        uploaded_batch = st.file_uploader("上传批量Excel文件", type=["xlsx"])

        # [修复逻辑 1] 初始化 Session State
        if "batch_last_file_id" not in st.session_state:
            st.session_state.batch_last_file_id = None
        if "batch_results_df" not in st.session_state:
            st.session_state.batch_results_df = None

        if uploaded_batch:
            # [修复逻辑 2] 检测文件是否变化，如果变化则清空之前的结果
            current_file_id = uploaded_batch.file_id
            if current_file_id != st.session_state.batch_last_file_id:
                st.session_state.batch_results_df = None
                st.session_state.batch_last_file_id = current_file_id

            # [修复逻辑 3] 点击按钮只负责计算和保存结果到 Session，不负责显示
            if st.button("开始批量计算", type="primary", use_container_width=True):
                if store_master_df is None:
                    st.error("❌ 未找到门店主数据，请检查 data/store_master.xlsx 文件！")
                else:
                    try:
                        df = read_excel_safe(uploaded_batch)
                        with st.spinner("正在批量计算..."):
                            results = []
                            progress_bar = st.progress(0)
                            
                            for index, row in df.iterrows():
                                row_dict = row.to_dict()
                                try:
                                    # [新增] 批量模式下读取采购类型，如果Excel里没这一列，默认“统采”
                                    p_type = row_dict.get('统采or地采')
                                    if pd.isna(p_type) or str(p_type).strip() == "":
                                        row_dict['统采or地采'] = "统采"
                                    else:
                                        row_dict['统采or地采'] = str(p_type).strip()

                                    channel_name = row_dict.get('铺货通道')
                                    batch_xp_cat = row_dict.get('处方类别')
                                    batch_target_code = xp_map.get(str(batch_xp_cat).strip()) if (batch_xp_cat and xp_map) else None
                                    
                                    # [新增] 批量计算读取战区
                                    batch_war_zone = row_dict.get('提报战区')
                                    if pd.isna(batch_war_zone) or str(batch_war_zone).strip() == "" or str(batch_war_zone).strip() == "全集团":
                                        batch_war_zone = "全集团"
                                    else:
                                        batch_war_zone = str(batch_war_zone).strip()

                                    excluded_count = 0

                                    # 1. 计算 Store Counts
                                    if channel_name == "自定义":
                                        store_counts = extract_manual_counts(row_dict)
                                    else:
                                        # 计算过滤后的门店数
                                        store_counts = calc_auto_counts(
                                            store_master_df, 
                                            channel_name, 
                                            restricted_xp_code=batch_target_code,
                                            war_zone=batch_war_zone
                                        )
                                        # 如果有处方限制，计算剔除数量
                                        if batch_target_code:
                                            raw_counts = calc_auto_counts(
                                                store_master_df, 
                                                channel_name, 
                                                restricted_xp_code=None,
                                                war_zone=batch_war_zone
                                            )
                                            excluded_count = sum(raw_counts.values()) - sum(store_counts.values())
                                    
                                    # 2. 费用计算
                                    result = calculate_fee(row_dict, store_counts, config)
                                    
                                    row_dict['理论总新品铺货费 (元)'] = int(result['theoretical_fee'])
                                    row_dict['折扣'] = result['discount_factor']
                                    row_dict['折后总新品铺货费 (元)'] = int(result['final_fee'])
                                    
                                    # 详情拆分
                                    active_stores = {k: v for k, v in result['store_details'].items() if v > 0}
                                    row_dict['[详情]门店分布'] = str(active_stores)
                                    
                                    coeffs_dict = {item[0]: item[1] for item in result['coefficients']}
                                    row_dict['[详情]计算系数'] = str(coeffs_dict)
                                    
                                    if batch_target_code and excluded_count > 0:
                                        row_dict['备注'] = f"已剔除受限门店数：{excluded_count}"
                                    elif batch_target_code:
                                        row_dict['备注'] = "无受限门店剔除"
                                    else:
                                        row_dict['备注'] = ""
                                        
                                    results.append(row_dict)
                                except Exception as e:
                                    row_dict['备注'] = f"Error: {e}"
                                    results.append(row_dict)
                                
                                progress_bar.progress((index + 1) / len(df))
                            
                            result_df = pd.DataFrame(results)
                            st.success("批量计算完成！")
                            
                            # [关键步骤] 将结果存入 Session State，而不是直接显示
                            st.session_state.batch_results_df = result_df

                    except Exception as e:
                        st.error(f"处理文件失败: {e}")
            
            # [修复逻辑 4] 只要 Session State 中有结果，就显示（独立于按钮点击事件）
            if st.session_state.batch_results_df is not None:
                st.dataframe(st.session_state.batch_results_df.head())
                
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    st.session_state.batch_results_df.to_excel(writer, index=False)
                
                st.download_button(
                    "导出结果", 
                    output.getvalue(), 
                    file_name="新品费批量计算结果.xlsx", 
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

if __name__ == "__main__":
    main()