import shutil
import unicodedata

from prompt_toolkit import Application
from prompt_toolkit.widgets import TextArea, Frame, Label
from prompt_toolkit.layout.containers import HSplit, VSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout import Layout
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
from prompt_toolkit.document import Document

# ══════════════════════════════════════════════
# 유틸
# ══════════════════════════════════════════════
def display_width(s: str) -> int:
    return sum(2 if unicodedata.east_asian_width(c) in ('W', 'F', 'A') else 1 for c in s)

def ljust_wide(s: str, width: int) -> str:
    return s + ' ' * max(0, width - display_width(s))

def wrap_wide(text: str, max_width: int) -> list[str]:
    lines, current, cur_w = [], [], 0
    for ch in text:
        cw = display_width(ch)
        if cur_w + cw > max_width:
            lines.append(''.join(current))
            current, cur_w = [], 0   # ← 버그 수정: cur_w 리셋
        current.append(ch)
        cur_w += cw
    if current:
        lines.append(''.join(current))
    return lines or ['']

def make_bubble(sender: str, text: str, is_me: bool) -> str:
    total_width = shutil.get_terminal_size().columns - 5
    bubble_max  = total_width // 2
    wrapped     = wrap_wide(text, bubble_max - 4)
    inner_w     = max(display_width(l) for l in wrapped)
    top         = f"┌{'─' * (inner_w + 2)}┐"
    bottom      = f"└{'─' * (inner_w + 2)}┘"
    middles     = [f"│ {ljust_wide(l, inner_w)} │" for l in wrapped]
    box_w       = inner_w + 4
    pad         = ' ' * (total_width - box_w)
    sender_pad  = ' ' * (total_width - display_width(sender))
    if is_me:
        return "\n".join([f"{sender_pad}{sender}", f"{pad}{top}",
                          *[f"{pad}{m}" for m in middles], f"{pad}{bottom}"])
    else:
        return "\n".join([f" {sender}", f" {top}",
                          *[f" {m}" for m in middles], f" {bottom}"])

