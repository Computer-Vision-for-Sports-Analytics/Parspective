import asyncio
import logging
import re
import flet as ft #flet is the interface that the email is put into
from EmailShareService import share_capture, ShareError

#install flet before running
log = logging.getLogger(__name__)

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$")

#build share view is just the formatting for the window to enter the email
def build_share_view(page: ft.Page, stats_path: str, video_path: str, on_finished):
    email = ft.TextField( 
        label="Enter email address",
        keyboard_type=ft.KeyboardType.EMAIL, # to make sure that the keyboard type is an email
        autofocus=True,
        text_size=20,
    )
    error = ft.Text("", color="red", visible=False)
    spinner = ft.ProgressRing(visible=False, width=24, height=24)
    send_btn = ft.Button("Send", disabled=True)
    skip = ft.TextButton("Skip")
    title = ft.Text("Get your results by email", size=26, weight=ft.FontWeight.BOLD)
    body = ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    # ^ formatting code with option to skip or send, also the tite is outputed seen on window
    def on_change(e):
        send_btn.disabled = not EMAIL_RE.match(email.value.strip())
        page.update()
#error checking 
    def show_error(message: str):
        error.value = message
        error.visible = True
        send_btn.text = "Retry"
        send_btn.disabled = False
        email.disabled = False
        skip.disabled = False
        spinner.visible = False
        page.update()

    async def send(e):
        address = email.value.strip()
        if not EMAIL_RE.match(address):
            return
        error.visible = False
        send_btn.disabled = True
        email.disabled = True
        skip.disabled = True
        spinner.visible = True
        page.update()
    #share_capture is built in EmailSHareScreen as well as ShareError those are called here:
        try:
            await share_capture(address, stats_path, video_path)
        except ShareError as ex:
            show_error(str(ex))  # specific message from share_service
            return
        except Exception:
            log.exception("Unexpected error while sharing")
            show_error("Something went wrong. Please try again.")
            return

        body.controls = [
            ft.Text("Sent!", size=30, weight=ft.FontWeight.BOLD),
            ft.Text(f"Check {address} for your stats and video.", size=18),
        ]
        page.update()
        await asyncio.sleep(2)
        on_finished()

    email.on_change = on_change
    email.on_submit = send
    send_btn.on_click = send
    skip.on_click = lambda e: on_finished()

    body.controls = [title, email, error, ft.Row([send_btn, spinner]), skip]
    return body
