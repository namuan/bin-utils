import flet
from flet import IconButton, MainAxisAlignment, Page, Row, TextAlign, TextField, icons


def main(page: Page):
    page.title = "Flet Counter"
    page.vertical_alignment = "center"

    txt_number = TextField(value="0", text_align=TextAlign.RIGHT, width=100)

    def plus_click(e):
        txt_number.value = str(int(txt_number.value) + 1)
        page.update()

    def minus_click(e):
        txt_number.value = str(int(txt_number.value) - 1)
        page.update()

    page.add(
        Row(
            [
                IconButton(icons.REMOVE, on_click=minus_click),
                txt_number,
                IconButton(icons.ADD, on_click=plus_click),
            ],
            alignment=MainAxisAlignment.CENTER,
        )
    )


flet.app(target=main)
