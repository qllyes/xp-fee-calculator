import streamlit as st
import os
import sys

# --- Path Setup ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))

if project_root not in sys.path:
    sys.path.append(project_root)

# Page Config
st.set_page_config(page_title="新品铺货费计算器", page_icon="💰", layout="wide")

# Load Config with Cache
@st.cache_data(show_spinner=False)
def get_config(path):
    from src.core.config_loader import load_config
    return load_config(path)

@st.cache_data(show_spinner=False)
def get_store_master(path):
    from src.core.store_manager import load_store_master
    return load_store_master(path)

@st.cache_data(show_spinner=False)
def get_xp_mapping(path):
    from src.core.store_manager import load_xp_mapping
    return load_xp_mapping(path)

@st.cache_data(show_spinner=False)
def get_region_map(path):
    import pandas as pd  # 延迟导入
    if os.path.exists(path):
        return pd.read_excel(path, engine='openpyxl')
    return None

@st.cache_data(show_spinner=False)
def get_dim_metadata(path):
    import json
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def main():
    # 延迟导入核心库
    from src.core.store_manager import calc_auto_counts, extract_manual_counts
    from src.core.calculator import calculate_fee
    import pandas as pd

    if "config" not in st.session_state:
        try:
            config_path = os.path.join(project_root, "config", "coefficients.xlsx")
            st.session_state["config"] = get_config(config_path)
        except Exception as e:
            st.error(f"无法加载配置文件: {e}")
            st.stop()
    
    config = st.session_state["config"]
    
    # --- 优化后的混合布局 CSS ---
    st.markdown("""
        <style>
        /* Popover 菜单样式 - 紧凑版 */
        div[data-testid="stPopoverBody"] {
            padding: 8px 6px !important;
            min-width: 120px !important;
            max-width: 150px !important;
        }

       div[data-testid="stPopoverBody"] button {
            background: transparent !important;
            border: none !important;
            padding: 2px 10px !important;  /* ← 更小的垂直 padding */
            margin: -2px 0 !important;     /* ← 使用负 margin 进一步压缩 */
            font-size: 0.9rem !important;
            width: 100% !important;
            text-align: left !important;
            line-height: 1.1 !important;   /* ← 更紧凑的行高 */
            min-height: 28px !important;   /* ← 限制最小高度 */
        }

        div[data-testid="stPopoverBody"] button:hover {
            background-color: #f0f2f6 !important;
        }

        /* 减少 Popover 内部垂直间距 */
        div[data-testid="stPopoverBody"] > div {
            gap: 0 !important;
        }
        
        /* 1. 顶部留白调整 */
        .block-container {
            padding-top: 1.5rem !important;
            padding-bottom: 2rem !important;
        }

        /* 2. 压缩垂直间距 */
        div[data-testid="stVerticalBlock"] > div {
            gap: 0.5rem !important;
        }
        
        /* 3. 压缩输入框本身的高度 and 边距 */
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
            margin-bottom: 0.2rem !important;
            padding-bottom: 0rem !important;
        }

        /* 8. 向上提拉 Tab 栏，消除默认的大间隙 */
        .stTabs {
            margin-top: -1.5rem !important;
        }

        /* 9. 自定义 secondary 按钮的背景色 */
        button[kind="secondary"] {
            background-color: #F0F2F6 !important;
            border: 1px solid #D1D5DB !important;
            color: #31333F !important;
        }
        
        /* 悬停效果 */
        button[kind="secondary"]:hover {
            background-color: #E6E9EF !important;
            border-color: #B0B5BE !important;
        }

        /* 10. 限制多选框最大高度 */
        .stMultiSelect div[data-baseweb="select"] > div {
            max-height: 46px !important;
            overflow-y: auto !important;
        }
        /* Popover 按钮字体大小 */
        button[data-testid="baseButton-secondary"] {
            font-size: 0.85rem !important;
        }

        </style>
    """, unsafe_allow_html=True)

    # 标题栏
    st.markdown("<div style='font-size: 1.8rem; font-weight: 700; margin-bottom: 15px;'>新品铺货费计算器</div>", unsafe_allow_html=True)

    # --- Data Loading (Auto) ---
    store_master_path = os.path.join(project_root, "data", "store_master.xlsx")
    region_map_path = os.path.join(project_root, "data", "region_map.xlsx")
    metadata_path = os.path.join(project_root, "data", "dim_metadata.json")
    
    store_master_df = None
    region_map_df = None
    dim_metadata = None
    update_time = "未知"

    if os.path.exists(store_master_path):
        try:
            store_master_df = get_store_master(store_master_path)
            if "门店表更新时间" in store_master_df.columns:
                update_time = str(store_master_df["门店表更新时间"].iloc[0])
        except Exception as e:
            st.error(f"加载门店数据失败: {e}")
            
    if os.path.exists(region_map_path):
        region_map_df = get_region_map(region_map_path)
        
    if os.path.exists(metadata_path):
        dim_metadata = get_dim_metadata(metadata_path)
        if dim_metadata and "更新时间" in dim_metadata:
            update_time = dim_metadata["更新时间"]
    
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

    # --- Tab 1: 单品计算器 ---
    with tab1:
        spacer_left, col_center, spacer_right = st.columns([1.5, 7, 1.5])
        
        with col_center:
            with st.container(border=True):
                st.markdown("<div style='font-size: 18px; font-weight: bold; margin-bottom: 10px;'>📝 通道计算器 -- 输入信息</div>", unsafe_allow_html=True)
                
                procurement_type = st.selectbox(
                    "统采or地采", 
                    ["统采", "地采"],
                    index=0,
                )

                c1, c2 = st.columns(2)
                with c1:
                    category = st.selectbox("新品大类", list(config["base_fees"].keys()))       
                with c2:
                    supplier_type = st.selectbox("供应商类型", list(config["supplier_type_coeffs"].keys()))

                # --- 动态布局逻辑开始 ---
                # 1. 准备选项
                all_return_policies = list(config["return_policy_coeffs"].keys()) 
                complex_policies = list(config.get("return_ratio_rules", {}).keys())
                all_return_policies = sorted(list(set(all_return_policies + complex_policies)))
                
                # 2. 预判布局：检查 session_state 或使用默认值
                # 如果这是第一次渲染，st.session_state 还没有这个 key，我们取列表第一个作为默认
                current_policy_val = st.session_state.get("widget_return_policy", all_return_policies[0])
                is_complex_policy = current_policy_val in complex_policies

                # 3. 动态定义列：如果是复杂条件，这行分3列；否则分2列
                if is_complex_policy:
                    # 比例调整：SKU(1) : 退货条件(1.2) : 退货比例(0.8)
                    c3, c4, c4_extra = st.columns([1, 1.2, 0.8])
                else:
                    c3, c4 = st.columns(2)
                    c4_extra = None

                with c3:
                    sku_count = st.number_input("同一供应商单次引进SKU数", min_value=1, value=1)
                
                with c4:
                    # 注意：必须设置 key，以便在 rerun 时能通过 session_state 获取最新值
                    return_policy = st.selectbox("退货条件", all_return_policies, key="widget_return_policy")

                return_ratio_val = 0.0
                if c4_extra:
                    with c4_extra:
                        # 更加简洁的 Label，不需要 st.info 干扰
                        return_ratio_val = st.number_input(
                            "退货比例 (%)", 
                            min_value=0.0, 
                            max_value=100.0, 
                            value=100.0,
                            step=0.1,
                            # 使用 help 替代 info
                            help="请输入比例以匹配折扣档位"
                        )
                # --- 动态布局逻辑结束 ---

                c5, c6 = st.columns(2)
                with c5:
                    cost_price = st.number_input("底价 (元)", min_value=0.0, value=10.0)
                with c6:
                    gross_margin = st.number_input("预估成交综合毛利率 (%)", min_value=0.0, max_value=100.0, value=40.0)               
                c7, c8 = st.columns(2)
                with c7:
                    payment = st.selectbox("付款方式", list(config["payment_coeffs"].keys()))
                with c8:
                    if xp_map:
                        xp_options = sorted(list(xp_map.keys()))
                    else:
                        xp_options = ["无 (未找到映射表)"]
                    selected_xp_category = st.selectbox("处方类别", xp_options)

                target_xp_code = xp_map.get(selected_xp_category) if xp_map else None
                
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
                    horizontal=True
                )
                
                channel = "自定义"
                custom_sub_mode = "手动输入"
                manual_counts = {}
                selected_filters = {}
                
                if "标准通道" in channel_mode:
                    color_selection = st.selectbox(
                        "选择标准通道范围",
                        ["全量门店", "小店及以上", "中店及以上", "大店及以上", "旗舰店及以上", "超级旗舰店"],
                        label_visibility="collapsed"
                    )
                    channel = color_selection.split()[-1] 
                else:
                    channel = "自定义"
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
                        st.caption("请选择筛选条件 (为空表示全选)")
                        filter_df = region_map_df if region_map_df is not None else store_master_df
                        if filter_df is not None:
                            with st.expander("选择省公司/省份/城市", expanded=True):
                                col_reg1, col_reg2, col_reg3 = st.columns(3)
                                if "filter_company" not in st.session_state: st.session_state["filter_company"] = []
                                if "filter_province" not in st.session_state: st.session_state["filter_province"] = []
                                if "filter_city" not in st.session_state: st.session_state["filter_city"] = []
                                sel_company = st.session_state["filter_company"]
                                sel_province = st.session_state["filter_province"]
                                sel_city = st.session_state["filter_city"]
                                def get_mask(col_name, selected_values):
                                    if not selected_values: return pd.Series(True, index=filter_df.index)
                                    return filter_df[col_name].isin(selected_values)
                                mask_company_cond = get_mask("省公司", sel_company)
                                mask_province_cond = get_mask("省份", sel_province)
                                mask_city_cond = get_mask("城市", sel_city)
                                opts_company = sorted(filter_df[mask_province_cond & mask_city_cond]["省公司"].dropna().unique())
                                opts_province = sorted(filter_df[mask_company_cond & mask_city_cond]["省份"].dropna().unique())
                                opts_city = sorted(filter_df[mask_company_cond & mask_province_cond]["城市"].dropna().unique())
                                def sanitize(current, valid): return [x for x in current if x in valid]
                                st.session_state["filter_company"] = sanitize(st.session_state["filter_company"], opts_company)
                                st.session_state["filter_province"] = sanitize(st.session_state["filter_province"], opts_province)
                                st.session_state["filter_city"] = sanitize(st.session_state["filter_city"], opts_city)
                                with col_reg1: selected_filters["省公司"] = st.multiselect("省公司", options=opts_company, key="filter_company", placeholder="全部 (默认)")
                                with col_reg2: selected_filters["省份"] = st.multiselect("省份", options=opts_province, key="filter_province", placeholder="全部 (默认)")
                                with col_reg3: selected_filters["城市"] = st.multiselect("城市", options=opts_city, key="filter_city", placeholder="全部 (默认)")
                            
                            with st.expander("门店属性筛选", expanded=True):
                                sales_scale_opts = dim_metadata["销售规模"] if dim_metadata else ["超级旗舰店", "旗舰店", "大店", "中店", "小店", "成长店"]
                                selected_filters["销售规模"] = st.multiselect("销售规模", sales_scale_opts, default=[], placeholder="全部 (默认)")
                                col_attr1, col_attr2 = st.columns(2)
                                with col_attr1:
                                    opts = dim_metadata["店龄店型"] if dim_metadata else []
                                    selected_filters["店龄店型"] = st.multiselect("店龄店型", opts, placeholder="全部 (默认)")
                                with col_attr2:
                                    opts = dim_metadata["客流商圈"] if dim_metadata else []
                                    selected_filters["客流商圈"] = st.multiselect("客流商圈", opts, placeholder="全部 (默认)")
                                col_attr3, col_attr4 = st.columns(2)
                                with col_attr3:
                                    opts = dim_metadata["行政区划等级"] if dim_metadata else []
                                    selected_filters["行政区划等级"] = st.multiselect("行政区划等级", opts, placeholder="全部 (默认)")
                                with col_attr4:
                                    opts = dim_metadata["公域O2O店型"] if dim_metadata else []
                                    selected_filters["公域O2O店型"] = st.multiselect("公域O2O店型", opts, placeholder="全部 (默认)")
                                st.markdown("---")
                                col_bool1, col_bool2, col_bool3 = st.columns(3)
                                insurance_opts = ["全部"] + (dim_metadata.get("是否医保店", ["是", "否"]) if dim_metadata else ["是", "否"])
                                o2o_opts = ["全部"] + (dim_metadata.get("是否O2O门店", ["是", "否"]) if dim_metadata else ["是", "否"])
                                coor_opts = ["全部"] + (dim_metadata.get("是否统筹店", ["是", "否"]) if dim_metadata else ["是", "否"])
                                with col_bool1: selected_filters["是否医保店"] = st.selectbox("是否医保店", insurance_opts)
                                with col_bool2: selected_filters["是否O2O门店"] = st.selectbox("是否O2O门店", o2o_opts)
                                with col_bool3: selected_filters["是否统筹店"] = st.selectbox("是否统筹店", coor_opts)

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
                    st.error("❌ 未找到门店主数据，无法进行自动计算！")
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
                        "退货条件": return_policy,
                        "退货比例(%)": return_ratio_val # [新增] 传入比例
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
                        elif channel == "自定义" and custom_sub_mode == "标签筛选":
                            is_auto_calc_mode = True
                            store_counts = calc_auto_counts(
                                store_master_df, 
                                channel, 
                                restricted_xp_code=target_xp_code,
                                war_zone=selected_war_zone,
                                filters=selected_filters
                            )
                            if target_xp_code:
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
                                .metric-box { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 10px; }
                                .metric-label { font-size: 0.9rem; color: #666; margin-bottom: 5px; }
                                .metric-value { font-size: 1.8rem; font-weight: 700; }
                            </style>
                            """
                            st.markdown(css_style, unsafe_allow_html=True)
                            col_res1, col_res2, col_res3 = st.columns([1, 1, 1.2]) 
                            with col_res1:
                                st.markdown(f"""<div class="metric-box"><div class="metric-label">理论总新品铺货费(元)</div><div class="metric-value" style="color: #333;">{int(result['theoretical_fee']):,}</div></div>""", unsafe_allow_html=True)
                            with col_res2:
                                st.markdown(f"""<div class="metric-box"><div class="metric-label">折扣</div><div class="metric-value" style="color: #333;">{result['discount_factor']:.2f}</div></div>""", unsafe_allow_html=True)
                            with col_res3:
                                st.markdown(f"""<div class="metric-box"><div class="metric-label">折后总新品铺货费(元)</div><div class="metric-value" style="color: #D32F2F; ">{int(result['final_fee']):,}</div></div>""", unsafe_allow_html=True)
                            if result.get('is_floor_triggered'):
                                procurement = result.get('procurement_type', '未知标准')
                                floor_src = result.get('floor_source_desc', '')
                                msg_suffix = f"({floor_src})" if floor_src else ""
                                st.caption(f"⚠️ 已触发最低兜底费用 ({procurement}): {result['min_floor']}元 {msg_suffix}")
                            st.divider()
                            
                            with st.expander("👁️ 查看计算过程详情", expanded=False):
                                col_detail_2, col_detail_1 = st.columns(2)
                                
                                with col_detail_2:
                                    st.markdown(f"**门店费率计算 (单店)**")
                                    st.json(result["scale_fees"])
                                
                                with col_detail_1:
                                    st.markdown(f"**基础系数**")
                                    st.markdown(f"- **新品大类系数**: {result['coeffs']['category_coeff']}")
                                    st.markdown(f"- **供应商类型系数**: {result['coeffs']['supplier_coeff']}")
                                    st.markdown(f"- **付款方式系数**: {result['coeffs']['payment_coeff']}")
                                    st.markdown(f"- **退货条件折扣**: {result['coeffs']['return_policy_discount']}")
                                    st.markdown(f"**计算公式**")
                                    st.latex(r"单店费用 = 底价 \times SKUs \times 基础 \times 规模系数")
                            
                            # 门店分布展示
                            st.markdown("---")
                            st.markdown(f"**📊 纳入计算的门店分布** (共 {sum(store_counts.values())} 家)")
                            
                            if is_auto_calc_mode and excluded_count > 0:
                                st.warning(f"⚠️ 注意：根据处方类别 `{selected_xp_category}` (代码: {target_xp_code})，已自动剔除 {excluded_count} 家不具备经营资质的门店。")

                            # 准备饼图数据
                            pie_data = []
                            for scale, count in store_counts.items():
                                if count > 0:
                                    pie_data.append({"规模": scale, "数量": count})
                            
                            if pie_data:
                                import plotly.express as px
                                df_pie = pd.DataFrame(pie_data)
                                color_map = {
                                    "超级旗舰店": "#B71C1C",
                                    "旗舰店": "#D32F2F",
                                    "大店": "#F57C00",
                                    "中店": "#FFB300",
                                    "小店": "#7CB342",
                                    "成长店": "#8D6E63"
                                }
                                fig = px.pie(
                                    df_pie, 
                                    names='规模', 
                                    values='数量', 
                                    hole=0.4,
                                    color='规模',
                                    color_discrete_map=color_map
                                )
                                fig.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=250)
                                st.plotly_chart(fig, use_container_width=True)
                            else:
                                st.info("暂无门店数据")

                    except Exception as e:
                        st.error(f"计算过程发生错误: {str(e)}")
                        import traceback
                        st.text(traceback.format_exc())

    # --- Tab 2: 批量计算器 ---
    with tab2:
        from src.ui.batch_processor import show_batch_processor
        show_batch_processor(store_master_df, region_map_df, config, xp_map)

if __name__ == "__main__":
    main()