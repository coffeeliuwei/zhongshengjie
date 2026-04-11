#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知识图谱可视化查看器
运行: streamlit run graph_viewer.py
"""

import streamlit as st
import json
from pathlib import Path
from typing import Dict, List, Any

# 配置
VECTORSTORE_DIR = Path(__file__).parent
GRAPH_FILE = VECTORSTORE_DIR / "knowledge_graph.json"

# 页面配置
st.set_page_config(page_title="知识图谱查看器", page_icon="🕸️", layout="wide")

st.title("🕸️ 众生界知识图谱")
st.caption("角色关系、势力网络、时间线事件")


# ============================================================
# 加载数据
# ============================================================


@st.cache_data
def load_graph():
    if not GRAPH_FILE.exists():
        return None

    with open(GRAPH_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


data = load_graph()

if not data:
    st.error("图谱数据不存在，请先运行 `python knowledge_graph.py --save`")
    st.stop()

实体 = data.get("实体", {})
关系 = data.get("关系", [])
统计 = data.get("统计", {})


# ============================================================
# 侧边栏
# ============================================================

with st.sidebar:
    st.header("📊 图谱统计")

    st.metric("实体总数", 统计.get("实体数", 0))
    st.metric("关系总数", 统计.get("关系数", 0))

    st.divider()

    # 实体类型分布
    st.subheader("实体类型分布")
    实体类型 = {}
    for e in 实体.values():
        t = e.get("类型", "未知")
        实体类型[t] = 实体类型.get(t, 0) + 1

    for t, count in sorted(实体类型.items(), key=lambda x: -x[1]):
        st.write(f"  {t}: {count}")

    st.divider()

    # 关系类型分布
    st.subheader("关系类型分布")
    关系类型 = {}
    for r in 关系:
        t = r.get("关系类型", "未知")
        关系类型[t] = 关系类型.get(t, 0) + 1

    for t, count in sorted(关系类型.items(), key=lambda x: -x[1]):
        st.write(f"  {t}: {count}")


# ============================================================
# 主内容区
# ============================================================

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["🔍 实体查询", "🔗 关系网络", "💕 感情关系", "⚔️ 敌对网络", "📅 时间线"]
)


# ============================================================
# Tab 1: 实体查询
# ============================================================

with tab1:
    st.subheader("实体查询")

    col1, col2 = st.columns([1, 2])

    with col1:
        # 类型过滤
        类型列表 = ["全部"] + list(实体类型.keys())
        类型过滤 = st.selectbox("实体类型", 类型列表)

        # 名称搜索
        名称搜索 = st.text_input("名称搜索", "")

    # 过滤实体
    过滤实体 = []
    for id_, e in 实体.items():
        if 类型过滤 != "全部" and e.get("类型") != 类型过滤:
            continue
        if 名称搜索 and 名称搜索 not in e.get("名称", ""):
            continue
        过滤实体.append((id_, e))

    st.info(f"显示 {len(过滤实体)} 个实体")

    # 显示实体
    for id_, e in 过滤实体[:50]:
        with st.expander(f"**{e.get('名称', '未知')}** [{e.get('类型', '未知')}]"):
            # 显示属性
            属性 = e.get("属性", {})
            for key, value in 属性.items():
                st.write(f"**{key}**: {value}")

            # 显示相关关系
            相关关系 = [
                r
                for r in 关系
                if r.get("源实体") == e.get("名称")
                or r.get("目标实体") == e.get("名称")
            ]

            if 相关关系:
                st.write("**相关关系:**")
                for r in 相关关系:
                    方向 = "→" if r.get("源实体") == e.get("名称") else "←"
                    目标 = (
                        r.get("目标实体")
                        if r.get("源实体") == e.get("名称")
                        else r.get("源实体")
                    )
                    st.write(f"  {方向} {r.get('关系类型')}: {目标}")


# ============================================================
# Tab 2: 关系网络
# ============================================================

with tab2:
    st.subheader("关系网络")

    # 选择实体
    实体名称列表 = sorted(set([e.get("名称") for e in 实体.values() if e.get("名称")]))
    selected_entity = st.selectbox("选择实体", [""] + 实体名称列表)

    if selected_entity:
        # 获取相关关系
        相关关系 = [
            r
            for r in 关系
            if r.get("源实体") == selected_entity
            or r.get("目标实体") == selected_entity
        ]

        st.write(f"### {selected_entity} 的关系网络")

        col1, col2 = st.columns(2)

        with col1:
            st.write("**出边关系 (→)**")
            出边 = [r for r in 相关关系 if r.get("源实体") == selected_entity]
            for r in 出边:
                st.write(f"  - {r.get('关系类型')} → **{r.get('目标实体')}**")

        with col2:
            st.write("**入边关系 (←)**")
            入边 = [r for r in 相关关系 if r.get("目标实体") == selected_entity]
            for r in 入边:
                st.write(f"  - **{r.get('源实体')}** → {r.get('关系类型')}")

        # 可视化（简单的文本图）
        st.divider()
        st.write("**关系图:**")

        图文本 = f"```\n{selected_entity}\n"
        for r in 出边:
            图文本 += f"  ├── [{r.get('关系类型')}] → {r.get('目标实体')}\n"
        图文本 += "```"
        st.code(图文本)


# ============================================================
# Tab 3: 感情关系
# ============================================================

with tab3:
    st.subheader("感情关系网络")

    # 筛选感情关系
    感情关系 = [r for r in 关系 if r.get("关系类型") in ["爱慕", "三角关系"]]

    st.write(f"共 {len(感情关系)} 条感情关系")

    # 按关系类型分组显示
    爱慕关系 = [r for r in 感情关系 if r.get("关系类型") == "爱慕"]
    三角关系 = [r for r in 感情关系 if r.get("关系类型") == "三角关系"]

    col1, col2 = st.columns(2)

    with col1:
        st.write("### 💕 爱慕关系")
        for r in 爱慕关系:
            属性 = r.get("属性", {})
            状态 = 属性.get("状态", "")
            冲突 = 属性.get("冲突", "")
            性质 = 属性.get("性质", "")

            额外信息 = []
            if 状态:
                额外信息.append(f"状态: {状态}")
            if 冲突:
                额外信息.append(f"冲突: {冲突}")
            if 性质:
                额外信息.append(f"性质: {性质}")

            信息文本 = f" ({', '.join(额外信息)})" if 额外信息 else ""
            st.write(f"- **{r.get('源实体')}** → {r.get('目标实体')}{信息文本}")

    with col2:
        st.write("### 🔺 三角关系")
        for r in 三角关系:
            第三方 = r.get("属性", {}).get("第三方", "")
            if 第三方:
                st.write(
                    f"- **{r.get('源实体')}** ↔ **{r.get('目标实体')}** ↔ **{第三方}**"
                )


# ============================================================
# Tab 4: 敌对网络
# ============================================================

with tab4:
    st.subheader("敌对网络")

    # 筛选敌对关系
    敌对关系 = [r for r in 关系 if r.get("关系类型") == "敌对"]
    入侵关系 = [r for r in 关系 if r.get("关系类型") == "被入侵"]
    杀死关系 = [r for r in 关系 if r.get("关系类型") == "杀死"]

    tab4a, tab4b, tab4c = st.tabs(["⚔️ 势力敌对", "🤖 入侵关系", "💀 杀死关系"])

    with tab4a:
        st.write(f"共 {len(敌对关系)} 条敌对关系")
        for r in 敌对关系:
            性质 = r.get("属性", {}).get("性质", "")
            st.write(f"- **{r.get('源实体')}** ⟷ **{r.get('目标实体')}** ({性质})")

    with tab4b:
        st.write(f"共 {len(入侵关系)} 条入侵关系")
        for r in 入侵关系:
            程度 = r.get("属性", {}).get("程度", "")
            原因 = r.get("属性", {}).get("原因", "")
            st.write(
                f"- **{r.get('源实体')}** 被 **{r.get('目标实体')}** 入侵 (程度: {程度})"
            )

    with tab4c:
        st.write(f"共 {len(杀死关系)} 条杀死关系")
        for r in 杀死关系:
            原因 = r.get("属性", {}).get("原因", "")
            st.write(
                f"- **{r.get('源实体')}** 杀死 **{r.get('目标实体')}** (原因: {原因})"
            )


# ============================================================
# Tab 5: 时间线
# ============================================================

with tab5:
    st.subheader("时间线")

    # 五大时代
    时代列表 = ["觉醒时代", "蛰伏时代", "风暴时代", "变革时代", "终局时代"]

    for 时代 in 时代列表:
        with st.expander(f"📅 {时代}"):
            # 查找时代事件
            时代事件 = []
            for id_, e in 实体.items():
                if e.get("类型") == "事件" and 时代 in e.get("名称", ""):
                    时代事件.append(e)

            if 时代事件:
                for e in 时代事件:
                    st.write(f"- **{e.get('名称')}**")
            else:
                st.write("暂无事件数据")


# ============================================================
# 页脚
# ============================================================

st.divider()
st.caption("众生界知识图谱查看器 | 基于 ChromaDB + Streamlit")
