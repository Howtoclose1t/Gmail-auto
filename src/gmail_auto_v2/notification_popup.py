from __future__ import annotations

import json
import re
import sys
from email.utils import parseaddr
from html import escape
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlencode

TARGET_SCREEN_INDEX = 0
MIN_POPUP_WIDTH = 920
MIN_POPUP_HEIGHT = 660
ICON_DIR = Path(__file__).with_name("assets") / "icons"

TEXT = {
    "title": "New Email Analysis Complete",
    "close": "Close",
    "sender": "Sender",
    "date": "Date",
    "category": "Category",
    "company": "Company",
    "position": "Position",
    "unknown": "unknown",
    "unknown_company": "Unknown company",
    "unknown_position": "Unknown position",
    "unknown_company_position": "Unknown company / Unknown position",
    "verification_code": "Verification code",
    "copy_hint": "Click to copy the code",
    "summary": "Summary",
    "no_summary": "No summary",
    "copy_code": "Copy code",
    "archive": "Archive",
    "unarchive": "Unarchive",
    "archived": "Archived",
    "delete": "Delete",
    "restore": "Restore",
    "deleted": "Deleted",
    "star": "Star",
    "unstar": "Unstar",
    "missing_id": "Missing message_id; this email cannot be modified.",
    "failed": "Action failed",
    "done": "Done",
    "working": "Working...",
    "unknown_action": "Unknown action",
}


def main() -> None:
    try:
        payload = json.loads(sys.argv[1])
    except (IndexError, json.JSONDecodeError):
        payload = {}

    show_popup(payload)


