# OrderFood/NotiHelper.py
from markupsafe import Markup
from flask import flash, url_for

TOAST_CSS = """
<style>
#toast-stack{position:fixed;right:16px;top:16px;z-index:2147483647;display:flex;flex-direction:column;gap:10px}
.toast{min-width:280px;max-width:420px;padding:12px 14px;border-radius:10px;box-shadow:0 8px 24px rgba(0,0,0,.15);color:#0f172a;background:#fff;display:flex;gap:10px;align-items:flex-start;border:1px solid rgba(0,0,0,.08);opacity:0;transform:translateY(-6px);transition:opacity .18s ease,transform .18s ease}
.toast.show{opacity:1;transform:translateY(0)}
.toast .t-title{font-weight:700;margin-bottom:2px}
.toast .t-msg{font-size:14px;opacity:.9}
.toast.success{border-left:6px solid #16a34a}
.toast.error{border-left:6px solid #ef4444}
.toast.warning{border-left:6px solid #f59e0b}
.toast .t-close{margin-left:auto;border:none;background:transparent;font-size:18px;line-height:1;cursor:pointer;opacity:.6}
.toast .t-close:hover{opacity:1}
</style>
"""

def noti_assets(flashed_messages=None):
    """
    Render CSS + container + flash messages + include toast.js
    """
    import json
    flashes_js = ""
    if flashed_messages:
        flashes_js = f"<script>window.__flashes = {json.dumps(flashed_messages, ensure_ascii=False)};</script>"

    # include toast.js
    toast_js_url = url_for("static", filename="js/toast.js")
    js_include = f'<script src="{toast_js_url}"></script>'

    return Markup(
        TOAST_CSS +
        '<div id="toast-stack"></div>' +
        flashes_js +
        js_include
    )

def flash_success(msg): flash(msg, "success")
def flash_error(msg):   flash(msg, "error")
def flash_warning(msg): flash(msg, "warning")

def init_app(app):
    """Inject noti_assets vào Jinja"""
    from flask import get_flashed_messages
    @app.context_processor
    def _inject_noti():
        flashes = get_flashed_messages(with_categories=True)
        return {"noti_assets": lambda: noti_assets(flashed_messages=flashes)}
