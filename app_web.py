from datetime import datetime

import streamlit as st
from google import genai

# ── 페이지 설정 ───────────────────────────────────────────────
st.set_page_config(
    page_title="AllWriter",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── API 키 (Streamlit Cloud Secrets 또는 직접 입력) ───────────
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    API_KEY = ""

MODEL_NAME = "gemini-2.5-flash"

# ── 옵션 ─────────────────────────────────────────────────────
CHAR_OPTIONS  = {"500자": 500, "1000자": 1000, "3000자": 3000}
TYPE_OPTIONS  = ["에세이", "보고서", "자기소개서", "시나리오", "블로그 포스트", "기사"]
TONE_OPTIONS  = ["격식체", "비격식체", "전문적", "친근한", "유머러스"]

TYPE_PROMPT: dict[str, str] = {
    "에세이":        "자신의 견해와 논리적 흐름이 살아있는 에세이",
    "보고서":        "객관적 사실과 분석 중심의 보고서",
    "자기소개서":    "1인칭 시점으로 작성하는 자기소개서",
    "시나리오":      "대화체와 지문(S#, 장면 묘사)을 포함한 시나리오",
    "블로그 포스트": "친근하고 읽기 쉬운 블로그 포스트",
    "기사":          "육하원칙에 따른 뉴스 기사",
}

TONE_PROMPT: dict[str, str] = {
    "격식체":   "격식 있고 공식적인 어조로",
    "비격식체": "편안하고 자연스러운 비격식 어조로",
    "전문적":   "전문적이고 논리적인 어조로",
    "친근한":   "친근하고 따뜻한 어조로",
    "유머러스": "유머와 위트를 담아",
}


# ── TextGenerator ────────────────────────────────────────────
class TextGenerator:
    def __init__(self, api_key: str) -> None:
        self._client = genai.Client(api_key=api_key)

    def _build_prompt(self, topic: str, char_count: int, text_type: str, tone: str) -> str:
        type_desc = TYPE_PROMPT.get(text_type, text_type)
        tone_desc = TONE_PROMPT.get(tone, tone)
        return (
            f"다음 주제에 대해 한국어로 {tone_desc} {type_desc}를 작성해 주세요.\n"
            f"주제: {topic}\n"
            f"분량: 약 {char_count}자\n\n"
            f"요구사항:\n"
            f"- '{text_type}' 형식과 구조에 맞게 작성\n"
            f"- {tone_desc} 어조를 유지\n"
            f"- 약 {char_count}자 분량을 지켜주세요\n"
            f"- 불필요한 메타 설명이나 안내 문구 없이 본문만 출력"
        )

    def stream(self, topic: str, char_count: int, text_type: str, tone: str):
        prompt = self._build_prompt(topic, char_count, text_type, tone)
        for chunk in self._client.models.generate_content_stream(
            model=MODEL_NAME, contents=prompt
        ):
            if chunk.text:
                yield chunk.text

    def stream_modify(self, original: str, request: str):
        prompt = (
            f"아래 글을 수정 요청에 맞게 수정해 주세요.\n\n"
            f"[원본 글]\n{original}\n\n"
            f"[수정 요청]\n{request}\n\n"
            f"요구사항:\n"
            f"- 수정 요청 사항만 반영하고, 나머지 내용·형식·어조는 유지해 주세요\n"
            f"- 불필요한 메타 설명 없이 수정된 본문만 출력"
        )
        for chunk in self._client.models.generate_content_stream(
            model=MODEL_NAME, contents=prompt
        ):
            if chunk.text:
                yield chunk.text


# ── 세션 상태 초기화 ──────────────────────────────────────────
if "history" not in st.session_state:
    st.session_state.history = []
if "current_result" not in st.session_state:
    st.session_state.current_result = ""


# ── 사이드바 (히스토리) ───────────────────────────────────────
with st.sidebar:
    st.markdown("## 히스토리")
    st.caption(f"총 {len(st.session_state.history)}건")
    st.divider()

    if not st.session_state.history:
        st.caption("아직 생성된 글이 없습니다.")
    else:
        for i, item in enumerate(st.session_state.history):
            short_topic = item["topic"][:22] + "…" if len(item["topic"]) > 22 else item["topic"]
            with st.container():
                if st.button(
                    f"**{short_topic}**  \n"
                    f"*{item['text_type']} · {item['char_count']}자 · {item['tone']}*  \n"
                    f"*{item['timestamp']}*",
                    key=f"hist_{i}",
                    use_container_width=True,
                ):
                    st.session_state.current_result = item["result"]
                    st.rerun()


# ── 메인 헤더 ─────────────────────────────────────────────────
st.markdown("# ✦ AllWriter")
st.caption("Gemini AI가 주제에 맞는 글을 작성해 드립니다")

# API 키 미설정 시 경고
if not API_KEY:
    st.warning(
        "Gemini API 키가 설정되지 않았습니다.  \n"
        "배포 환경: Streamlit Cloud의 **Secrets**에 `GEMINI_API_KEY`를 추가하세요.  \n"
        "로컬 실행: `.streamlit/secrets.toml`에 `GEMINI_API_KEY = \"키값\"` 를 추가하세요.",
        icon="⚠️",
    )
    st.stop()

generator = TextGenerator(API_KEY)

st.divider()

# ── 입력 영역 ─────────────────────────────────────────────────
topic = st.text_input(
    "주제",
    placeholder="글로 작성할 주제를 입력하세요",
    label_visibility="collapsed",
)

col1, col2, col3 = st.columns([1, 2, 2])
with col1:
    char_key = st.radio("분량", list(CHAR_OPTIONS.keys()), index=1, horizontal=True)
with col2:
    text_type = st.radio("글 종류", TYPE_OPTIONS, index=0, horizontal=True)
with col3:
    tone = st.radio("어조", TONE_OPTIONS, index=0, horizontal=True)

char_count = CHAR_OPTIONS[char_key]

generate_clicked = st.button("✦  생성", type="primary", use_container_width=False)

st.divider()

# ── 생성 처리 ─────────────────────────────────────────────────
if generate_clicked:
    if not topic.strip():
        st.error("주제를 입력해 주세요.")
    else:
        st.markdown(
            f"**생성 중** — {text_type} · {char_count}자 · {tone}"
        )
        try:
            full_text = st.write_stream(
                generator.stream(topic.strip(), char_count, text_type, tone)
            )
            st.session_state.current_result = full_text
            st.session_state.history.insert(0, {
                "topic": topic.strip(),
                "text_type": text_type,
                "char_count": char_count,
                "tone": tone,
                "result": full_text,
                "timestamp": datetime.now().strftime("%H:%M"),
            })
            st.rerun()
        except Exception as e:
            st.error(f"오류가 발생했습니다:\n\n{e}")

# ── 결과 영역 ─────────────────────────────────────────────────
if st.session_state.current_result:
    result = st.session_state.current_result
    chars = len(result.replace("\n", "").replace(" ", ""))

    col_title, col_chars, col_save = st.columns([6, 2, 1])
    with col_title:
        st.markdown("**생성된 글**")
    with col_chars:
        st.caption(f"{chars:,}자")
    with col_save:
        st.download_button(
            "⬇ 저장", data=result,
            file_name="allwriter_result.txt",
            mime="text/plain",
            use_container_width=True,
        )

    # 결과 텍스트 (st.code = 오른쪽 상단에 복사 버튼 자동 제공)
    st.code(result, language="")

    # ── 수정 요청 ──
    st.divider()
    st.markdown("**수정 요청**")

    col_mod, col_btn = st.columns([8, 1])
    with col_mod:
        modify_req = st.text_input(
            "수정 요청",
            placeholder="수정할 내용을 입력하세요  (예: 더 짧게, 결론을 바꿔줘, 격식체로 수정)",
            label_visibility="collapsed",
        )
    with col_btn:
        modify_clicked = st.button("수정", use_container_width=True)

    if modify_clicked:
        if not modify_req.strip():
            st.error("수정 요청 내용을 입력해 주세요.")
        else:
            st.markdown(f"**수정 중** — {modify_req}")
            try:
                modified = st.write_stream(
                    generator.stream_modify(result, modify_req.strip())
                )
                st.session_state.current_result = modified
                st.session_state.history.insert(0, {
                    "topic": f"[수정] {modify_req[:30]}",
                    "text_type": text_type,
                    "char_count": char_count,
                    "tone": tone,
                    "result": modified,
                    "timestamp": datetime.now().strftime("%H:%M"),
                })
                st.rerun()
            except Exception as e:
                st.error(f"수정 중 오류가 발생했습니다:\n\n{e}")
