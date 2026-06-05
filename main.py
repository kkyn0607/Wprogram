import threading
from datetime import datetime
from tkinter import filedialog

import customtkinter as ctk
from google import genai

# ============================================================
# 설정: 아래 API 키에 본인의 Gemini API 키를 입력하세요.
# ============================================================
API_KEY = "AQ.Ab8RN6KwMx2fwZakWPzB1zJ8vJOv6xN9k7VfYI8m5hL_irG9rw"
MODEL_NAME = "gemini-2.5-flash"

APP_TITLE     = "AllWriter"
WINDOW_WIDTH  = 1100
WINDOW_HEIGHT = 800
SIDEBAR_WIDTH = 220

# ── 폰트 ──────────────────────────────────────────────────────
FONT = "Malgun Gothic"

# ── 컬러 팔레트 ───────────────────────────────────────────────
BG_ROOT          = "#0F0F1A"
BG_SIDEBAR       = "#13131F"
BG_CARD          = "#1A1A2E"
BG_INPUT         = "#0F0F1A"
BG_HISTORY_ITEM  = "#1E1E32"
BG_HISTORY_HOVER = "#252540"
BORDER           = "#2A2A42"
ACCENT           = "#6C5CE7"
ACCENT_HOVER     = "#5A4BD1"
TEXT_PRIMARY     = "#E2E8F0"
TEXT_SECONDARY   = "#8B8FA8"
TEXT_RESULT      = "#CDD6F4"
DOT_IDLE         = "#3A3A52"
DOT_BUSY         = "#6C5CE7"
DOT_DONE         = "#10B981"
DOT_ERROR        = "#EF4444"
BTN_SEC          = "#2A2A42"
BTN_SEC_HOVER    = "#3A3A58"

# ── 선택 옵션 ─────────────────────────────────────────────────
CHAR_OPTIONS = ["500자", "1000자", "3000자"]
TYPE_OPTIONS = ["에세이", "보고서", "자기소개서", "시나리오", "블로그 포스트", "기사"]
TONE_OPTIONS = ["격식체", "비격식체", "전문적", "친근한", "유머러스"]

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


# ─────────────────────────────────────────────────────────────
class TextGenerator:
    """Google Gemini API를 사용해 주제 기반 텍스트를 생성합니다."""

    def __init__(self, api_key: str, model_name: str = MODEL_NAME) -> None:
        if not api_key or api_key == "YOUR_GEMINI_API_KEY_HERE":
            raise ValueError("API 키를 main.py 상단의 API_KEY 변수에 설정해 주세요.")
        self._client = genai.Client(api_key=api_key)
        self._model_name = model_name

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

    def stream_modify(self, original_text: str, request: str):
        """기존 글을 수정 요청에 따라 스트리밍으로 수정합니다."""
        if not original_text.strip():
            raise ValueError("수정할 글이 없습니다.")
        if not request.strip():
            raise ValueError("수정 요청 내용을 입력해 주세요.")
        prompt = (
            f"아래 글을 수정 요청에 맞게 수정해 주세요.\n\n"
            f"[원본 글]\n{original_text}\n\n"
            f"[수정 요청]\n{request}\n\n"
            f"요구사항:\n"
            f"- 수정 요청 사항만 반영하고, 나머지 내용·형식·어조는 유지해 주세요\n"
            f"- 불필요한 메타 설명 없이 수정된 본문만 출력"
        )
        for chunk in self._client.models.generate_content_stream(
            model=self._model_name,
            contents=prompt,
        ):
            text = getattr(chunk, "text", None)
            if text:
                yield text

    def stream(self, topic: str, char_count: int, text_type: str, tone: str):
        """텍스트 청크를 실시간으로 yield 합니다."""
        topic = (topic or "").strip()
        if not topic:
            raise ValueError("주제는 비어 있을 수 없습니다.")
        prompt = self._build_prompt(topic, char_count, text_type, tone)
        for chunk in self._client.models.generate_content_stream(
            model=self._model_name,
            contents=prompt,
        ):
            text = getattr(chunk, "text", None)
            if text:
                yield text


