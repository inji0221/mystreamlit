import streamlit as st
import pandas as pd
import requests
import os
from html import escape
import folium
from streamlit_folium import st_folium
from openai import OpenAI, OpenAIError

SERVICE_KEY = "0efe02107f87a0a8fe8538368274832de47eda96b6ffc5a01054a53af1fce91f"
API_URL = "https://apis.data.go.kr/B551011/KorService2/areaBasedList2"


# API 응답을 한 시간 동안 캐시해 화면 조작마다 다시 요청하지 않습니다.
@st.cache_data(ttl=3600)
def load_data():
    # 지역 코드 38의 관광지(유형 12)를 첫 페이지에서 최대 1,000개 요청합니다.
    params = {
        "serviceKey": SERVICE_KEY,
        "MobileOS": "ETC",
        "MobileApp": "TourDashboard",
        "_type": "json",
        "areaCode": 38,
        "contentTypeId": 12,
        "numOfRows": 1000,
        "pageNo": 1,
    }
    response = requests.get(API_URL, params=params, timeout=30)
    response.raise_for_status()  # HTTP 오류가 발생하면 화면의 예외 처리로 전달합니다.
    items = response.json()["response"]["body"].get("items") or {}
    records = items.get("item", [])
    # 결과가 한 건(딕셔너리)이어도 목록으로 감싸고, API의 모든 컬럼을 유지합니다.
    df = pd.DataFrame([records] if isinstance(records, dict) else records)
    if df.empty:
        return df
    # 주소의 첫 지역명이 일치하는 관광지만 사용합니다.(홍성군이 코드가 38이지만 전남광주통합특별시가 아닌 경우가 있어 필터링)
    return df.loc[
        df["addr1"].fillna("").str.split().str[0].eq("전남광주통합특별시")
    ].copy()

# 관광지 이름·주소가 같으면 AI 설명을 1시간 동안 재사용합니다.
@st.cache_data(ttl=3600, show_spinner=False)
def get_ai_description(title, address):
    # OPENAI_API_KEY 환경변수로 인증하고 관광지 이름과 주소를 AI에 전달합니다.
    with OpenAI(timeout=30, max_retries=0) as client:
        response = client.responses.create(
            model="gpt-4.1-mini",
            instructions=(
                "관광지의 특징과 볼거리를 한국어로 공백 포함 300자 이내로 설명하세요. "
                "확실하지 않은 정보는 추측하지 말고, 모르는 관광지는 정보가 부족하다고 알려주세요."
                "교통편에 대한 정보도 추가하여 50자이내로 추가로 설명하세요."
                ),
            input=f"관광지: {title}\n주소: {address}",
            max_output_tokens=500,
        )
    text = response.output_text.strip()
    if not text:
        raise ValueError("빈 AI 응답")
    # AI가 길게 답해도 교통편을 포함한 전체 설명을 최대 300자로 제한합니다.
    return text if len(text) <= 300 else text[:299] + "…"


