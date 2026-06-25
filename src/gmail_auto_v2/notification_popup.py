from __future__ import annotations

import json
import sys
from typing import Any, Callable

TARGET_SCREEN_INDEX = 0
MIN_POPUP_WIDTH = 920
MIN_POPUP_HEIGHT = 600

TEXT = {
    "title": "New Email Analysis Complete",
    "close": "Close",
    "sender": "Sender",
    "category": "Category",
    "company_position": "Company/Position",
    "unknown": "unknown",
    "unknown_company_position": "Unknown company / Unknown position",
    "verification_code": "Verification code",
    "summary": "Summary",
    "no_summary": "No summary",
    "copy_code": "Copy code",
    "archive": "Archive",
    "star": "Star",
    "unstar": "Unstar",
    "missing_id": "Missing message_id; this email cannot be modified.",
    "failed": "Action failed",
    "done": "Done",
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
    height = max(int(payload.get("height") or MIN_POPUP_HEIGHT), MIN_POPUP_HEIGHT)
    message_id = str(payload.get("message_id") or "").strip()
    verification_code = str(payload.get("verification_code") or "").strip()

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
    meta_frame.setFixedHeight(164 if verification_code else 116)
    meta_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    meta_layout = QVBoxLayout(meta_frame)
    meta_layout.setContentsMargins(0, 8, 0, 14)
    meta_layout.setSpacing(10)
    for icon, label, value in [
        ("", TEXT["sender"], payload.get("sender") or TEXT["unknown"]),
        ("", TEXT["category"], payload.get("category") or TEXT["unknown"]),
        (
            "",
            TEXT["company_position"],
            payload.get("company_position") or TEXT["unknown_company_position"],
        ),
    ]:
        meta_layout.addLayout(meta_row(icon, label, str(value)))

    if verification_code:
        meta_layout.addLayout(
            meta_row("", TEXT["verification_code"], verification_code)
        )

    action_layout = QHBoxLayout()
    action_layout.setContentsMargins(0, 0, 0, 0)
    action_layout.setSpacing(20)
    for icon, label, action in [
        ("\u25a3", TEXT["archive"], "archive"),
        ("\u2606", TEXT["star"], "star"),
        ("\u2606", TEXT["unstar"], "unstar"),
    ]:
        button = QPushButton(f"{icon}  {label}")
        button.setObjectName("primaryButton" if action == "archive" else "actionButton")
        button.setFixedHeight(48)
        button.setEnabled(bool(message_id))
        button.clicked.connect(make_action_handler(action, message_id, status_label, app))
        action_layout.addWidget(button)

    if verification_code:
        copy_code_button = QPushButton(f"\u2398  {TEXT['copy_code']}")
        copy_code_button.setObjectName("actionButton")
        copy_code_button.setFixedHeight(48)
        copy_code_button.clicked.connect(
            lambda: QApplication.clipboard().setText(verification_code)
        )
        action_layout.addWidget(copy_code_button)

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


def meta_row(icon: str, label: str, value: str) -> Any:
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

    value_label = selectable_label(value, QFont("Microsoft YaHei UI", 12), word_wrap=False)
    value_label.setObjectName("metaValue")
    value_label.setFixedHeight(34)

    row.addWidget(name_label)
    row.addWidget(value_label, stretch=1)
    return row


def divider() -> Any:
    from PyQt5.QtWidgets import QFrame

    line = QFrame()
    line.setObjectName("divider")
    line.setFrameShape(QFrame.HLine)
    return line


def make_action_handler(
    action: str,
    message_id: str,
    status_label: Any,
    app: Any,
) -> Callable[[], None]:
    def handler() -> None:
        try:
            run_mail_action(action, message_id)
        except Exception as exc:
            status_label.setText(f"{TEXT['failed']}: {exc}")
            status_label.setVisible(True)
            return

        status_label.setText(f"{TEXT['done']}: {action_label(action)}")
        status_label.setVisible(True)
        if action == "archive":
            app.quit()

    return handler


def run_mail_action(action: str, message_id: str) -> None:
    from gmail_auto_v2.gmail_client import (
        archive_message,
        authenticate_gmail,
        star_message,
        unstar_message,
    )

    service = authenticate_gmail()
    actions = {
        "archive": archive_message,
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

QPushButton:hover {
    background-color: #f3f7fc;
    border-color: #b9c7dc;
}

QPushButton#primaryButton:hover {
    background-color: #e8f2ff;
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