def show_popup(payload: dict[str, Any]) -> None:
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QColor, QFont
    from PyQt5.QtWidgets import (
        QApplication,
        QFrame,
        QGraphicsDropShadowEffect,
        QHBoxLayout,
        QLabel,
        QPushButton,
        QSizePolicy,
        QVBoxLayout,
        QWidget,
    )

    app = QApplication(sys.argv)

    width = max(int(payload.get("width") or MIN_POPUP_WIDTH), MIN_POPUP_WIDTH)
    message_id = str(payload.get("message_id") or "").strip()
    verification_code = _displayable_verification_code(
        str(payload.get("verification_code") or "")
    )
    min_height = 760 if verification_code else MIN_POPUP_HEIGHT
    height = max(int(payload.get("height") or min_height), min_height)

    window = QWidget()
    window.setWindowTitle("Gmail Auto v2")
    window.setFixedSize(width, height)
    window.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
    window.setAttribute(Qt.WA_ShowWithoutActivating)
    window.setAttribute(Qt.WA_TranslucentBackground)

    card = QFrame()
    card.setObjectName("card")
    shadow = QGraphicsDropShadowEffect(card)
    shadow.setBlurRadius(36)
    shadow.setOffset(0, 12)
    shadow.setColor(QColor(88, 106, 135, 95))
    card.setGraphicsEffect(shadow)

    status_label = selectable_label("", QFont("Microsoft YaHei UI", 10), word_wrap=True)
    status_label.setObjectName("statusLabel")
    status_label.setVisible(False)

    title_icon = QLabel("\u2709")
    title_icon.setObjectName("titleIcon")
    title_icon.setAlignment(Qt.AlignCenter)
    title_icon.setFixedSize(54, 54)

    title_label = selectable_label(
        str(payload.get("subject") or TEXT["title"]),
        QFont("Microsoft YaHei UI", 20, QFont.Bold),
        word_wrap=True,
    )
    title_label.setObjectName("titleLabel")
    title_label.setMinimumHeight(76)
    title_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

    close_button = QPushButton(f"\u2715   {TEXT['close']}")
    close_button.setObjectName("closeButton")
    close_button.setFixedSize(116, 46)
    close_button.clicked.connect(app.quit)

    header_layout = QHBoxLayout()
    header_layout.setContentsMargins(0, 0, 0, 0)
    header_layout.setSpacing(18)
    header_layout.addWidget(title_icon)
    header_layout.addWidget(title_label, stretch=1)
    header_layout.addWidget(close_button)

    meta_frame = QFrame()
    meta_frame.setObjectName("metaFrame")
    meta_frame.setFixedHeight(232)
    meta_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    meta_layout = QVBoxLayout(meta_frame)
    meta_layout.setContentsMargins(0, 8, 0, 14)
    meta_layout.setSpacing(10)
    reply_link = build_reply_link(
        str(payload.get("sender") or ""),
        str(payload.get("subject") or ""),
    )
    fallback_company, fallback_position = split_company_position(
        str(payload.get("company_position") or ""),
        TEXT["unknown_company"],
        TEXT["unknown_position"],
    )

    for icon, label, value, link_url in [
        ("", TEXT["sender"], payload.get("sender") or TEXT["unknown"], reply_link),
        ("", TEXT["date"], payload.get("date") or TEXT["unknown"], ""),
        ("", TEXT["category"], payload.get("category") or TEXT["unknown"], ""),
        ("", TEXT["company"], payload.get("company") or fallback_company, ""),
        ("", TEXT["position"], payload.get("position") or fallback_position, ""),
    ]:
        meta_layout.addLayout(meta_row(icon, label, str(value), link_url=link_url))

    action_layout = QHBoxLayout()
    action_layout.setContentsMargins(0, 0, 0, 0)
    action_layout.setSpacing(20)
    action_buttons = []

    archive_button = QPushButton(TEXT["archive"])
    archive_button.setProperty("mailAction", "archive_toggle")
    archive_button.setFixedHeight(48)
    update_archive_button(archive_button, archived=False)
    archive_button.setEnabled(bool(message_id))
    archive_button.clicked.connect(
        make_action_handler(
            lambda: archive_toggle_action(archive_button),
            message_id,
            status_label,
            action_buttons,
        )
    )
    action_layout.addWidget(archive_button)
    action_buttons.append(archive_button)

    delete_button = QPushButton(TEXT["delete"])
    delete_button.setProperty("mailAction", "delete_toggle")
    delete_button.setFixedHeight(48)
    update_delete_button(delete_button, deleted=False)
    delete_button.setEnabled(bool(message_id))
    delete_button.clicked.connect(
        make_action_handler(
            lambda: delete_toggle_action(delete_button),
            message_id,
            status_label,
            action_buttons,
        )
    )
    action_layout.addWidget(delete_button)
    action_buttons.append(delete_button)

    star_button = QPushButton()
    star_button.setProperty("mailAction", "star_toggle")
    star_button.setFixedHeight(48)
    update_star_button(star_button, bool(payload.get("starred")))
    star_button.setEnabled(bool(message_id))
    star_button.clicked.connect(
        make_action_handler(
            lambda: star_toggle_action(star_button),
            message_id,
            status_label,
            action_buttons,
        )
    )
    action_layout.addWidget(star_button)
    action_buttons.append(star_button)

    summary_card = QFrame()
    summary_card.setObjectName("summaryCard")
    summary_card.setMinimumHeight(112)
    summary_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    summary_card_layout = QHBoxLayout(summary_card)
    summary_card_layout.setContentsMargins(24, 20, 24, 20)
    summary_card_layout.setSpacing(18)

    summary_icon = QLabel("\u2630")
    summary_icon.setObjectName("summaryIcon")
    summary_icon.setAlignment(Qt.AlignCenter)
    summary_icon.setFixedSize(48, 48)

    summary_title = QLabel(f"{TEXT['summary']}:")
    summary_title.setObjectName("summaryTitle")
    summary_title.setFont(QFont("Microsoft YaHei UI", 13, QFont.Bold))

    summary_label = selectable_label(
        str(payload.get("summary") or TEXT["no_summary"]),
        QFont("Microsoft YaHei UI", 13),
        word_wrap=True,
    )
    summary_label.setObjectName("summaryText")
    summary_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
    summary_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    summary_text_layout = QVBoxLayout()
    summary_text_layout.setContentsMargins(0, 0, 0, 0)
    summary_text_layout.setSpacing(4)
    summary_text_layout.addWidget(summary_title)
    summary_text_layout.addWidget(summary_label)

    summary_card_layout.addWidget(summary_icon)
    summary_card_layout.addLayout(summary_text_layout, stretch=1)

    card_layout = QVBoxLayout(card)
    card_layout.setContentsMargins(36, 28, 36, 28)
    card_layout.setSpacing(14)
    card_layout.addLayout(header_layout)
    card_layout.addWidget(divider())
    card_layout.addWidget(meta_frame)
    if verification_code:
        card_layout.addWidget(
            verification_code_card(
                verification_code,
                lambda: QApplication.clipboard().setText(verification_code),
            )
        )
    card_layout.addSpacing(4)
    card_layout.addWidget(divider())
    card_layout.addLayout(action_layout)
    card_layout.addWidget(status_label)
    card_layout.addWidget(summary_card, stretch=1)

    outer_layout = QVBoxLayout(window)
    outer_layout.setContentsMargins(18, 18, 18, 22)
    outer_layout.addWidget(card)

    window.setStyleSheet(STYLESHEET)

    if not message_id:
        status_label.setText(TEXT["missing_id"])
        status_label.setVisible(True)

    move_to_screen(window, app)
    window.show()
    app.exec_()


