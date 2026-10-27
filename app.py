import streamlit as st
from pathlib import Path
from streamlit_option_menu import option_menu
import home
import info
import statis

# 브라우저 탭 제목과 아이콘을 지정하고 넓은 화면으로 표시합니다.
st.set_page_config(page_title="전남광주 관광 여행", page_icon="🌊", layout="wide")
# 공통 CSS를 불러와 홈·관광정보·통계 화면에 여름 바다 스타일을 적용합니다.
st.markdown(
    f"<style>{Path(__file__).with_name('style.css').read_text(encoding='utf-8')}</style>",
    unsafe_allow_html=True,
)

# 상단 메뉴를 만들고 선택한 메뉴 이름을 selected에 저장합니다.
selected = option_menu( 
    menu_title="전남광주통합특별시 관광지  ",
    options=['홈','관광정보','통계'],
    icons=["house","info-circle",'bar-chart'],
    menu_icon="cast",
    default_index=0,
    orientation="horizontal",
    styles={
        "container": {"padding": "12px", "background-color": "#ffffff", "border-radius": "20px"},
        "menu-title": {"color": "#075985", "font-weight": "700"},
        "icon": {"color": "#0284c7"},
        "nav-link": {"color": "#164e63", "border-radius": "12px", "--hover-color": "#e0f2fe"},
        "nav-link-selected": {"background-color": "#0369a1", "color": "#ffffff"},
    },
)

# 선택한 메뉴에 해당하는 파일의 화면 함수를 실행합니다.
if selected =='홈':
    home.home()
elif selected == '관광정보':
    info.info()
elif selected == '통계':
    statis.statis()
