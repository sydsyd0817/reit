import streamlit as st
st.set_page_config(layout="wide")
import pandas as pd
import altair as alt

st.title("리츠 배당 시뮬레이션")

# 화면을 좌우 2열로 분할
col1, col2 = st.columns([1, 1])

# 왼쪽: 입력 폼
with col1:
    with st.container():
        # 1. 리츠 기본 정보 입력
        st.header("리츠별 정보 입력")
        user_reits = []
        num_reits = st.number_input("리츠 종목 수", min_value=1, max_value=20, value=3)
        for i in range(num_reits):
            cols = st.columns([2, 2, 3])
            with cols[0]:
                name = st.text_input(f"종목명 {i+1}", key=f"name_{i}")
            with cols[1]:
                div_per_share = st.number_input(f"주당 배당금(원) {i+1}", min_value=0, value=0, key=f"div_{i}")
            with cols[2]:
                div_months = st.multiselect(f"배당월 {i+1}", options=list(range(1,13)), default=[], key=f"months_{i}")
            if name and div_per_share > 0 and div_months:
                user_reits.append({
                    "name": name,
                    "div_per_share": div_per_share,
                    "div_months": div_months
                })

        # 2. 연도 범위 선택
        st.header("시뮬레이션 연도 범위")
        start_year = st.number_input("시작 연도", min_value=2000, max_value=2100, value=2024)
        end_year = st.number_input("종료 연도", min_value=start_year, max_value=2100, value=2027)
        years = list(range(start_year, end_year+1))

        # 3. 연도별 매입 계획 및 추가매입금액 입력
        global_buy_plan = {}
        global_invest_plan = {}
        for r in user_reits:
            st.subheader(f"{r['name']} 매입 계획 및 추가매입금액")
            buy_plan = []
            invest_plan = []
            for y in years:
                col1_, col2_, col3_, col4_, col5_ = st.columns([2,2,2,2,2])
                with col1_:
                    qty = st.number_input(f"{y}년 매입 수량", min_value=0, value=0, key=f"{r['name']}_{y}_qty")
                with col2_:
                    price = st.number_input(f"{y}년 주가(원)", min_value=0, value=0, key=f"{r['name']}_{y}_price")
                with col3_:
                    invest = qty * price
                    st.number_input(f"{y}년 매입금액(원)", min_value=0, value=invest, key=f"{r['name']}_{y}_invest", disabled=True)
                with col4_:
                    naver_search_url = f"https://finance.naver.com/search/search.naver?query={r['name']}" if r['name'] else "https://finance.naver.com/"
                    st.markdown(f"[네이버 주식]({naver_search_url})", unsafe_allow_html=True)
                with col5_:
                    fn_guide_url = "https://comp.fnguide.com/SVO2/ASP/SVD_Main.asp?gicode=A348950&MenuYn=Y"
                    st.markdown(f"[FnGuide]({fn_guide_url})", unsafe_allow_html=True)
                buy_plan.append(qty)
                invest_plan.append(invest)
            global_buy_plan[r['name']] = buy_plan
            global_invest_plan[r['name']] = invest_plan

# 오른쪽: 시뮬레이션 및 결과 시각화
with col2:
    with st.container():
        if 'user_reits' in locals() and user_reits:
            # 4. 연도별/월별 보유량 및 배당금 계산
            records = []
            reits_names = [r["name"] for r in user_reits]
            for y_idx, y in enumerate(years):
                for m in range(1, 13):
                    row = {"연도": y, "월": m}
                    total_div = 0
                    for r in user_reits:
                        shares = sum(global_buy_plan[r['name']][:y_idx+1])
                        div = shares * r["div_per_share"] if m in r["div_months"] else 0
                        row[r["name"]] = div
                        total_div += div
                    row["총배당금"] = total_div
                    records.append(row)

            df = pd.DataFrame(records)
            df.columns = df.columns.str.strip()  # 🔧 컬럼 공백 제거
            df["누적배당금"] = df.groupby("연도")["총배당금"].cumsum()
            df["전체누적배당금"] = df["총배당금"].cumsum()

            # 5. 연도별 투자원금 및 수익률 계산
            year_invest, year_div, year_profit, year_rate = [], [], [], []
            for y_idx, y in enumerate(years):
                invest = sum(sum(global_invest_plan[r['name']][:y_idx+1]) for r in user_reits)
                div = df[df["연도"] == y]["총배당금"].sum()
                profit = div
                rate = (profit / invest * 100) if invest > 0 else 0
                year_invest.append(invest)
                year_div.append(div)
                year_profit.append(profit)
                year_rate.append(rate)

            year_df = pd.DataFrame({
                "연도": years,
                "누적투자원금": year_invest,
                "연간배당금": year_div,
                "연간수익률(%)": year_rate
            })

            # 6. 시각화
            st.header("연도별/월별 배당금 시뮬레이션")
            for y in years:
                st.subheader(f"{y}년 배당 캘린더")
                df_y = df[df["연도"] == y]
                df_melt = df_y.melt(id_vars=["월"], value_vars=reits_names, var_name="종목", value_name="배당금")
                chart = alt.Chart(df_melt).mark_bar().encode(
                    x=alt.X('월:O', title='월'),
                    y=alt.Y('배당금:Q', stack='zero'),
                    color=alt.Color('종목:N'),
                    tooltip=['종목', '배당금']
                ).properties(width=700, height=400)
                st.altair_chart(chart, use_container_width=True)
                st.write(df_y[["월"] + reits_names + ["총배당금", "누적배당금"]])

            # ✅ 누적 배당금 라인 차트 수정
            df["연도-월"] = df["연도"].astype(str) + "-" + df["월"].astype(str).str.zfill(2)
            st.header("전체 누적 배당금 추이")
            st.line_chart(df.set_index("연도-월")[["누적배당금"]])

            st.header("연도별 투자원금 및 수익률")
            st.dataframe(year_df)
            st.bar_chart(year_df.set_index("연도")[["연간수익률(%)"]])
        else:
            st.info("왼쪽에서 리츠 정보를 입력하세요.")
