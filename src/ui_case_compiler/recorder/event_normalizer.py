from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ui_case_compiler.recorder.recorder_session import RecordedEvent


class EventNormalizer:
    """Remove noisy events and merge consecutive input updates."""

    noise_types = {"mousemove"}

    def normalize(self, events: list[RecordedEvent]) -> list[RecordedEvent]:
        normalized: list[RecordedEvent] = []
        pending_input: RecordedEvent | None = None

        for event in events:
            if event.type in self.noise_types:
                continue

            if event.type == "input":
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
    def _same_element(left: RecordedEvent, right: RecordedEvent) -> bool:
        return left.element == right.element