def meta_row(icon: str, label: str, value: str, link_url: str = "") -> Any:
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QFont
    from PyQt5.QtWidgets import QHBoxLayout, QLabel

    row = QHBoxLayout()
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(14)

    if icon:
        icon_label = QLabel(icon)
        icon_label.setObjectName("metaIcon")
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setFixedWidth(36)
        icon_label.setFixedHeight(34)
        row.addWidget(icon_label)

    name_label = QLabel(f"{label}:")
    name_label.setObjectName("metaName")
    name_label.setFont(QFont("Microsoft YaHei UI", 12, QFont.Bold))
    name_label.setFixedWidth(120)
    name_label.setFixedHeight(34)

    if link_url:
        value_label = link_label(value, link_url, QFont("Microsoft YaHei UI", 12))
    else:
        value_label = selectable_label(
            value, QFont("Microsoft YaHei UI", 12), word_wrap=False
        )
    value_label.setObjectName("metaValue")
    value_label.setFixedHeight(34)
    value_label.setToolTip(value)

    row.addWidget(name_label)
    row.addWidget(value_label, stretch=1)
    return row


def verification_code_card(code: str, copy_callback: Callable[[], None]) -> Any:
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QFont
    from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

    compact_code = re.sub(r"[\s-]+", "", code)

    card = QFrame()
    card.setObjectName("verificationCodeCard")
    card.setFixedHeight(126)

    layout = QHBoxLayout(card)
    layout.setContentsMargins(34, 20, 34, 20)
    layout.setSpacing(30)

    code_title = QLabel(TEXT["verification_code"])
    code_title.setObjectName("verificationCodeTitle")
    code_title.setAlignment(Qt.AlignCenter)
    code_title.setFont(QFont("Microsoft YaHei UI", 16, QFont.Bold))

    code_value = selectable_label(
        "  ".join(compact_code),
        QFont("Microsoft YaHei UI", 28, QFont.Bold),
        word_wrap=False,
    )
    code_value.setObjectName("verificationCodeValue")
    code_value.setAlignment(Qt.AlignCenter)

    code_layout = QVBoxLayout()
    code_layout.setContentsMargins(0, 0, 0, 0)
    code_layout.setSpacing(8)
    code_layout.addWidget(code_title)
    code_layout.addWidget(code_value)

    separator = QFrame()
    separator.setObjectName("verificationCodeSeparator")
    separator.setFixedWidth(1)

    copy_button = QPushButton(f"\u29c9  {TEXT['copy_code']}")
    copy_button.setObjectName("copyCodeButton")
    copy_button.setFixedSize(260, 58)
    copy_button.clicked.connect(copy_callback)

    copy_hint = QLabel(TEXT["copy_hint"])
    copy_hint.setObjectName("copyCodeHint")
    copy_hint.setAlignment(Qt.AlignCenter)

    copy_layout = QVBoxLayout()
    copy_layout.setContentsMargins(0, 0, 0, 0)
    copy_layout.setSpacing(8)
    copy_layout.addWidget(copy_button, alignment=Qt.AlignCenter)
    copy_layout.addWidget(copy_hint, alignment=Qt.AlignCenter)

    layout.addLayout(code_layout, stretch=1)
    layout.addWidget(separator)
    layout.addLayout(copy_layout, stretch=0)
    return card


def divider() -> Any:
    from PyQt5.QtWidgets import QFrame

    line = QFrame()
    line.setObjectName("divider")
    line.setFrameShape(QFrame.HLine)
    return line


