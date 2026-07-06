from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ui_case_compiler.recorder.recorder_session import RecordedEvent


class EventNormalizer:
    """Remove noisy events and merge consecutive input updates."""

    noise_types = {"mousemove"}
    blocked_hosts = {"wappass.baidu.com"}
    blocked_url_markers = (
        "/captcha/",
        "captcha",
        "verify",
        "security",
        "rsv_jmp=fail",
    )

    def normalize(self, events: list[RecordedEvent]) -> list[RecordedEvent]:
        normalized: list[RecordedEvent] = []
        pending_input: RecordedEvent | None = None
        inside_blocked_flow = False

        for event in events:
            if event.type in self.noise_types:
                continue

            if event.type == "navigation":
                if self._is_blocked_url(event.url):
                    if pending_input is not None:
                        normalized.append(pending_input)
                        pending_input = None
                    inside_blocked_flow = True
                    continue

                if inside_blocked_flow:
                    inside_blocked_flow = False
                    continue

            if inside_blocked_flow:
                continue

            if self._is_text_entry_update(event):
                if pending_input is not None and self._same_element(pending_input, event):
                    pending_input = event
                else:
                    if pending_input is not None:
                        normalized.append(pending_input)
                    pending_input = event
                continue

            if pending_input is not None:
                normalized.append(pending_input)
                pending_input = None
            normalized.append(event)

        if pending_input is not None:
            normalized.append(pending_input)

        return normalized

    @staticmethod
    def _is_text_entry_update(event: RecordedEvent) -> bool:
        if event.type not in {"input", "change"} or event.element is None:
            return False

        tag = event.element.tag.lower()
        role = (event.element.role or "").lower()
        if role in {"checkbox", "radio", "switch", "button"}:
            return False
        return tag in {"input", "textarea"} or role == "textbox"

    @classmethod
    def _is_blocked_url(cls, url: str | None) -> bool:
        if not url:
            return False
        normalized_url = url.lower()
        if any(host in normalized_url for host in cls.blocked_hosts):
            return True
        return any(marker in normalized_url for marker in cls.blocked_url_markers)

    @staticmethod
    def _same_element(left: RecordedEvent, right: RecordedEvent) -> bool:
        left_element = left.element
        right_element = right.element
        if left_element is None or right_element is None:
            return False

        for attr in ("test_id", "css"):
            left_value = getattr(left_element, attr)
            right_value = getattr(right_element, attr)
            if left_value and left_value == right_value:
                return True

        if (
            left_element.role
            and left_element.role == right_element.role
            and left_element.label
            and left_element.label == right_element.label
        ):
            return True

        if (
            left_element.role
            and left_element.role == right_element.role
            and left_element.placeholder
            and left_element.placeholder == right_element.placeholder
        ):
            return True

        return left_element == right_element