# ─────────────────────────────────────────────────────────────
class MainWindow:
    """AllWriter 메인 윈도우."""

    def __init__(self) -> None:
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.root = ctk.CTk()
        self.root.title(APP_TITLE)
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.minsize(860, 620)
        self.root.configure(fg_color=BG_ROOT)

        self._text_generator = TextGenerator(API_KEY, MODEL_NAME)
        self._job_id = 0
        self._is_running = False
        self._history: list[dict] = []
        self._current_result = ""

        self._build_ui()

    def run(self) -> None:
        self.root.mainloop()

    # ── 최상위 레이아웃 ───────────────────────────────────────

    def _build_ui(self) -> None:
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=0, minsize=SIDEBAR_WIDTH)

        self._build_main_panel()
        self._build_sidebar()

    # ── 메인 패널 ─────────────────────────────────────────────

    def _build_main_panel(self) -> None:
        main = ctk.CTkFrame(self.root, fg_color="transparent")
        main.grid(row=0, column=0, sticky="nsew")
        main.grid_rowconfigure(3, weight=1)
        main.grid_columnconfigure(0, weight=1)

        self._build_header(main)
        self._build_input_card(main)
        self._build_status_bar(main)
        self._build_result_card(main)

    def _build_header(self, parent: ctk.CTkFrame) -> None:
        header = ctk.CTkFrame(parent, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=32, pady=(28, 8))
        header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            header, text="✦",
            font=ctk.CTkFont(family=FONT, size=18),
            text_color=ACCENT, width=26,
        ).grid(row=0, rowspan=2, column=0, padx=(0, 12), sticky="ns")

        ctk.CTkLabel(
            header, text=APP_TITLE,
            font=ctk.CTkFont(family=FONT, size=24, weight="bold"),
            text_color=TEXT_PRIMARY, anchor="w",
        ).grid(row=0, column=1, sticky="w")

        ctk.CTkLabel(
            header, text="Gemini AI가 주제에 맞는 글을 작성해 드립니다",
            font=ctk.CTkFont(family=FONT, size=12),
            text_color=TEXT_SECONDARY, anchor="w",
        ).grid(row=1, column=1, sticky="w", pady=(2, 0))

    def _build_input_card(self, parent: ctk.CTkFrame) -> None:
        card = ctk.CTkFrame(
            parent, fg_color=BG_CARD, corner_radius=16,
            border_width=1, border_color=BORDER,
        )
        card.grid(row=1, column=0, sticky="ew", padx=32, pady=(14, 0))
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card, text="주제 입력",
            font=ctk.CTkFont(family=FONT, size=11, weight="bold"),
            text_color=TEXT_SECONDARY, anchor="w",
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(16, 6))

        self.topic_entry = ctk.CTkEntry(
            card,
            placeholder_text="글로 작성할 주제를 입력하세요 (Enter 또는 생성 버튼)",
            height=46, font=ctk.CTkFont(family=FONT, size=14),
            fg_color=BG_INPUT, border_color=BORDER, border_width=1,
            corner_radius=10, text_color=TEXT_PRIMARY,
        )
        self.topic_entry.grid(row=1, column=0, sticky="ew", padx=(20, 10), pady=(0, 14))
        self.topic_entry.bind("<Return>", lambda _: self._on_generate_clicked())

        self.generate_button = ctk.CTkButton(
            card, text="생성", width=100, height=46,
            font=ctk.CTkFont(family=FONT, size=14, weight="bold"),
            fg_color=ACCENT, hover_color=ACCENT_HOVER, corner_radius=10,
            command=self._on_generate_clicked,
        )
        self.generate_button.grid(row=1, column=1, padx=(0, 20), pady=(0, 14))

        ctk.CTkFrame(card, fg_color=BORDER, height=1).grid(
            row=2, column=0, columnspan=2, sticky="ew", padx=20
        )

        opts = ctk.CTkFrame(card, fg_color="transparent")
        opts.grid(row=3, column=0, columnspan=2, sticky="ew", padx=20, pady=(14, 18))
        opts.grid_columnconfigure(1, weight=1)

        _seg_kw = dict(
            font=ctk.CTkFont(family=FONT, size=12),
            fg_color=BG_INPUT,
            selected_color=ACCENT, selected_hover_color=ACCENT_HOVER,
            unselected_color=BG_INPUT, unselected_hover_color=BTN_SEC_HOVER,
            text_color=TEXT_PRIMARY, corner_radius=20, height=34,
        )

        # ── 분량 ──
        ctk.CTkLabel(
            opts, text="분량",
            font=ctk.CTkFont(family=FONT, size=11, weight="bold"),
            text_color=TEXT_SECONDARY, width=52, anchor="w",
        ).grid(row=0, column=0, padx=(0, 10), pady=(0, 10))

        self.char_seg = ctk.CTkSegmentedButton(opts, values=CHAR_OPTIONS, **_seg_kw)
        self.char_seg.set("1000자")
        self.char_seg.grid(row=0, column=1, sticky="w", pady=(0, 10))

        # ── 글 종류 ──
        ctk.CTkLabel(
            opts, text="글 종류",
            font=ctk.CTkFont(family=FONT, size=11, weight="bold"),
            text_color=TEXT_SECONDARY, width=52, anchor="w",
        ).grid(row=1, column=0, padx=(0, 10), pady=(0, 10))

        self.type_seg = ctk.CTkSegmentedButton(opts, values=TYPE_OPTIONS, **_seg_kw)
        self.type_seg.set("에세이")
        self.type_seg.grid(row=1, column=1, sticky="w", pady=(0, 10))

        # ── 어조 ──
        ctk.CTkLabel(
            opts, text="어조",
            font=ctk.CTkFont(family=FONT, size=11, weight="bold"),
            text_color=TEXT_SECONDARY, width=52, anchor="w",
        ).grid(row=2, column=0, padx=(0, 10))

        self.tone_seg = ctk.CTkSegmentedButton(opts, values=TONE_OPTIONS, **_seg_kw)
        self.tone_seg.set("격식체")
        self.tone_seg.grid(row=2, column=1, sticky="w")

    def _build_status_bar(self, parent: ctk.CTkFrame) -> None:
        bar = ctk.CTkFrame(parent, fg_color="transparent")
        bar.grid(row=2, column=0, sticky="ew", padx=32, pady=(12, 4))

        self.status_dot = ctk.CTkLabel(
            bar, text="●", font=ctk.CTkFont(family=FONT, size=10),
            text_color=DOT_IDLE, width=16,
        )
        self.status_dot.grid(row=0, column=0, padx=(0, 8))

        self.status_label = ctk.CTkLabel(
            bar, text="주제를 입력하고 생성 버튼을 눌러주세요",
            font=ctk.CTkFont(family=FONT, size=12),
            text_color=TEXT_SECONDARY, anchor="w",
        )
        self.status_label.grid(row=0, column=1, sticky="w")

    def _build_result_card(self, parent: ctk.CTkFrame) -> None:
        card = ctk.CTkFrame(
            parent, fg_color=BG_CARD, corner_radius=16,
            border_width=1, border_color=BORDER,
        )
        card.grid(row=3, column=0, sticky="nsew", padx=32, pady=(0, 28))
        card.grid_rowconfigure(1, weight=1)
        card.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(card, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 8))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header, text="생성된 글",
            font=ctk.CTkFont(family=FONT, size=11, weight="bold"),
            text_color=TEXT_SECONDARY, anchor="w",
        ).grid(row=0, column=0, sticky="w")

        self.char_count_label = ctk.CTkLabel(
            header, text="",
            font=ctk.CTkFont(family=FONT, size=11),
            text_color=TEXT_SECONDARY,
        )
        self.char_count_label.grid(row=0, column=1, padx=(0, 8))

        self.save_button = ctk.CTkButton(
            header, text="저장", width=60, height=28,
            font=ctk.CTkFont(family=FONT, size=11),
            fg_color=BTN_SEC, hover_color=BTN_SEC_HOVER,
            corner_radius=8, text_color=TEXT_SECONDARY,
            command=self._on_save_clicked,
        )
        self.save_button.grid(row=0, column=2, padx=(0, 6))

        self.copy_button = ctk.CTkButton(
            header, text="복사", width=60, height=28,
            font=ctk.CTkFont(family=FONT, size=11),
            fg_color=BTN_SEC, hover_color=BTN_SEC_HOVER,
            corner_radius=8, text_color=TEXT_SECONDARY,
            command=self._on_copy_clicked,
        )
        self.copy_button.grid(row=0, column=3)

        self.result_textbox = ctk.CTkTextbox(
            card, wrap="word",
            font=ctk.CTkFont(family=FONT, size=14),
            fg_color=BG_INPUT, corner_radius=10, border_spacing=14,
            text_color=TEXT_RESULT,
            scrollbar_button_color=BORDER,
            scrollbar_button_hover_color=ACCENT,
        )
        self.result_textbox.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 12))
        self.result_textbox.configure(state="disabled")

        # ── 수정 요청 영역 ──
        ctk.CTkFrame(card, fg_color=BORDER, height=1).grid(
            row=2, column=0, sticky="ew", padx=20
        )

        modify_row = ctk.CTkFrame(card, fg_color="transparent")
        modify_row.grid(row=3, column=0, sticky="ew", padx=20, pady=(12, 16))
        modify_row.grid_columnconfigure(0, weight=0)
        modify_row.grid_columnconfigure(1, weight=1)
        modify_row.grid_columnconfigure(2, weight=0)

        ctk.CTkLabel(
            modify_row, text="수정 요청",
            font=ctk.CTkFont(family=FONT, size=11, weight="bold"),
            text_color=TEXT_SECONDARY, width=60, anchor="w",
        ).grid(row=0, column=0, padx=(0, 10))

        self.modify_entry = ctk.CTkEntry(
            modify_row,
            placeholder_text="수정할 내용을 입력하세요  (예: 더 짧게, 결론을 바꿔줘, 격식체로 수정)",
            height=38, font=ctk.CTkFont(family=FONT, size=13),
            fg_color=BG_INPUT, border_color=BORDER, border_width=1,
            corner_radius=10, text_color=TEXT_PRIMARY, state="disabled",
        )
        self.modify_entry.grid(row=0, column=1, sticky="ew", padx=(0, 10))
        self.modify_entry.bind("<Return>", lambda _: self._on_modify_clicked())

        self.modify_button = ctk.CTkButton(
            modify_row, text="수정", width=80, height=38,
            font=ctk.CTkFont(family=FONT, size=13, weight="bold"),
            fg_color=BTN_SEC, hover_color=BTN_SEC_HOVER,
            corner_radius=10, text_color=TEXT_SECONDARY, state="disabled",
            command=self._on_modify_clicked,
        )
        self.modify_button.grid(row=0, column=2)

    # ── 사이드바 (히스토리) ───────────────────────────────────

    def _build_sidebar(self) -> None:
        sidebar = ctk.CTkFrame(
            self.root, fg_color=BG_SIDEBAR,
            corner_radius=0, border_width=1, border_color=BORDER,
        )
        sidebar.grid(row=0, column=1, sticky="nsew")
        sidebar.grid_rowconfigure(1, weight=1)
        sidebar.grid_columnconfigure(0, weight=1)

        title_row = ctk.CTkFrame(sidebar, fg_color="transparent")
        title_row.grid(row=0, column=0, sticky="ew", padx=14, pady=(22, 10))
        title_row.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            title_row, text="히스토리",
            font=ctk.CTkFont(family=FONT, size=13, weight="bold"),
            text_color=TEXT_PRIMARY, anchor="w",
        ).grid(row=0, column=0, sticky="w")

        self._history_count_label = ctk.CTkLabel(
            title_row, text="0건",
            font=ctk.CTkFont(family=FONT, size=11),
            text_color=TEXT_SECONDARY,
        )
        self._history_count_label.grid(row=0, column=1)

        self._history_scroll = ctk.CTkScrollableFrame(
            sidebar, fg_color="transparent",
            scrollbar_button_color=BORDER,
            scrollbar_button_hover_color=ACCENT,
        )
        self._history_scroll.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 14))

        self._refresh_history_ui()

    def _refresh_history_ui(self) -> None:
        for w in self._history_scroll.winfo_children():
            w.destroy()

        self._history_count_label.configure(text=f"{len(self._history)}건")

        if not self._history:
            ctk.CTkLabel(
                self._history_scroll,
                text="아직 생성된 글이\n없습니다",
                font=ctk.CTkFont(family=FONT, size=12),
                text_color=DOT_IDLE,
            ).pack(pady=40)
            return

        for entry in self._history:
            self._create_history_item(entry)

    def _create_history_item(self, entry: dict) -> None:
        item = ctk.CTkFrame(
            self._history_scroll,
            fg_color=BG_HISTORY_ITEM, corner_radius=10,
            border_width=1, border_color=BORDER,
            cursor="hand2",
        )
        item.pack(fill="x", padx=2, pady=(0, 6))
        item.grid_columnconfigure(0, weight=1)

        short_topic = entry["topic"][:20] + "…" if len(entry["topic"]) > 20 else entry["topic"]

        topic_lbl = ctk.CTkLabel(
            item, text=short_topic,
            font=ctk.CTkFont(family=FONT, size=12, weight="bold"),
            text_color=TEXT_PRIMARY, anchor="w",
        )
        topic_lbl.grid(row=0, column=0, sticky="w", padx=12, pady=(10, 2))

        meta_lbl = ctk.CTkLabel(
            item,
            text=f"{entry['text_type']} · {entry['char_count']}자 · {entry['tone']}",
            font=ctk.CTkFont(family=FONT, size=10),
            text_color=TEXT_SECONDARY, anchor="w",
        )
        meta_lbl.grid(row=1, column=0, sticky="w", padx=12, pady=(0, 8))

        time_lbl = ctk.CTkLabel(
            item, text=entry["timestamp"],
            font=ctk.CTkFont(family=FONT, size=10),
            text_color=DOT_IDLE,
        )
        time_lbl.grid(row=0, column=1, rowspan=2, padx=(0, 10), sticky="e")

        result = entry["result"]
        for widget in (item, topic_lbl, meta_lbl, time_lbl):
            widget.bind("<Button-1>", lambda _e, r=result: self._load_history_result(r))
            widget.bind("<Enter>", lambda _e, f=item: f.configure(fg_color=BG_HISTORY_HOVER))
            widget.bind("<Leave>", lambda _e, f=item: f.configure(fg_color=BG_HISTORY_ITEM))

    def _add_to_history(self, topic: str, text_type: str, char_count: int, tone: str, result: str) -> None:
        self._history.insert(0, {
            "topic": topic,
            "text_type": text_type,
            "char_count": char_count,
            "tone": tone,
            "result": result,
            "timestamp": datetime.now().strftime("%H:%M"),
        })
        self._refresh_history_ui()

    def _load_history_result(self, result: str) -> None:
        self._set_result_text(result)
        chars = len(result.replace("\n", "").replace(" ", ""))
        self._set_status(f"히스토리 불러옴  ·  {chars:,}자", DOT_DONE)
        self._set_result_available(True)

    # ── 상태 제어 ─────────────────────────────────────────────

    def _set_result_available(self, available: bool) -> None:
        """수정 요청 컨트롤의 활성/비활성을 제어합니다."""
        state = "normal" if available else "disabled"
        self.modify_entry.configure(state=state)
        self.modify_button.configure(
            state=state,
            fg_color=ACCENT if available else BTN_SEC,
            hover_color=ACCENT_HOVER if available else BTN_SEC_HOVER,
            text_color=TEXT_PRIMARY if available else TEXT_SECONDARY,
        )

    def _set_busy(self, is_busy: bool) -> None:
        self._is_running = is_busy
        state = "disabled" if is_busy else "normal"
        self.topic_entry.configure(state=state)
        self.generate_button.configure(state=state)
        self.char_seg.configure(state=state)
        self.type_seg.configure(state=state)
        self.tone_seg.configure(state=state)
        # 수정 버튼은 결과가 있을 때만 활성화하므로 별도 처리
        if is_busy:
            self.modify_entry.configure(state="disabled")
            self.modify_button.configure(state="disabled")

    def _set_status(self, text: str, dot_color: str) -> None:
        self.status_label.configure(text=text)
        self.status_dot.configure(text_color=dot_color)

    def _set_result_text(self, text: str) -> None:
        self._current_result = text
        self.result_textbox.configure(state="normal")
        self.result_textbox.delete("1.0", "end")
        self.result_textbox.insert("end", text)
        self.result_textbox.configure(state="disabled")
        chars = len(text.replace("\n", "").replace(" ", ""))
        self.char_count_label.configure(text=f"{chars:,}자" if text else "")

    def _stream_start(self) -> None:
        """스트리밍 시작 전 텍스트박스를 초기화합니다."""
        self._current_result = ""
        self.result_textbox.configure(state="normal")
        self.result_textbox.delete("1.0", "end")
        self.char_count_label.configure(text="")

    def _stream_append(self, chunk: str) -> None:
        """청크를 텍스트박스 끝에 추가하고 스크롤합니다."""
        self._current_result += chunk
        self.result_textbox.insert("end", chunk)
        self.result_textbox.see("end")
        chars = len(self._current_result.replace("\n", "").replace(" ", ""))
        self.char_count_label.configure(text=f"{chars:,}자")

    def _stream_end(self) -> None:
        """스트리밍 완료 후 텍스트박스를 읽기 전용으로 전환하고 수정 컨트롤을 활성화합니다."""
        self.result_textbox.configure(state="disabled")
        self._set_result_available(True)

    def _get_char_count(self) -> int:
        return int(self.char_seg.get().replace("자", ""))

    # ── 이벤트 처리 ───────────────────────────────────────────

    def _on_generate_clicked(self) -> None:
        if self._is_running:
            return

        topic = self.topic_entry.get().strip()
        if not topic:
            self._set_status("주제를 입력해 주세요.", DOT_ERROR)
            return

        char_count = self._get_char_count()
        text_type  = self.type_seg.get()
        tone       = self.tone_seg.get()

        self._job_id += 1
        job_id = self._job_id

        self._set_busy(True)
        self._set_status(
            f"Gemini가 {text_type}  ·  {char_count}자  ·  {tone}  작성 중...",
            DOT_BUSY,
        )
        self.root.after(0, self._stream_start)

        def worker() -> None:
            try:
                for chunk in self._text_generator.stream(topic, char_count, text_type, tone):
                    if job_id != self._job_id:
                        return
                    c = chunk
                    self.root.after(0, lambda t=c: self._stream_append(t))

                self.root.after(0, lambda: self._handle_stream_done(
                    job_id, topic, text_type, char_count, tone
                ))
            except Exception as e:
                msg = str(e)
                self.root.after(0, lambda m=msg: self._handle_error(job_id, m))

        threading.Thread(target=worker, daemon=True).start()

    def _on_modify_clicked(self) -> None:
        if self._is_running:
            return
        request = self.modify_entry.get().strip()
        if not request:
            self._set_status("수정 요청 내용을 입력해 주세요.", DOT_ERROR)
            return
        if not self._current_result:
            self._set_status("수정할 글이 없습니다.", DOT_ERROR)
            return

        original = self._current_result
        self._job_id += 1
        job_id = self._job_id

        self._set_busy(True)
        self._set_status(f"Gemini가 수정 중...  ({request[:20]}{'…' if len(request) > 20 else ''})", DOT_BUSY)
        self.root.after(0, self._stream_start)

        def worker() -> None:
            try:
                for chunk in self._text_generator.stream_modify(original, request):
                    if job_id != self._job_id:
                        return
                    c = chunk
                    self.root.after(0, lambda t=c: self._stream_append(t))
                self.root.after(0, lambda: self._handle_modify_done(job_id, request))
            except Exception as e:
                msg = str(e)
                self.root.after(0, lambda m=msg: self._handle_error(job_id, m))

        threading.Thread(target=worker, daemon=True).start()

    def _handle_modify_done(self, job_id: int, request: str) -> None:
        if job_id != self._job_id:
            return
        self._stream_end()
        chars = len(self._current_result.replace("\n", "").replace(" ", ""))
        self._set_status(f"수정 완료  ·  {chars:,}자", DOT_DONE)
        self._set_busy(False)
        # 수정 요청 입력창 초기화
        self.modify_entry.delete(0, "end")
        # 수정 결과도 히스토리에 추가
        self._add_to_history(
            f"[수정] {request[:30]}",
            self.type_seg.get(), self._get_char_count(),
            self.tone_seg.get(), self._current_result,
        )

    def _on_copy_clicked(self) -> None:
        if not self._current_result:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(self._current_result)
        self.copy_button.configure(text="복사됨!", text_color=DOT_DONE)
        self.root.after(1500, lambda: self.copy_button.configure(
            text="복사", text_color=TEXT_SECONDARY
        ))

    def _on_save_clicked(self) -> None:
        if not self._current_result:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("텍스트 파일", "*.txt"), ("모든 파일", "*.*")],
            title="파일 저장",
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self._current_result)
            self.save_button.configure(text="저장됨!", text_color=DOT_DONE)
            self.root.after(1500, lambda: self.save_button.configure(
                text="저장", text_color=TEXT_SECONDARY
            ))
        except Exception as e:
            self._set_status(f"저장 오류: {e}", DOT_ERROR)

    def _handle_stream_done(
        self, job_id: int, topic: str, text_type: str,
        char_count: int, tone: str
    ) -> None:
        if job_id != self._job_id:
            return
        self._stream_end()
        chars = len(self._current_result.replace("\n", "").replace(" ", ""))
        self._set_status(f"완료  ·  {chars:,}자 생성", DOT_DONE)
        self._set_busy(False)
        self._add_to_history(topic, text_type, char_count, tone, self._current_result)

    def _handle_error(self, job_id: int, message: str) -> None:
        if job_id != self._job_id:
            return
        self._set_result_text(f"오류가 발생했습니다.\n\n{message}")
        self._set_status("오류 — 아래 내용을 확인해 주세요.", DOT_ERROR)
        self._set_busy(False)


def main() -> None:
    app = MainWindow()
    app.run()


if __name__ == "__main__":
    main()
