import threading
from typing import Optional

import customtkinter as ctk
from PIL import Image

from .constants import (
    APP_TITLE,
    IMAGE_HEIGHT,
    IMAGE_WIDTH,
    PLACEHOLDER_TOPIC,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)
from .generator_service import DummyGeneratorService


class MainWindow:
    def __init__(self) -> None:
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        self.root = ctk.CTk()
        self.root.title(APP_TITLE)
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.minsize(WINDOW_WIDTH, WINDOW_HEIGHT)

        self._generator = DummyGeneratorService()
        self._job_id = 0
        self._is_running = False
        self._ctk_image_ref: Optional[ctk.CTkImage] = None

        self._build_ui()

    def run(self) -> None:
        self.root.mainloop()

    def _build_ui(self) -> None:
        self.root.grid_rowconfigure(2, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(self.root)
        top.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))
        top.grid_columnconfigure(0, weight=1)
        top.grid_columnconfigure(1, weight=0)

        self.topic_entry = ctk.CTkEntry(top, placeholder_text=PLACEHOLDER_TOPIC)
        self.topic_entry.grid(row=0, column=0, sticky="ew", padx=(12, 6), pady=10)

        self.generate_button = ctk.CTkButton(top, text="생성", command=self._on_generate_clicked)
        self.generate_button.grid(row=0, column=1, sticky="e", padx=(6, 12), pady=10)

        status = ctk.CTkFrame(self.root)
        status.grid(row=1, column=0, sticky="ew", padx=12, pady=6)
        status.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(status, text="대기 중")
        self.status_label.grid(row=0, column=0, sticky="w", padx=12, pady=(10, 6))

        self.progress_bar = ctk.CTkProgressBar(status)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 10))

        results = ctk.CTkFrame(self.root)
        results.grid(row=2, column=0, sticky="nsew", padx=12, pady=(6, 12))
        results.grid_columnconfigure(0, weight=1)
        results.grid_columnconfigure(1, weight=1)
        results.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(results)
        left.grid(row=0, column=0, sticky="nsew", padx=(12, 6), pady=12)
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)

        left_title = ctk.CTkLabel(left, text="텍스트 결과")
        left_title.grid(row=0, column=0, sticky="w", padx=12, pady=(10, 6))

        self.text_result = ctk.CTkTextbox(left, wrap="word")
        self.text_result.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.text_result.configure(state="disabled")

        right = ctk.CTkFrame(results)
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 12), pady=12)
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        right_title = ctk.CTkLabel(right, text="이미지 결과")
        right_title.grid(row=0, column=0, sticky="w", padx=12, pady=(10, 6))

        self.image_result = ctk.CTkLabel(
            right,
            text="이미지가 없습니다.",
            anchor="center",
        )
        self.image_result.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))

    def _set_busy(self, is_busy: bool) -> None:
        self._is_running = is_busy
        state = "disabled" if is_busy else "normal"
        self.topic_entry.configure(state=state)
        self.generate_button.configure(state=state)

    def _reset_results(self) -> None:
        self.text_result.configure(state="normal")
        self.text_result.delete("1.0", "end")
        self.text_result.configure(state="disabled")

        self.image_result.configure(image=None, text="이미지가 없습니다.")
        self._ctk_image_ref = None

        self.progress_bar.set(0)
        self.status_label.configure(text="대기 중")

    def _on_generate_clicked(self) -> None:
        if self._is_running:
            return

        topic = self.topic_entry.get().strip()
        if not topic:
            self.status_label.configure(text="주제를 입력하세요.")
            return

        self._job_id += 1
        job_id = self._job_id

        self._set_busy(True)
        self._reset_results()
        self.status_label.configure(text="생성 중...")

        def on_progress(percent: int, message: str) -> None:
            self.root.after(0, lambda: self._handle_progress(job_id, percent, message))

        def on_complete(text: str, image: Image.Image) -> None:
            self.root.after(0, lambda: self._handle_complete(job_id, text, image))

        def on_error(message: str) -> None:
            self.root.after(0, lambda: self._handle_error(job_id, message))

        threading.Thread(
            target=self._generator.generate,
            args=(topic, on_progress, on_complete, on_error),
            daemon=True,
        ).start()

    def _handle_progress(self, job_id: int, percent: int, message: str) -> None:
        if job_id != self._job_id:
            return

        safe_percent = max(0, min(100, int(percent)))
        self.progress_bar.set(safe_percent / 100)
        self.status_label.configure(text=f"{message} ({safe_percent}%)")

    def _handle_complete(self, job_id: int, text: str, image: Image.Image) -> None:
        if job_id != self._job_id:
            return

        self._show_result(text, image)
        self.progress_bar.set(1)
        self.status_label.configure(text="완료")
        self._set_busy(False)

    def _handle_error(self, job_id: int, message: str) -> None:
        if job_id != self._job_id:
            return

        self.status_label.configure(text=f"오류: {message}")
        self.text_result.configure(state="normal")
        self.text_result.delete("1.0", "end")
        self.text_result.insert("end", f"오류가 발생했습니다.\n\n{message}")
        self.text_result.configure(state="disabled")
        self.image_result.configure(image=None, text="이미지가 없습니다.")

        self._set_busy(False)

    def _show_result(self, text: str, image: Image.Image) -> None:
        self.text_result.configure(state="normal")
        self.text_result.delete("1.0", "end")
        self.text_result.insert("end", text)
        self.text_result.configure(state="disabled")

        ctk_image = ctk.CTkImage(
            light_image=image,
            dark_image=image,
            size=(IMAGE_WIDTH, IMAGE_HEIGHT),
        )
        # Tk 위젯이 이미지 레퍼런스를 유지해야 깜빡임/소실이 줄어듭니다.
        self._ctk_image_ref = ctk_image
        self.image_result.configure(image=ctk_image, text="")

