import time
from typing import Callable

from PIL import Image, ImageDraw, ImageFont

from .constants import (
    DUMMY_TEXT_TEMPLATE,
    IMAGE_BG_COLOR,
    IMAGE_HEIGHT,
    IMAGE_TEXT_COLOR,
    IMAGE_WIDTH,
    PROGRESS_STEPS,
)


ProgressCallback = Callable[[int, str], None]
CompleteCallback = Callable[[str, Image.Image], None]
ErrorCallback = Callable[[str], None]


class DummyGeneratorService:
    """
    실제 API 연동 전, UI 동작 검증을 위한 더미 생성기입니다.
    """

    def generate(
        self,
        topic: str,
        on_progress: ProgressCallback,
        on_complete: CompleteCallback,
        on_error: ErrorCallback,
    ) -> None:
        try:
            topic = (topic or "").strip()
            if not topic:
                raise ValueError("주제는 비어 있을 수 없습니다.")

            for percent, message in PROGRESS_STEPS:
                on_progress(percent, message)
                # UI에서 진행 상태가 보이도록 단계별로 딜레이를 둡니다.
                time.sleep(0.7)

            text = DUMMY_TEXT_TEMPLATE.format(topic=topic)
            image = self._make_dummy_image(topic)
            on_complete(text, image)
        except Exception as e:
            on_error(str(e))

    def _make_dummy_image(self, topic: str) -> Image.Image:
        image = Image.new("RGB", (IMAGE_WIDTH, IMAGE_HEIGHT), IMAGE_BG_COLOR)
        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default()

        # 제목처럼 보이도록 상단에 고정 문구를 넣습니다.
        header = "Dummy Image"
        header_bbox = draw.textbbox((0, 0), header, font=font)
        header_w = header_bbox[2] - header_bbox[0]
        draw.text(
            ((IMAGE_WIDTH - header_w) // 2, 12),
            header,
            fill=IMAGE_TEXT_COLOR,
            font=font,
        )

        # 토픽을 너비에 맞춰 줄바꿈합니다.
        max_text_width = IMAGE_WIDTH - 24
        lines = []
        current = ""
        # 공백 기반으로 우선 줄을 만들되, 한 단어가 너무 길면 글자 단위로 쪼갭니다.
        words = topic.split() or [topic]
        for word in words:
            candidate = word if not current else f"{current} {word}"
            candidate_bbox = draw.textbbox((0, 0), candidate, font=font)
            candidate_w = candidate_bbox[2] - candidate_bbox[0]

            if candidate_w <= max_text_width:
                current = candidate
                continue

            if current:
                lines.append(current)
                current = ""

            # 단어 자체가 너무 길면 글자 단위로 분할
            if draw.textbbox((0, 0), word, font=font)[2] - draw.textbbox((0, 0), word, font=font)[0] > max_text_width:
                buf = ""
                for ch in word:
                    test = buf + ch
                    if draw.textbbox((0, 0), test, font=font)[2] - draw.textbbox((0, 0), test, font=font)[0] <= max_text_width:
                        buf = test
                    else:
                        if buf:
                            lines.append(buf)
                        buf = ch
                if buf:
                    current = buf
            else:
                current = word

        if current:
            lines.append(current)
        if not lines:
            lines = [topic]

        # 가운데 정렬로 배치
        line_height = font.size + 4
        total_height = len(lines) * line_height
        y = (IMAGE_HEIGHT - total_height) // 2 + 10

        for line in lines[:4]:  # 너무 길면 앞부분만 보여줍니다.
            bbox = draw.textbbox((0, 0), line, font=font)
            w = bbox[2] - bbox[0]
            draw.text(
                ((IMAGE_WIDTH - w) // 2, y),
                line,
                fill=IMAGE_TEXT_COLOR,
                font=font,
            )
            y += line_height

        return image

