import flet as ft
from EmailShareScreen import build_share_view


def main(page: ft.Page):
    page.title = "Share test"
    page.padding = 24

    def finished():
        page.controls.clear()
        page.add(ft.Text("Back to start screen", size=24))
        page.update()

    page.add(build_share_view(
        page,
        stats_path="putt_stats.json",  # doesn't need to exist while USE_MOCK = True
        video_path="putt.mp4",         # !!video path may need to be changed when in prod
        on_finished=finished,
    ))


ft.run(main)