(() => {
  if (window.__uicaseRecorderInstalled) return;
  window.__uicaseRecorderInstalled = true;

  const IMPLICIT_ROLES = {
    a: (el) => (el.hasAttribute("href") ? "link" : null),
    button: () => "button",
    select: () => "combobox",
    textarea: () => "textbox",
  };

  function inputRole(el) {
    const type = (el.getAttribute("type") || "text").toLowerCase();
    if (type === "checkbox") return "checkbox";
    if (type === "radio") return "radio";
    if (type === "button" || type === "submit" || type === "reset") return "button";
    return "textbox";
  }

  function roleOf(el) {
    const explicit = el.getAttribute("role");
    if (explicit) return explicit;
    const tag = el.tagName.toLowerCase();
    if (tag === "input") return inputRole(el);
    const fn = IMPLICIT_ROLES[tag];
    return fn ? fn(el) : null;
  }

  function trimText(value) {
    if (!value) return null;
    const line = value.trim().split("\n")[0].trim();
    if (!line) return null;
    return line.length > 200 ? line.slice(0, 200) : line;
  }

  function labelOf(el) {
    const aria = el.getAttribute("aria-label");
    if (aria && aria.trim()) return aria.trim();
    const labelledby = el.getAttribute("aria-labelledby");
    if (labelledby) {
      const ref = document.getElementById(labelledby);
      const text = trimText(ref && ref.textContent);
      if (text) return text;
    }
    if (el.id) {
      const forLabel = document.querySelector(`label[for="${el.id}"]`);
      const text = trimText(forLabel && forLabel.textContent);
      if (text) return text;
    }
    const ancestor = el.closest("label");
    if (ancestor) {
      const clone = ancestor.cloneNode(true);
      clone.querySelectorAll("input, textarea, select").forEach((n) => n.remove());
      const text = trimText(clone.textContent);
      if (text) return text;
    }
    return null;
  }

  function cssOf(el) {
    if (el.id) return `#${el.id}`;
    const parts = [];
    let node = el;
    while (node && node.nodeType === 1 && node.tagName.toLowerCase() !== "html") {
      let selector = node.tagName.toLowerCase();
      const parent = node.parentElement;
      if (parent) {
        const siblings = Array.from(parent.children).filter(
          (c) => c.tagName === node.tagName
        );
        if (siblings.length > 1) {
          selector += `:nth-of-type(${siblings.indexOf(node) + 1})`;
        }
      }
      parts.unshift(selector);
      if (node.id) {
        parts[0] = `#${node.id}`;
        break;
      }
      node = node.parentElement;
    }
    return parts.join(" > ");
  }

  function xpathOf(el) {
    const parts = [];
    let node = el;
    while (node && node.nodeType === 1) {
      let index = 1;
      let sibling = node.previousElementSibling;
      while (sibling) {
        if (sibling.tagName === node.tagName) index += 1;
        sibling = sibling.previousElementSibling;
      }
      parts.unshift(`${node.tagName.toLowerCase()}[${index}]`);
      node = node.parentElement;
    }
    return "/" + parts.join("/");
  }

  function attr(el, name) {
    const value = el.getAttribute(name);
    return value && value.trim() ? value.trim() : null;
  }

  function describe(el) {
    return {
      tag: el.tagName.toLowerCase(),
      text: trimText(el.textContent),
      role: roleOf(el),
      label: labelOf(el),
      placeholder: attr(el, "placeholder"),
      test_id: attr(el, "data-testid"),
      css: cssOf(el),
      xpath: xpathOf(el),
    };
  }

  function send(type, el, extra) {
    if (!el || el.nodeType !== 1) return;
    const payload = { type, timestamp: Date.now(), element: describe(el) };
    if (extra && "value" in extra) payload.value = extra.value;
    if (window.__uicaseRecord) window.__uicaseRecord(payload);
  }

  document.addEventListener(
    "click",
    (event) => {
      if (event.button !== 0) return;
      send("click", event.target, null);
    },
    true
  );
  document.addEventListener(
    "input",
    (event) => send("input", event.target, { value: event.target.value }),
    true
  );
  document.addEventListener(
    "change",
    (event) => send("change", event.target, { value: event.target.value }),
    true
  );
})();