def split_company_position(value: str, unknown_company: str, unknown_position: str) -> tuple[str, str]:
    if not value.strip():
        return unknown_company, unknown_position

    company, separator, position = value.partition(" / ")
    if not separator:
        return value.strip(), unknown_position

    return company.strip() or unknown_company, position.strip() or unknown_position


def make_action_handler(
    action: str | Callable[[], str],
    message_id: str,
    status_label: Any,
    action_buttons: list[Any],
) -> Callable[[], None]:
    def handler() -> None:
        from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot

        class MailActionWorker(QObject):
            finished = pyqtSignal(str, object)

            def __init__(self, action_name: str, mail_message_id: str) -> None:
                super().__init__()
                self.action_name = action_name
                self.mail_message_id = mail_message_id

            def run(self) -> None:
                error: Exception | None = None
                try:
                    run_mail_action(self.action_name, self.mail_message_id)
                except Exception as exc:
                    error = exc
                self.finished.emit(self.action_name, error)

        class MailActionFinishProxy(QObject):
            @pyqtSlot(str, object)
            def finish(self, action_name: str, error: object) -> None:
                if error:
                    status_label.setText(f"{TEXT['failed']}: {error}")
                    set_action_buttons_enabled(action_buttons, True, message_id)
                else:
                    status_label.setText(f"{TEXT['done']}: {action_label(action_name)}")
                    if action_name in {"archive", "unarchive"}:
                        mark_archive_toggled(action_buttons, action_name == "archive")
                        set_action_buttons_enabled(action_buttons, True, message_id)
                    elif action_name in {"delete", "restore"}:
                        mark_delete_toggled(action_buttons, action_name == "delete")
                        set_action_buttons_enabled(action_buttons, True, message_id)
                    elif action_name in {"star", "unstar"}:
                        mark_star_toggled(action_buttons, action_name == "star")
                        set_action_buttons_enabled(action_buttons, True, message_id)
                    else:
                        set_action_buttons_enabled(action_buttons, True, message_id)
                thread.quit()

        action_name = action() if callable(action) else action
        set_action_buttons_enabled(action_buttons, False, message_id)
        status_label.setText(f"{TEXT['working']} {action_label(action_name)}")
        status_label.setVisible(True)

        thread = QThread()
        worker = MailActionWorker(action_name, message_id)
        finish_proxy = MailActionFinishProxy()
        worker.moveToThread(thread)

        active_actions = getattr(status_label, "_active_mail_actions", None)
        if active_actions is None:
            active_actions = []
            setattr(status_label, "_active_mail_actions", active_actions)
        active_actions.append((thread, worker, finish_proxy))

        def cleanup() -> None:
            try:
                active_actions.remove((thread, worker, finish_proxy))
            except ValueError:
                pass

        thread.started.connect(worker.run)
        worker.finished.connect(finish_proxy.finish)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(cleanup)
        thread.start()

    return handler


def set_action_buttons_enabled(
    action_buttons: list[Any],
    enabled: bool,
    message_id: str,
) -> None:
    for button in action_buttons:
        button.setEnabled(enabled and bool(message_id))


def archive_toggle_action(button: Any) -> str:
    return "unarchive" if bool(button.property("archived")) else "archive"


def delete_toggle_action(button: Any) -> str:
    return "restore" if bool(button.property("deleted")) else "delete"


def star_toggle_action(button: Any) -> str:
    return "unstar" if bool(button.property("starred")) else "star"


def mark_archive_toggled(action_buttons: list[Any], archived: bool) -> None:
    for button in action_buttons:
        if button.property("mailAction") == "archive_toggle":
            update_archive_button(button, archived)
            return


def mark_delete_toggled(action_buttons: list[Any], deleted: bool) -> None:
    for button in action_buttons:
        if button.property("mailAction") == "delete_toggle":
            update_delete_button(button, deleted)
            return


def mark_star_toggled(action_buttons: list[Any], starred: bool) -> None:
    for button in action_buttons:
        if button.property("mailAction") == "star_toggle":
            update_star_button(button, starred)
            return


def update_archive_button(button: Any, archived: bool) -> None:
    button.setProperty("archived", archived)
    if archived:
        button.setText(TEXT["unarchive"])
        set_button_icon(button, "archive-muted")
        button.setObjectName("archivedButton")
    else:
        button.setText(TEXT["archive"])
        set_button_icon(button, "archive-blue")
        button.setObjectName("primaryButton")

    button.style().unpolish(button)
    button.style().polish(button)


