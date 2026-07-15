# ruff: noqa: E501
from __future__ import annotations

import json
from typing import Any, cast

from playwright.async_api import async_playwright
from pydantic import BaseModel, ConfigDict, Field


class LocatorCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strategy: str
    value: str | None = None
    role: str | None = None
    name: str | None = None


class SelectOptionSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str
    value: str


class InteractiveElementSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    element_id: str
    tag: str
    role: str | None = None
    text: str | None = None
    label: str | None = None
    placeholder: str | None = None
    test_id: str | None = None
    name: str | None = None
    type: str | None = None
    css: str | None = None
    visible: bool = True
    enabled: bool = True
    options: list[SelectOptionSummary] = Field(default_factory=list)
    locator_candidates: list[LocatorCandidate] = Field(default_factory=list)


class FormSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    form_id: str | None = None
    fields: list[str] = Field(default_factory=list)
    submit_buttons: list[str] = Field(default_factory=list)


class AssertionCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str
    css: str | None = None


class PageSemanticContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str
    title: str
    visible_texts: list[str] = Field(default_factory=list)
    interactive_elements: list[InteractiveElementSummary] = Field(default_factory=list)
    forms: list[FormSummary] = Field(default_factory=list)
    assertion_candidates: list[AssertionCandidate] = Field(default_factory=list)

    def to_prompt_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), ensure_ascii=False, indent=2)

    def to_baseline_dom_summary(self) -> str:
        texts = " / ".join(self.visible_texts[:20])
        tags = " ".join(
            f"{element.tag}#{element.css.removeprefix('#')}"
            for element in self.interactive_elements[:20]
            if element.css and element.css.startswith("#")
        )
        return f"可见文案: {texts}\n简单 DOM: {tags}"


class SemanticContextCollector:
    """Collect a compact semantic map of a page for context-aware compilation."""

    def __init__(self, timeout_ms: int = 10_000) -> None:
        self._timeout_ms = timeout_ms

    async def collect(self, url: str) -> PageSemanticContext:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=self._timeout_ms)
                await page.wait_for_load_state("networkidle", timeout=self._timeout_ms)
                raw = await page.evaluate(_COLLECT_SCRIPT)
                return PageSemanticContext.model_validate(cast(dict[str, Any], raw))
            finally:
                await browser.close()


