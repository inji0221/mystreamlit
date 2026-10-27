import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import folium
from html import escape
from streamlit_folium import st_folium
from info import load_data


def statis():
    st.header("📊 관광지 통계")
    st.caption("관광공사 API에서 조회된 관광지 기준입니다. 최대 1,000개이며 전체 현황과 다를 수 있습니다.")

    # 소개 화면과 같은 API 캐시를 재사용하고 통계 가공용 복사본을 만듭니다.
    try:
        df = load_data().copy()
    except (requests.RequestException, ValueError, KeyError, TypeError):
        st.error("관광지 정보를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.")
        return
    if df.empty:
        st.info("조회된 관광지가 없습니다.")
        return

    # 주소에서 시·군을 추출하고 지역별 관광지 개수를 집계합니다.
    df["city"] = df["addr1"].fillna("").str.extract(
        r"^\S+\s+([가-힣]+[시군])(?:\s|$)", expand=False
    )
    city_counts = df["city"].value_counts().rename_axis("지역").reset_index(name="관광지 수")

    # 조회된 관광지 수와 확인 가능한 시·군 수를 요약 카드로 표시합니다.
    left, right = st.columns(2)
    left.metric("전체 관광지 수 (조회 기준)", f"{len(df):,}개")
    right.metric("지역 수 (시·군)", f"{df['city'].nunique()}개")

    st.subheader("시·군별 관광지 수")
    if city_counts.empty:
        st.info("주소에서 시·군 정보를 찾을 수 없습니다.")
    else:
        # 가로 막대그래프를 만들고 관광지가 많은 지역을 위쪽에 배치합니다.
        fig = px.bar(city_counts, x="관광지 수", y="지역", orientation="h", text="관광지 수")
        fig.update_layout(
            height=675,
            font={"size": 18},
            yaxis={"categoryorder": "total ascending"},
        )
        fig.update_xaxes(
            tickfont={"size": 18},
            title_font={"size": 21},
            range=[0, city_counts["관광지 수"].max() * 1.15],  # 막대 오른쪽 숫자를 위한 여유 공간입니다.
        )
        fig.update_yaxes(tickfont={"size": 18}, title_font={"size": 21})
        # 관광지 개수를 막대 바깥에 가로로 표시합니다.
        fig.update_traces(
            textposition="outside",
            textangle=0,
            textfont={"size": 18},
            cliponaxis=False,
        )
        st.plotly_chart(fig, use_container_width=True)
    # 시·군을 추출하지 못한 주소는 지역별 집계에서 빠졌음을 안내합니다.
    missing_cities = df["city"].isna().sum()
    if missing_cities:
        st.caption(f"시·군을 확인할 수 없는 관광지 {missing_cities}개는 지역별 통계에서 제외했습니다.")

    st.subheader("관광지 위치 분포")
    # 위도·경도를 숫자로 변환하고 잘못된 값은 결측값으로 처리합니다.
    locations = df.reindex(columns=["mapy", "mapx"]).apply(pd.to_numeric, errors="coerce")
    locations = locations.rename(columns={"mapy": "lat", "mapx": "lon"})
    # 좌표 범위를 벗어나거나 위치 미등록을 뜻하는 0인 좌표는 지도에서 제외합니다.
    locations = locations.loc[
        locations["lat"].between(-90, 90)
        & locations["lon"].between(-180, 180)
        & locations["lat"].ne(0)
        & locations["lon"].ne(0)
    ]
    if locations.empty:
        st.info("지도에 표시할 위치 정보가 없습니다.")
    else:
        # 체크박스로 관광지 마커를 켜거나 끄고, 좌표 중앙값을 지도 중심으로 사용합니다.
        show_markers = st.checkbox("물방울 마커 표시", value=True)
        locations = locations.copy()
        locations["title"] = df.loc[locations.index, "title"].fillna("이름 없는 관광지")
        tour_map = folium.Map(
            location=[locations["lat"].median(), locations["lon"].median()],
            zoom_start=9,
        )
        if show_markers:
            for _, row in locations.iterrows():
                title = escape(str(row["title"]))  # 관광지 이름을 HTML 대신 텍스트로 표시합니다.
                folium.Marker(
                    location=[row["lat"], row["lon"]],
                    tooltip=title,
                    popup=title,
                ).add_to(tour_map)
        # Folium 지도를 Streamlit에 표시하며 지도 조작 이벤트는 반환하지 않습니다.
        st_folium(tour_map, use_container_width=True, height=500, returned_objects=[])
    st.caption(
        f"위치 정보가 유효한 관광지 {len(locations):,}개 · "
        f"위치 정보 누락 또는 오류 {len(df) - len(locations):,}개 제외"
    )