def update_delete_button(button: Any, deleted: bool) -> None:
    button.setProperty("deleted", deleted)
    if deleted:
        button.setText(TEXT["restore"])
        set_button_icon(button, "trash-muted")
        button.setObjectName("deletedButton")
    else:
        button.setText(TEXT["delete"])
        set_button_icon(button, "trash-red")
        button.setObjectName("dangerButton")

    button.style().unpolish(button)
    button.style().polish(button)


def update_star_button(button: Any, starred: bool) -> None:
    button.setProperty("starred", starred)
    if starred:
        button.setText(TEXT["unstar"])
        set_button_icon(button, "star-filled-blue")
        button.setObjectName("starredButton")
    else:
        button.setText(TEXT["star"])
        set_button_icon(button, "star-outline-dark")
        button.setObjectName("actionButton")

    button.style().unpolish(button)
    button.style().polish(button)


def set_button_icon(button: Any, icon_name: str) -> None:
    from PyQt5.QtCore import QSize
    from PyQt5.QtGui import QIcon

    button.setIcon(QIcon(str(ICON_DIR / f"{icon_name}.svg")))
    button.setIconSize(QSize(26, 26))


def run_mail_action(action: str, message_id: str) -> None:
    from gmail_auto_v2.gmail_client import (
        archive_message,
        authenticate_gmail,
        star_message,
        trash_message,
        unarchive_message,
        unstar_message,
        untrash_message,
    )

    service = authenticate_gmail()
    actions = {
        "archive": archive_message,
        "unarchive": unarchive_message,
        "delete": trash_message,
        "restore": untrash_message,
        "star": star_message,
        "unstar": unstar_message,
    }
    try:
        action_func = actions[action]
    except KeyError as exc:
        raise ValueError(f"{TEXT['unknown_action']}: {action}") from exc

    action_func(service, message_id)


def action_label(action: str) -> str:
    return {
        "archive": TEXT["archive"],
        "unarchive": TEXT["unarchive"],
        "delete": TEXT["delete"],
        "restore": TEXT["restore"],
        "star": TEXT["star"],
        "unstar": TEXT["unstar"],
    }.get(action, action)


def selectable_label(
    text: str,
    font: Any,
    word_wrap: bool = False,
) -> Any:
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import QLabel

    label = QLabel(text)
    label.setFont(font)
    label.setWordWrap(word_wrap)
    label.setTextInteractionFlags(Qt.TextSelectableByMouse)
    return label


def link_label(text: str, url: str, font: Any) -> Any:
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import QLabel

    label = QLabel(f'<a href="{escape(url, quote=True)}">{escape(text)}</a>')
    label.setFont(font)
    label.setTextFormat(Qt.RichText)
    label.setTextInteractionFlags(Qt.TextBrowserInteraction)
    label.setOpenExternalLinks(True)
    return label


def build_reply_link(sender: str, subject: str) -> str:
    _, email_address = parseaddr(sender)
    if not email_address:
        return ""

    reply_subject = subject.strip()
    if reply_subject and not reply_subject.lower().startswith("re:"):
        reply_subject = f"Re: {reply_subject}"

    query = urlencode({"subject": reply_subject}) if reply_subject else ""
    return f"mailto:{email_address}?{query}" if query else f"mailto:{email_address}"


def move_to_screen(window: Any, app: Any) -> None:
    screens = app.screens()
    if not screens:
        return

    screen_index = TARGET_SCREEN_INDEX
    if screen_index < 0 or screen_index >= len(screens):
        screen_index = 0

    area = screens[screen_index].availableGeometry()
    margin = 20
    x = area.x() + area.width() - window.width() - margin
    y = area.y() + area.height() - window.height() - margin
    window.move(x, y)


def _displayable_verification_code(value: str) -> str:
    code = value.strip()
    compact_code = re.sub(r"[\s-]+", "", code)
    if not 4 <= len(compact_code) <= 12:
        return ""
    if not re.fullmatch(r"[A-Za-z0-9]+", compact_code):
        return ""
    if compact_code.isalpha() and len(compact_code) > 8:
        return ""
    if not re.search(r"\d", compact_code):
        return ""
    return code