_COLLECT_SCRIPT = """() => {
  const clean = (value) => (value || "").replace(/\\s+/g, " ").trim();
  const isVisible = (element) => {
    const style = window.getComputedStyle(element);
    const rect = element.getBoundingClientRect();
    return style.visibility !== "hidden" &&
      style.display !== "none" &&
      rect.width > 0 &&
      rect.height > 0;
  };
  const cssEscape = (value) => {
    if (window.CSS && window.CSS.escape) return window.CSS.escape(value);
    return String(value).replace(/[^a-zA-Z0-9_-]/g, "\\\\$&");
  };
  const cssPath = (element) => {
    if (element.id) return `#${cssEscape(element.id)}`;
    const testId = element.getAttribute("data-testid");
    if (testId) return `[data-testid="${testId.replace(/"/g, "\\\\\\"")}"]`;
    const name = element.getAttribute("name");
    if (name) return `${element.tagName.toLowerCase()}[name="${name.replace(/"/g, "\\\\\\"")}"]`;
    const parent = element.parentElement;
    if (!parent) return element.tagName.toLowerCase();
    const sameTag = Array.from(parent.children).filter((item) => item.tagName === element.tagName);
    const index = sameTag.indexOf(element) + 1;
    return `${element.tagName.toLowerCase()}:nth-of-type(${index})`;
  };
  const labelText = (element) => {
    const aria = clean(element.getAttribute("aria-label"));
    if (aria) return aria;
    const labelledBy = element.getAttribute("aria-labelledby");
    if (labelledBy) {
      const text = labelledBy.split(/\\s+/).map((id) => clean(document.getElementById(id)?.innerText)).filter(Boolean).join(" ");
      if (text) return text;
    }
    if (element.labels && element.labels.length) {
      const text = Array.from(element.labels).map((item) => clean(item.innerText)).filter(Boolean).join(" ");
      if (text) return text;
    }
    const parentLabel = element.closest("label");
    if (parentLabel) {
      const text = clean(parentLabel.innerText);
      if (text) return text;
    }
    return "";
  };
  const roleFor = (element) => {
    const explicit = clean(element.getAttribute("role"));
    if (explicit) return explicit;
    const tag = element.tagName.toLowerCase();
    const type = clean(element.getAttribute("type")).toLowerCase();
    if (tag === "button") return "button";
    if (tag === "a") return "link";
    if (tag === "select") return "combobox";
    if (tag === "textarea") return "textbox";
    if (tag === "input" && ["checkbox", "radio"].includes(type)) return type;
    if (tag === "input") return "textbox";
    return "";
  };
  const textFor = (element) => clean(element.innerText || element.value || element.getAttribute("value"));
  const addCandidate = (items, candidate) => {
    const key = JSON.stringify(candidate);
    if (!items.some((item) => JSON.stringify(item) === key)) items.push(candidate);
  };
  const candidatesFor = (element, role, label, text, css) => {
    const items = [];
    const testId = clean(element.getAttribute("data-testid"));
    const placeholder = clean(element.getAttribute("placeholder"));
    if (testId) addCandidate(items, {strategy: "test_id", value: testId});
    if (label) addCandidate(items, {strategy: "label", value: label});
    if (placeholder) addCandidate(items, {strategy: "placeholder", value: placeholder});
    if (role && (label || text)) addCandidate(items, {strategy: "role", role, name: label || text});
    if (text && ["button", "link"].includes(role)) addCandidate(items, {strategy: "text", value: text});
    if (css) addCandidate(items, {strategy: "css", value: css});
    return items.slice(0, 6);
  };

  const selector = "input, textarea, select, button, a, [role='button'], [contenteditable='true']";
  const elements = Array.from(document.querySelectorAll(selector))
    .filter(isVisible)
    .slice(0, 80)
    .map((element, index) => {
      const tag = element.tagName.toLowerCase();
      const role = roleFor(element);
      const label = labelText(element);
      const text = textFor(element);
      const css = cssPath(element);
      const options = tag === "select"
        ? Array.from(element.options).map((option) => ({label: clean(option.textContent), value: option.value}))
        : [];
      return {
        element_id: `e${index + 1}`,
        tag,
        role: role || null,
        text: text || null,
        label: label || null,
        placeholder: clean(element.getAttribute("placeholder")) || null,
        test_id: clean(element.getAttribute("data-testid")) || null,
        name: clean(element.getAttribute("name")) || null,
        type: clean(element.getAttribute("type")) || null,
        css,
        visible: true,
        enabled: !element.disabled,
        options,
        locator_candidates: candidatesFor(element, role, label, text, css)
      };
    });

  const forms = Array.from(document.querySelectorAll("form")).map((form) => {
    const fields = Array.from(form.querySelectorAll("input, textarea, select"))
      .map((element) => labelText(element) || clean(element.getAttribute("placeholder")) || clean(element.getAttribute("name")))
      .filter(Boolean);
    const submit_buttons = Array.from(form.querySelectorAll("button, input[type='submit']"))
      .map((element) => textFor(element))
      .filter(Boolean);
    return {form_id: form.id || form.getAttribute("data-testid") || null, fields, submit_buttons};
  });

  const visibleTexts = Array.from(document.body.querySelectorAll("h1,h2,h3,p,label,button,a,option,th,td,[role='status']"))
    .filter(isVisible)
    .map((element) => clean(element.innerText || element.textContent))
    .filter((text) => text && text.length <= 80);
  const uniqueVisibleTexts = Array.from(new Set(visibleTexts)).slice(0, 80);
  const assertionCandidates = Array.from(document.querySelectorAll("[role='status'], .msg, .toast, section, p"))
    .filter(isVisible)
    .map((element) => ({text: clean(element.innerText || element.textContent), css: cssPath(element)}))
    .filter((item) => item.text)
    .slice(0, 30);

  return {
    url: window.location.href,
    title: document.title,
    visible_texts: uniqueVisibleTexts,
    interactive_elements: elements,
    forms,
    assertion_candidates: assertionCandidates
  };
}"""