# 관광지 목록 화면을 구성합니다.
def info():
    st.header("🏝️ 전남광주통합특별시 관광지")
    try:
        df = load_data()
    except (requests.RequestException, ValueError, KeyError, TypeError):
        st.error("관광지 정보를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.")
        return
    if df.empty:
        st.info("조회된 관광지가 없습니다.")
        return
    # API의 문자열 유형 코드를 숫자로 바꿔 필터링하고 한글 유형명을 연결합니다.
    df["contenttypeid"] = pd.to_numeric(df["contenttypeid"], errors="coerce")
    type_names = {
        12: "관광지",
        14: "문화시설",
        15: "축제·공연·행사",
        25: "여행코스",
        28: "레포츠",
        32: "숙박",
        38: "쇼핑",
        39: "음식점"
    }
    df["type_name"] = df["contenttypeid"].map(type_names)
    
    # 지역은 API의 areaCode로 제한하고 관광지(12)만 표시합니다.
    df = df.loc[df["contenttypeid"].eq(12)].copy()
    
    # 주소에서 시·군 이름을 추출하고 중복을 제거합니다.
    df["city"] = df["addr1"].str.extract(r"^\S+\s+([가-힣]+[시군])(?:\s|$)", expand=False)
    cities = sorted(df["city"].dropna().unique())
    
 
 
    # 시·군 체크박스를 다섯 열에 배치하고 여러 지역을 함께 선택할 수 있게 합니다.
    selected_cities = []
    with st.popover("원하는 지역 선택하세요", use_container_width=True):
        city_cols = st.columns(5)
        for i, city in enumerate(cities):
            if city_cols[i % 5].checkbox(city, key=f"info_city_{city}"):
                selected_cities.append(city)
    
    # 선택한 지역의 관광지만 표시합니다.
    if selected_cities:
        df = df.loc[df["city"].isin(selected_cities)]
    else:
        st.caption("지역을 선택하면 해당 지역의 관광지만 표시합니다.")

    # 한 페이지에 3열 × 10줄, 최대 30개 카드를 표시합니다.
    if df.empty:
        st.info("조회된 관광지가 없습니다.")
        return
    page_size = 30
    total_pages = (len(df) + page_size - 1) // page_size  # 나머지 카드도 마지막 페이지에 표시합니다.
    page = st.selectbox(
        "페이지",
        range(1, total_pages + 1),
        format_func=lambda number: f"{number} / {total_pages} 페이지",
        key=f"info_page_{'_'.join(selected_cities)}",  # 지역 선택이 바뀌면 페이지 선택도 구분합니다.
    )
    start = (page - 1) * page_size
    st.caption(f"총 {len(df):,}개 중 {start + 1}–{min(start + page_size, len(df))}개 표시")
    page_df = df.iloc[start:start + page_size]  # 현재 페이지에 해당하는 행만 카드로 만듭니다.
    
    # 상세보기 버튼으로 열리는 팝업을 정의합니다.
    @st.dialog("관광지 상세정보", width="large")
    def show_detail(row):
        left, right = st.columns(2)
        with left:
            if pd.notna(row["firstimage"]) and row["firstimage"]:
                st.image(
                    row["firstimage"],
                    use_container_width=True
                )
            st.subheader(row["title"])
            st.write("📍",row["addr1"])
            # 관광 유형을 표시합니다.
            st.write("🏷️",row["type_name"])
    
        # 오른쪽에 AI 관광 안내 영역을 표시합니다.
        with right:
            st.subheader("🤖 AI 관광 안내")
            if not os.getenv("OPENAI_API_KEY"):
                st.info("OPENAI_API_KEY 환경변수를 설정해 주세요.")
            else:
                try:
                    with st.spinner("관광지 설명을 작성하고 있습니다..."):
                        st.info(get_ai_description(row["title"], row["addr1"]))
                except (OpenAIError, ValueError):
                    st.error("AI 설명을 불러오지 못했습니다. API 키와 사용 한도를 확인해 주세요.")

            # 경도(mapx)·위도(mapy)를 숫자로 바꾸고 누락·범위 오류·0 좌표를 제외합니다.
            st.subheader("📍 관광지 위치")
            lat = pd.to_numeric(row.get("mapy", ""), errors="coerce")
            lon = pd.to_numeric(row.get("mapx", ""), errors="coerce")
            if (
                pd.notna(lat) and pd.notna(lon)
                and -90 <= lat <= 90 and -180 <= lon <= 180
                and lat != 0 and lon != 0
            ):
                # 해당 관광지를 중심으로 지도를 만들고 이름이 있는 마커를 추가합니다.
                detail_map = folium.Map(location=[lat, lon], zoom_start=14)
                title = escape(str(row["title"]))
                folium.Marker(
                    location=[lat, lon], tooltip=title, popup=title,
                ).add_to(detail_map)
                # 지도 조작으로 팝업이 불필요하게 다시 실행되지 않도록 반환 이벤트를 비웁니다.
                st_folium(
                    detail_map, use_container_width=True, height=300,
                    returned_objects=[], key=f"detail_map_{row['contentid']}",
                )
            else:
                st.info("이 관광지의 위치 정보가 없습니다.")
    
    # 관광지 카드를 세 열로 배치합니다.
    cols = st.columns(3)
    for i, (_, row) in enumerate(page_df.iterrows()):
        # 각 카드에 관광지 정보와 상세보기 버튼을 표시합니다.
        with cols[i % 3]:
            with st.container(border=True, key=f"tour_card_{row['contentid']}"):
                # API 문자열의 HTML 특수문자를 처리해 카드 안에서 텍스트로 표시합니다.
                title = escape(str(row["title"]))
                address = escape(str(row["addr1"]))
                type_name = escape(str(row["type_name"]))
                # style.css의 tour-card 클래스로 제목·주소 높이와 줄 수를 통일합니다.
                st.markdown(
                    f'<div class="tour-card-content">'
                    f'<h3 class="tour-card-title" title="{title}">{title}</h3>'
                    f'<p class="tour-card-address" title="{address}">📍 {address}</p>'
                    f'<p class="tour-card-type">🏷️ 관광유형: {type_name}</p>'
                    '</div>',
                    unsafe_allow_html=True,
                )
                if st.button("상세보기",key=f"btn_{row['contentid']}"):
                    show_detail(row)
