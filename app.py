import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ================= 1. 页面基础设置 =================
st.set_page_config(page_title="杜邦分析诊断系统", layout="wide")
st.title("杜邦分析交互式财务诊断系统")

# ================= 2. 基础数据与计算函数 =================
# 默认模拟数据
default_data = pd.DataFrame({
    "期间": ["2022年", "2023年"],
    "营业收入": [120000, 150000],
    "净利润": [9600, 8400],
    "期初总资产": [150000, 160000],
    "期末总资产": [160000, 190000],
    "期初股东权益": [60000, 65000],
    "期末股东权益": [65000, 70000]
})

# 计算衍生指标
def calculate_dupont(df):
    df["平均总资产"] = (df["期初总资产"] + df["期末总资产"]) / 2
    df["平均股东权益"] = (df["期初股东权益"] + df["期末股东权益"]) / 2
    df["销售净利率"] = df["净利润"] / df["营业收入"]
    df["总资产周转率"] = df["营业收入"] / df["平均总资产"]
    df["权益乘数"] = df["平均总资产"] / df["平均股东权益"]
    df["ROE"] = df["销售净利率"] * df["总资产周转率"] * df["权益乘数"]
    return df

# 连环替代法归因
def sequential_substitution(m0, t0, l0, m1, t1, l1):
    roe0 = m0 * t0 * l0
    roe1 = m1 * t1 * l1
    r1 = m1 * t0 * l0
    effect_m = r1 - roe0
    r2 = m1 * t1 * l0
    effect_t = r2 - r1
    r3 = m1 * t1 * l1
    effect_l = r3 - r2
    return {
        "基期ROE": roe0, "报告期ROE": roe1, "总变动": roe1 - roe0,
        "销售净利率贡献": effect_m, "总资产周转率贡献": effect_t, "权益乘数贡献": effect_l
    }

# ================= 3. 网页布局 =================
tab1, tab2 = st.tabs(["📈 数据与结构分解", "🔍 归因诊断分析"])

# ----------------- Tab 1: 数据与结构分解 -----------------
with tab1:
    col_data, col_chart = st.columns([1, 1.2]) # 左边表格，右边图表
    
    with col_data:
        st.subheader("1. 基础财务数据（双击修改）")
        # 允许用户在网页上直接改数字
        edited_data = st.data_editor(default_data, hide_index=True, use_container_width=True, num_rows="fixed")
        
        # 动态计算
        updated_dupont_df = calculate_dupont(edited_data.copy())
        
        st.subheader("2. 杜邦分析衍生指标")
        st.dataframe(
            updated_dupont_df[["期间", "销售净利率", "总资产周转率", "权益乘数", "ROE"]].style.format({
                "销售净利率": "{:.2%}", "总资产周转率": "{:.4f}", "权益乘数": "{:.4f}", "ROE": "{:.2%}"
            }), 
            hide_index=True, use_container_width=True
        )

    with col_chart:
        st.subheader("3. 杜邦树状图 (Treemap)")
        # 选择查看哪一年的分解
        selected_year = st.selectbox("选择要查看的年份：", updated_dupont_df["期间"].tolist(), index=1)
        
        # 取出该年的数据
        row = updated_dupont_df[updated_dupont_df["期间"] == selected_year].iloc[0]
        
        # 构建 Plotly Treemap 所需的层级数据 (通过 id 和 parent 建立关系)
        tree_data = pd.DataFrame({
            "id": ["ROE", "净利率", "周转率", "乘数", "净利润", "营收1", "营收2", "总资产1", "总资产2", "股东权益"],
            "parent": ["", "ROE", "ROE", "ROE", "净利率", "净利率", "周转率", "周转率", "乘数", "乘数"],
            "label": ["ROE", "销售净利率", "总资产周转率", "权益乘数", "净利润", "营业收入", "营业收入", "平均总资产", "平均总资产", "平均股东权益"],
            "value": [row["ROE"]*10000, row["销售净利率"]*100, row["总资产周转率"]*100, row["权益乘数"]*100, 
                      row["净利润"], row["营业收入"], row["营业收入"], row["平均总资产"], row["平均总资产"], row["平均股东权益"]]
        })
        
        # 画图
        fig_tree = px.treemap(tree_data, path=['parent', 'label'], values='value',
                              color='value', color_continuous_scale='Blues', 
                              title=f"{selected_year} 杜邦分解结构 (面积代表绝对数值规模)")
        fig_tree.update_traces(textinfo="label+value")
        st.plotly_chart(fig_tree, use_container_width=True)


# ----------------- Tab 2: 归因诊断分析 -----------------
with tab2:
    # 拿到最新算出的数据
    updated_dupont_df = calculate_dupont(edited_data.copy())
    row0 = updated_dupont_df.iloc[0]
    row1 = updated_dupont_df.iloc[1]
    
    attribution = sequential_substitution(
        row0["销售净利率"], row0["总资产周转率"], row0["权益乘数"],
        row1["销售净利率"], row1["总资产周转率"], row1["权益乘数"]
    )
    
    st.subheader("连环替代法归因结果")
    
    col1, col2, col3 = st.columns(3)
    col1.metric(f"{row0['期间']} ROE", f"{attribution['基期ROE']*100:.2f}%")
    col2.metric(f"{row1['期间']} ROE", f"{attribution['报告期ROE']*100:.2f}%", f"{attribution['总变动']*100:.2f}%")
    
    st.write("---")
    
    # 画瀑布图
    st.subheader("ROE 变动归因瀑布图")
    fig_waterfall = go.Figure(go.Waterfall(
        name="归因", orientation="v",
        measure=["absolute", "relative", "relative", "relative", "total"],
        x=["基期 ROE", "净利率影响", "周转率影响", "权益乘数影响", "报告期 ROE"],
        y=[attribution['基期ROE']*100, attribution['销售净利率贡献']*100, 
           attribution['总资产周转率贡献']*100, attribution['权益乘数贡献']*100, 
           attribution['报告期ROE']*100],
        textposition="outside",
        text=[f"{val:.2f}%" for val in [attribution['基期ROE']*100, attribution['销售净利率贡献']*100, 
                                        attribution['总资产周转率贡献']*100, attribution['权益乘数贡献']*100, 
                                        attribution['报告期ROE']*100]],
        connector={"line": {"color": "rgb(63, 63, 63)"}},
        increasing={"marker": {"color": "#2ca02c"}}, # 正贡献绿色
        decreasing={"marker": {"color": "#d62728"}}, # 负贡献红色
        totals={"marker": {"color": "#1f77b4"}}      # 总数值蓝色
    ))
    fig_waterfall.update_layout(yaxis_title="ROE (%)", showlegend=False)
    st.plotly_chart(fig_waterfall, use_container_width=True)
    
    st.write("---")
    st.write("**💡 系统自动诊断结论：**")
    st.info(f"ROE 从 **{attribution['基期ROE']*100:.2f}%** 变化到 **{attribution['报告期ROE']*100:.2f}%**（变动 {attribution['总变动']*100:.2f}%）。"
            f"其中，最主要的驱动因素是销售净利率（贡献 {attribution['销售净利率贡献']*100:.2f}%）。")