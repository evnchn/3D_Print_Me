from nicegui import ui


def unified_header(header_str, back_location=""):
    with ui.header().classes("w-full bg-gray-100 p-4"):
        with ui.row().classes("w-full"):
            if back_location:
                ui.button("Back", on_click=lambda: ui.navigate.to(back_location)).classes("shrink-0")
            ui.label(header_str).classes('text-2xl flex-grow font-bold text-black')
            with ui.row().classes("shrink-0") as injectable:
                pass
        return injectable