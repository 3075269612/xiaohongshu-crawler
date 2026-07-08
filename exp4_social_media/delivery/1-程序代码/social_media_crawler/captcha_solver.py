from __future__ import annotations


class CaptchaRequired(RuntimeError):
    pass


def handle_captcha(context: str) -> None:
    """Pause for manual verification instead of bypassing real platform security."""
    raise CaptchaRequired(
        f"检测到验证码或异常访问：{context}。请人工确认后再继续，或降低访问频率。"
    )