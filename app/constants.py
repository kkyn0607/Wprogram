APP_TITLE = "콘텐츠 생성기"
WINDOW_WIDTH = 900
WINDOW_HEIGHT = 600

PLACEHOLDER_TOPIC = "주제를 입력하세요"

IMAGE_WIDTH = 400
IMAGE_HEIGHT = 300
IMAGE_BG_COLOR = (45, 55, 72)
IMAGE_TEXT_COLOR = (255, 255, 255)

DUMMY_TEXT_TEMPLATE = """[{topic}]에 대한 생성 결과입니다.

이 텍스트는 실제 API 연동 전 테스트용 더미 데이터입니다.
주제를 바탕으로 작성된 샘플 문단이 여기에 표시됩니다.

- 핵심 요약: {topic}은(는) 흥미로운 주제입니다.
- 상세 설명: 추후 API를 연동하면 이 영역에 AI가 생성한 본문이 나타납니다.
- 참고: 현재는 UI 동작 확인을 위한 placeholder 콘텐츠입니다."""

PROGRESS_STEPS = [
    (10, "요청 준비 중..."),
    (30, "텍스트 생성 중..."),
    (70, "이미지 생성 중..."),
    (100, "완료"),
]