STYLESHEET = """
QWidget {
    background: transparent;
    color: #0b1224;
    font-family: "Microsoft YaHei UI", "Segoe UI";
}

QFrame#card {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 18px;
}

QLabel {
    border: none;
    background: transparent;
    color: #0b1224;
}

QLabel#titleLabel {
    color: #061329;
    font-size: 20pt;
    font-weight: 800;
}

QLabel#titleIcon {
    color: #ffffff;
    background-color: #2d73f5;
    border-radius: 27px;
    font-size: 24pt;
    font-weight: 600;
}

QLabel#metaIcon {
    color: #6d82ad;
    font-size: 14pt;
}

QLabel#metaName {
    color: #0b1224;
    font-size: 12pt;
    font-weight: 700;
}

QLabel#metaValue {
    color: #111827;
    font-size: 12pt;
}

QFrame#divider {
    border: none;
    background-color: #e5eaf2;
    min-height: 1px;
    max-height: 1px;
}

QFrame#verificationCodeCard {
    background-color: #ffffff;
    border: 1px solid #a9c8ff;
    border-radius: 18px;
}

QLabel#verificationCodeTitle {
    color: #123ca8;
    font-size: 16pt;
    font-weight: 800;
}

QLabel#verificationCodeValue {
    color: #1261e8;
    font-size: 28pt;
    font-weight: 800;
    letter-spacing: 0;
}

QFrame#verificationCodeSeparator {
    border: none;
    border-left: 1px dashed #a9c8ff;
    background: transparent;
}

QLabel#copyCodeHint {
    color: #74809c;
    font-size: 12pt;
}

QFrame#summaryCard {
    background-color: #f8fbff;
    border: 1px solid #e0e8f5;
    border-left: 5px solid #1a73e8;
    border-radius: 10px;
}

QLabel#summaryIcon {
    color: #ffffff;
    background-color: #a7c7fa;
    border-radius: 24px;
    font-size: 18pt;
    font-weight: 700;
}

QLabel#summaryTitle,
QLabel#summaryText {
    font-size: 13pt;
}

QLabel#statusLabel {
    color: #476385;
    font-size: 10pt;
}

QPushButton {
    background-color: #ffffff;
    border: 1px solid #d8e0eb;
    border-radius: 24px;
    color: #0b1224;
    font-family: "Microsoft YaHei UI";
    font-size: 13pt;
    font-weight: 600;
    padding: 0 18px;
}

QPushButton#closeButton {
    border-radius: 10px;
    color: #0f172a;
    background-color: #ffffff;
    border: 1px solid #d8e0eb;
    font-size: 12pt;
    padding: 0 14px;
}

QPushButton#primaryButton {
    color: #0b6fea;
    background-color: #f2f7ff;
    border: 1px solid #a9c8ff;
}

QPushButton#starredButton {
    color: #0b6fea;
    background-color: #f2f7ff;
    border: 1px solid #a9c8ff;
}

QPushButton#dangerButton {
    color: #b42318;
    background-color: #fff5f5;
    border: 1px solid #f4b4ab;
}

QPushButton#archivedButton {
    color: #8a94a6;
    background-color: #eef1f5;
    border: 1px solid #d8dee8;
}

QPushButton#deletedButton {
    color: #8a94a6;
    background-color: #eef1f5;
    border: 1px solid #d8dee8;
}

QPushButton#copyCodeButton {
    color: #0b6fea;
    background-color: #ffffff;
    border: 1px solid #a9c8ff;
    border-radius: 14px;
    font-size: 15pt;
    font-weight: 800;
}

QPushButton:hover {
    background-color: #f3f7fc;
    border-color: #b9c7dc;
}

QPushButton#primaryButton:hover {
    background-color: #e8f2ff;
    border-color: #7fb0ff;
}

QPushButton#starredButton:hover {
    background-color: #e8f2ff;
    border-color: #7fb0ff;
}

QPushButton#dangerButton:hover {
    background-color: #ffe7e4;
    border-color: #f08a7d;
}

QPushButton#copyCodeButton:hover {
    background-color: #f2f7ff;
    border-color: #7fb0ff;
}

QPushButton:disabled {
    color: #9aa6b6;
    background-color: #f6f8fb;
    border-color: #e2e8f0;
}
"""


if __name__ == "__main__":
    main()
