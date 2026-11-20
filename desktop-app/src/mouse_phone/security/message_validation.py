"""Validación estricta de mensajes antes de que alcancen acciones de Windows."""
import math

MAX_MESSAGE_BYTES = 16_384
MAX_DELTA = 500.0
MAX_SCROLL = 5_000
MAX_COUNTER = 9_007_199_254_740_991
MEDIA_ACTIONS = frozenset({"play_pause", "next", "previous", "volume_up", "volume_down", "seek_back", "seek_forward"})


class MessageValidationError(ValueError):
    pass


def _number(value, field: str, limit: float) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or abs(value) > limit:
        raise MessageValidationError(f"invalid {field}")


def _only(message: dict, allowed: set[str]) -> None:
    if set(message) - allowed:
        raise MessageValidationError("unexpected field")


def validate_message(message: object) -> dict:
    if not isinstance(message, dict) or not isinstance(message.get("type"), str):
        raise MessageValidationError("message must be an object with a type")
    message_type = message["type"]
    if message_type == "move":
        _only(message, {"type", "dx", "dy"})
        if "dx" not in message or "dy" not in message: raise MessageValidationError("move requires dx and dy")
        _number(message["dx"], "dx", MAX_DELTA); _number(message["dy"], "dy", MAX_DELTA)
    elif message_type == "move_end": _only(message, {"type"})
    elif message_type == "click":
        _only(message, {"type", "button"})
        if message.get("button", "left") != "left": raise MessageValidationError("unsupported button")
    elif message_type == "scroll":
        _only(message, {"type", "amount"})
        amount = message.get("amount")
        if isinstance(amount, bool) or not isinstance(amount, int) or abs(amount) > MAX_SCROLL: raise MessageValidationError("invalid scroll amount")
    elif message_type == "media":
        _only(message, {"type", "action"})
        if message.get("action") not in MEDIA_ACTIONS: raise MessageValidationError("unsupported media action")
    elif message_type == "session_init":
        _only(message, {"type", "mode", "public"})
        if message.get("mode") not in {"qr", "code"} or not isinstance(message.get("public"), str) or not 40 <= len(message["public"]) <= 128: raise MessageValidationError("invalid session init")
    elif message_type == "secure":
        _only(message, {"type", "counter", "nonce", "data"})
        counter = message.get("counter")
        if isinstance(counter, bool) or not isinstance(counter, int) or not 0 < counter <= MAX_COUNTER: raise MessageValidationError("invalid counter")
        if not isinstance(message.get("nonce"), str) or not 12 <= len(message["nonce"]) <= 64: raise MessageValidationError("invalid nonce")
        if not isinstance(message.get("data"), str) or not 1 <= len(message["data"]) <= MAX_MESSAGE_BYTES: raise MessageValidationError("invalid encrypted data")
    elif message_type == "confirm":
        _only(message, {"type", "mode", "code"})
        if message.get("mode") not in {"qr", "code"}: raise MessageValidationError("invalid confirmation")
        if message["mode"] == "code" and (not isinstance(message.get("code"), str) or len(message["code"]) != 6 or not message["code"].isdigit()): raise MessageValidationError("invalid code")
    else:
        raise MessageValidationError("unsupported message type")
    return message