def make_system_msg(text: str) -> str:
    """채팅창 가운데 정렬 시스템 메시지"""
    total_w = shutil.get_terminal_size().columns - 5
    msg = f"─── {text} ───"
    pad = ' ' * max(0, (total_w - display_width(msg)) // 2)
    return f"{pad}{msg}"


# ══════════════════════════════════════════════
# 공통 스타일
# ══════════════════════════════════════════════
APP_STYLE = Style.from_dict({
    # 공통 레이아웃
    "header-frame frame.border":   "bold #00bcd4",
    "header-label":                "bold #00bcd4",
    "body-frame frame.border":     "#00bcd4",
    "body-frame frame.label":      "bold #00bcd4",
    "footer-frame frame.border":   "#444466",
    "textarea prompt":             "bold #ffcc00",
    "chat":                        "#cccccc",
    # 로그인
    "login-frame frame.border":    "bold #00bcd4",
    "login-logo":                  "bold #00e5ff",
    "login-step":                  "#aaaaaa",
    # 방 목록
    "room-hint":                   "#555577",
    # 에러
    "error":                       "#ff5555",
})


# ══════════════════════════════════════════════
# Mock 데이터 (서버 연동 시 교체)
# ══════════════════════════════════════════════
FRIENDS: list[str] = ["Alice", "Bob", "Charlie", "Dave"]
rooms:   list[dict] = []
_room_id = [1]

def new_room(name: str, members: list[str]) -> dict:
    r = {"id": _room_id[0], "name": name, "members": members, "online": members[:1]}
    _room_id[0] += 1
    return r


# ══════════════════════════════════════════════
# SCREEN 1 : 로그인
# ══════════════════════════════════════════════
LOGO = """\
  ██████╗██╗     ██╗     
 ██╔════╝██║     ██║     
 ██║     ██║     ██║     
 ██║     ██║     ██║     
 ╚██████╗███████╗██║     
  ╚═════╝╚══════╝╚═╝     
      C·H·A·T            """

def run_login() -> str | None:
    """로그인 화면. 성공 시 username 반환, 취소 시 None."""
    state  = {"step": "username", "username": ""}
    result = {"value": None}

    # 단계별 텍스트
    step_texts = {"username": "① 아이디 입력", "password": "② 비밀번호 입력"}

    step_label  = Label(step_texts["username"], style="class:login-step")
    error_text  = [""]
    error_win   = Window(
        content=FormattedTextControl(lambda: [("class:error", error_text[0])]),
        height=1,
    )
    input_field = TextArea(
        multiline=False, prompt="> ",
        style="class:input", focusable=True,
    )

    kb = KeyBindings()

    @kb.add("enter")
    def on_enter(event):
        val = input_field.text.strip()
        error_text[0] = ""
        if not val:
            error_text[0] = "  값을 입력해주세요."
            return

        if state["step"] == "username":
            state["username"] = val
            state["step"]     = "password"
            step_label.text   = step_texts["password"]
            input_field.text  = ""

        elif state["step"] == "password":
            # TODO: 서버 인증으로 교체
            if state["username"]:
                result["value"] = state["username"]
                event.app.exit()
            else:
                error_text[0] = "  인증 실패. 다시 시도하세요."

    @kb.add("c-c")
    @kb.add("escape")
    def on_quit(event):
        event.app.exit()

    form = HSplit([
        Label(LOGO, style="class:login-logo"),
        Label("  " + "─" * 26, style="class:room-hint"),
        Label(""),
        step_label,
        Label(""),
        input_field,
        Label(""),
        error_win,
        Label("  ESC: 종료", style="class:room-hint"),
    ])

    # 화면 중앙 배치
    centered = HSplit([
        Window(),
        VSplit([Window(), Frame(form, width=36, style="class:login-frame"), Window()]),
        Window(),
    ])

    layout = Layout(centered, focused_element=input_field)
    Application(layout=layout, key_bindings=kb, style=APP_STYLE, full_screen=True).run()
    return result["value"]


# ══════════════════════════════════════════════
# SCREEN 2 : 방 목록
# ══════════════════════════════════════════════
def run_rooms(username: str) -> tuple[str, dict | None]:
    """
    반환값:
      ("chat",   room)  → 방 입장
      ("create", None)  → 방 생성
      ("quit",   None)  → 종료
    """
    result = {"action": "quit", "room": None}

    def build_list() -> str:
        if not rooms:
            return (
                "\n\n"
                "  아직 참여 중인 방이 없습니다.\n\n"
                "  [ + ] 를 입력하여 새 방을 만드세요.\n"
            )
        lines = ["\n  참여 중인 채팅방\n  " + "─" * 32]
        for r in rooms:
            preview   = ", ".join(r["members"][:3])
            if len(r["members"]) > 3:
                preview += f" 외 {len(r['members'])-3}명"
            online_n  = len(r.get("online", []))
            lines += [
                f"\n  [{r['id']}]  {r['name']}",
                f"       멤버: {preview}",
                f"       온라인: {online_n}명",
            ]
        lines += ["\n  " + "─" * 32,
                  "  숫자: 방 입장    +: 새 방 만들기"]
        return "\n".join(lines)

    display = TextArea(
        text=build_list(), read_only=True,
        focusable=False, wrap_lines=False, style="class:chat",
    )
    input_box   = TextArea(multiline=False, prompt=f"{username} > ",
                           style="class:input", focusable=True)
    error_text  = [""]
    error_win   = Window(
        content=FormattedTextControl(lambda: [("class:error", error_text[0])]),
        height=1,
    )

    kb = KeyBindings()

    @kb.add("enter")
    def on_enter(event):
        val = input_box.text.strip()
        input_box.text  = ""
        error_text[0]   = ""

        if val == "+":
            result["action"] = "create"
            event.app.exit()
            return

        if val.isdigit():
            rid = int(val)
            match = next((r for r in rooms if r["id"] == rid), None)
            if match:
                result.update(action="chat", room=match)
                event.app.exit()
                return
            error_text[0] = "  없는 방 번호입니다."
            return

        error_text[0] = "  숫자 또는 + 를 입력하세요."

    @kb.add("c-c")
    @kb.add("escape")
    def on_quit(event):
        event.app.exit()

    root = HSplit([
        Frame(Label(f"  💬  CLI CHAT  ·  {username}", style="class:header-label"),
              style="class:header-frame", height=3),
        Frame(display, title="채팅방 목록", style="class:body-frame"),
        error_win,
        Frame(input_box, style="class:footer-frame", height=3),
    ])

    layout = Layout(root, focused_element=input_box)
    Application(layout=layout, key_bindings=kb, style=APP_STYLE, full_screen=True).run()
    return result["action"], result["room"]


# ══════════════════════════════════════════════
# SCREEN 3 : 방 생성
# ══════════════════════════════════════════════
def run_create_room(username: str) -> dict | None:
    """방 생성 화면. 생성된 room dict 반환, 취소 시 None."""
    state  = {"step": "name", "room_name": "", "selected": set()}
    result = {"room": None}

    def build_friend_view() -> str:
        lines = [
            f"\n  방 이름 : {state['room_name']}\n",
            "  초대할 친구를 선택하세요\n",
            "  " + "─" * 30,
        ]
        for i, f in enumerate(FRIENDS, 1):
            mark = "●" if i in state["selected"] else "○"
            lines.append(f"  [{i}]  {mark}  {f}")
        lines.append("  " + "─" * 30)
        chosen = [FRIENDS[i - 1] for i in sorted(state["selected"])]
        lines.append(f"\n  선택: {', '.join(chosen) if chosen else '없음'}")
        lines.append("  숫자: 토글    done: 완료    back: 취소")
        return "\n".join(lines)

    hint_label  = Label("  방 이름을 입력하세요", style="class:login-step")
    display     = TextArea(text="", read_only=True, focusable=False, style="class:chat")
    input_box   = TextArea(multiline=False, prompt="> ",
                           style="class:input", focusable=True)
    error_text  = [""]
    error_win   = Window(
        content=FormattedTextControl(lambda: [("class:error", error_text[0])]),
        height=1,
    )

    def refresh_display():
        t = build_friend_view()
        display.buffer.set_document(Document(t, 0), bypass_readonly=True)

    kb = KeyBindings()

    @kb.add("enter")
    def on_enter(event):
        val = input_box.text.strip()
        input_box.text = ""
        error_text[0]  = ""

        if state["step"] == "name":
            if not val:
                error_text[0] = "  방 이름을 입력해주세요."
                return
            state["room_name"] = val
            state["step"]      = "friends"
            hint_label.text    = "  숫자로 친구를 선택하세요"
            refresh_display()

        elif state["step"] == "friends":
            if val.lower() == "done":
                members = [username] + [FRIENDS[i - 1] for i in sorted(state["selected"])]
                r = new_room(state["room_name"], members)
                rooms.append(r)
                result["room"] = r
                event.app.exit()
                return
            if val.lower() == "back":
                event.app.exit()
                return
            if val.isdigit() and 1 <= int(val) <= len(FRIENDS):
                idx = int(val)
                state["selected"].symmetric_difference_update({idx})
                refresh_display()
                return
            error_text[0] = "  숫자(토글)  done(완료)  back(취소)"

    @kb.add("c-c")
    @kb.add("escape")
    def on_quit(event):
        event.app.exit()

    root = HSplit([
        Frame(Label("  💬  새 채팅방 만들기", style="class:header-label"),
              style="class:header-frame", height=3),
        Frame(HSplit([hint_label, display]), title="방 만들기", style="class:body-frame"),
        error_win,
        Frame(input_box, style="class:footer-frame", height=3),
    ])

    layout = Layout(root, focused_element=input_box)
    Application(layout=layout, key_bindings=kb, style=APP_STYLE, full_screen=True).run()
    return result["room"]


# ══════════════════════════════════════════════
# SCREEN 4 : 채팅
# ══════════════════════════════════════════════
def run_chat(username: str, room: dict) -> str:
    """채팅 화면. 'back' 또는 'quit' 반환."""
    result = {"action": "back"}

    chat_output = TextArea(
        text="", read_only=True, scrollbar=True,
        focusable=False, wrap_lines=False, style="class:chat",
    )
    input_box = TextArea(
        multiline=False, prompt=f"{username} > ",
        style="class:input", focusable=True,
    )

    # ── 채팅창 헬퍼 ──────────────────────────
    def append(line: str) -> None:
        t = chat_output.text + line + "\n"
        chat_output.buffer.set_document(Document(t, len(t)), bypass_readonly=True)

    def chat_me(text: str):
        append(make_bubble(username, text, is_me=True)); append("")

    def chat_other(sender: str, text: str):
        append(make_bubble(sender, text, is_me=False)); append("")

    def system(text: str):
        # TODO: 서버 시스템 메시지 수신 시 이 함수 호출
        append(make_system_msg(text)); append("")

    def show_current():
        total_w  = shutil.get_terminal_size().columns - 5
        members  = room.get("members", [])
        online   = set(room.get("online", []))
        system("현재 접속자")
        for m in members:
            status = "● 온라인" if m in online else "○ 오프라인"
            line   = f"{m}  {status}"
            pad    = ' ' * max(0, (total_w - display_width(line)) // 2)
            append(f"{pad}{line}")
        append(make_system_msg("─" * 12))
        append("")

    # ── 키 바인딩 ────────────────────────────
    kb = KeyBindings()

    @kb.add("enter")
    def on_enter(event):
        text = input_box.text.strip()
        if not text:
            return
        input_box.text = ""

        if text.lower() == "quit":
            result["action"] = "quit"; event.app.exit(); return
        if text.lower() == "back":
            result["action"] = "back"; event.app.exit(); return
        if text.lower() == "current":
            show_current(); return

        chat_me(text)
        # TODO: 서버로 전송 후 상대 응답은 chat_other() / system() 호출
        chat_other("Bot", text)   # 임시 에코

    @kb.add("up")
    def scroll_up(event):
        buf = chat_output.buffer
        text, pos = buf.text, buf.cursor_position
        ls = text.rfind("\n", 0, pos)
        if ls == -1: return
        ps = text.rfind("\n", 0, ls)
        buf.set_document(Document(text, max(0, ps + 1 if ps != -1 else 0)), bypass_readonly=True)

    @kb.add("down")
    def scroll_down(event):
        buf = chat_output.buffer
        text, pos = buf.text, buf.cursor_position
        nxt = text.find("\n", pos)
        buf.set_document(Document(text, len(text) if nxt == -1 else nxt + 1), bypass_readonly=True)

    @kb.add("pageup")
    def page_up(event):
        for _ in range(5): scroll_up(event)

    @kb.add("pagedown")
    def page_down(event):
        for _ in range(5): scroll_down(event)

    @kb.add("c-c")
    @kb.add("escape")
    def on_esc(event):
        result["action"] = "back"; event.app.exit()

    root = HSplit([
        Frame(
            Label(f"  💬  {room['name']}  ·  {username}", style="class:header-label"),
            style="class:header-frame", height=3,
        ),
        Frame(chat_output, title="채 팅", style="class:body-frame"),
        Frame(input_box, style="class:footer-frame", height=3),
    ])

    layout = Layout(root, focused_element=input_box)
    app = Application(layout=layout, key_bindings=kb, style=APP_STYLE, full_screen=True)

    system(f"{username} 님이 입장했습니다")
    system("back: 방 목록  ·  current: 접속자  ·  quit: 종료")

    app.run()
    return result["action"]


# ══════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════
def main():
    # 1. 로그인
    username = run_login()
    if not username:
        return

    # 2. 방 목록 ↔ 방 생성 ↔ 채팅 루프
    while True:
        action, room = run_rooms(username)

        if action == "quit":
            break

        if action == "create":
            created = run_create_room(username)
            if created:
                if run_chat(username, created) == "quit":
                    break
            continue   # 방 목록으로

        if action == "chat" and room:
            if run_chat(username, room) == "quit":
                break
            # "back" → 루프 반복 → 방 목록으로


if __name__ == "__main__":
    main()