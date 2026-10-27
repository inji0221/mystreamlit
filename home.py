import streamlit as st
from pathlib import Path


def home():

    # 실행 위치와 관계없이 home.py 옆 assets 폴더에서 대표 그림을 찾습니다.
    image_path = Path(__file__).parent / "assets" / "jindo_bridge_illustration.png"
    if image_path.exists():
        st.image(
            str(image_path),
            use_container_width=True,
            caption="진도대교와 푸른 바다를 표현한 AI 생성 그림",
        )
    else:
        st.info("그림 파일을 찾을 수 없습니다.")

    # 대표 그림 아래에 여행지 소개 문구를 표시합니다.
    st.subheader("전남광주통합특별시로 떠나는 특별한 여행")

    st.write("""
    전남광주통합특별시는 아름다운 바다와 섬, 풍부한 자연환경,
    다양한 문화유산과 맛있는 남도 음식을 만날 수 있는
    대표적인 국내 여행지입니다.

    여수, 순천, 목포, 담양, 신안 등 지역마다
    다양한 관광 명소를 찾아 여행을 즐겨보세요

    전남광주통합특별시 관광정보에서는 관광지
    다양한 관광 정보를 확인할 수 있습니다.
    """)

