from shiny import App, ui

app_ui = ui.page_fluid(ui.h1("Hello — HF Breeding Planner"))


def server(input, output, session):  # type: ignore[no-untyped-def]
    pass


app = App(app_ui, server)
