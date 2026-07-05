from ui_case_compiler.config import RuntimeConfig, load_config
from ui_case_compiler.errors import PlanValidationError, UiCaseCompilerError


def test_default_config_loads() -> None:
    config = load_config()

    assert isinstance(config, RuntimeConfig)
    assert config.browser == "chromium"
    assert config.timeout_ms > 0


def test_custom_errors_share_base_type() -> None:
    assert issubclass(PlanValidationError, UiCaseCompilerError)


def test_llm_config_defaults(monkeypatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)

    config = load_config()

    assert config.llm.api_key is None
    assert config.llm.base_url == "https://api.deepseek.com"
    assert config.llm.model == "deepseek-chat"
    assert config.llm.timeout_s == 60


def test_llm_config_reads_environment(monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    monkeypatch.setenv("LLM_BASE_URL", "https://custom.example")
    monkeypatch.setenv("LLM_MODEL", "deepseek-reasoner")

    config = load_config()

    assert config.llm.api_key == "sk-test"
    assert config.llm.base_url == "https://custom.example"
    assert config.llm.model == "deepseek-reasoner"
