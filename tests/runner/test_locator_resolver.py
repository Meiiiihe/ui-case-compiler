import pytest

from ui_case_compiler.errors import StepExecutionError
from ui_case_compiler.runner.locator_resolver import LocatorResolver
from ui_case_compiler.schema.steps import Locator, StepTarget


class FakeLocator:
    def __init__(
        self,
        name: str,
        count: int = 1,
        visible: bool = True,
        enabled: bool = True,
        editable: bool = True,
    ) -> None:
        self.name = name
        self._count = count
        self._visible = visible
        self._enabled = enabled
        self._editable = editable

    async def count(self) -> int:
        return self._count

    def nth(self, index: int) -> "FakeLocator":
        return FakeLocator(
            f"{self.name}[{index}]",
            count=1,
            visible=self._visible,
            enabled=self._enabled,
            editable=self._editable,
        )

    async def is_visible(self) -> bool:
        return self._visible

    async def is_enabled(self) -> bool:
        return self._enabled

    async def is_editable(self) -> bool:
        return self._editable


class FakePage:
    def __init__(
        self,
        counts: dict[str, int] | None = None,
        visible: dict[str, bool] | None = None,
    ) -> None:
        self.calls: list[str] = []
        self.counts = counts or {}
        self.visible = visible or {}

    def _make(self, key: str) -> FakeLocator:
        self.calls.append(key)
        return FakeLocator(
            key,
            self.counts.get(key, 1),
            visible=self.visible.get(key, True),
        )

    def get_by_role(self, role: str, *, name: str | None = None) -> FakeLocator:
        return self._make(f"role:{role}:{name}")

    def get_by_label(self, text: str) -> FakeLocator:
        return self._make(f"label:{text}")

    def get_by_placeholder(self, text: str) -> FakeLocator:
        return self._make(f"placeholder:{text}")

    def get_by_test_id(self, test_id: str) -> FakeLocator:
        return self._make(f"test_id:{test_id}")

    def get_by_text(self, text: str) -> FakeLocator:
        return self._make(f"text:{text}")

    def locator(self, selector: str) -> FakeLocator:
        return self._make(f"locator:{selector}")


def test_role_locator_mapping() -> None:
    page = FakePage()
    locator = LocatorResolver().to_playwright_locator(
        page,
        Locator(strategy="role", role="button", name="登录"),
    )

    assert locator.name == "role:button:登录"


@pytest.mark.asyncio
async def test_fallback_used_when_primary_matches_zero() -> None:
    page = FakePage({"role:button:提交": 0, "text:提交": 1})
    target = StepTarget(
        primary=Locator(strategy="role", role="button", name="提交"),
        fallbacks=[Locator(strategy="text", value="提交")],
    )

    locator = await LocatorResolver().resolve(page, target)

    assert locator.name == "text:提交"
    assert page.calls == ["role:button:提交", "text:提交"]


@pytest.mark.asyncio
async def test_fallback_used_when_primary_is_hidden_for_input() -> None:
    page = FakePage(
        {"locator:#kw": 1, "label:搜索": 1},
        visible={"locator:#kw": False, "label:搜索": True},
    )
    target = StepTarget(
        primary=Locator(strategy="css", value="#kw"),
        fallbacks=[Locator(strategy="label", value="搜索")],
    )

    locator = await LocatorResolver().resolve(page, target)

    assert locator.name == "label:搜索"
    assert page.calls == ["locator:#kw", "label:搜索"]


@pytest.mark.asyncio
async def test_all_candidates_failed() -> None:
    page = FakePage({"role:button:提交": 0, "locator:button.submit": 0})
    target = StepTarget(
        primary=Locator(strategy="role", role="button", name="提交"),
        fallbacks=[Locator(strategy="css", value="button.submit")],
    )

    with pytest.raises(StepExecutionError, match="Unable to resolve locator"):
        await LocatorResolver().resolve(page, target)
