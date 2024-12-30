from nicegui import ui

MARKDOWN_FONT_SIZE_CSS = """
.nicegui-editor .q-editor__content h1,
.nicegui-markdown h1 {
  font-size: 2.25rem; /* from 3rem */
  line-height: 1;
  margin-bottom: 1rem;
  margin-top: 1.5rem;
  font-weight: 300;
}
.nicegui-editor .q-editor__content h2,
.nicegui-markdown h2 {
  font-size: 1.875rem; /* from 2.25rem */
  line-height: 2.5rem;
  margin-bottom: 0.75rem;
  margin-top: 1.25rem;
  font-weight: 300;
}
.nicegui-editor .q-editor__content h3,
.nicegui-markdown h3 {
  font-size: 1.5rem; /* from 1.875rem */
  line-height: 2.25rem;
  margin-bottom: 0.5rem;
  margin-top: 1rem;
  font-weight: 400;
}
.nicegui-editor .q-editor__content h4,
.nicegui-markdown h4 {
  font-size: 1.25rem; /* from 1.5rem */
  line-height: 2rem;
  margin-bottom: 0.25rem;
  margin-top: 0.75rem;
  font-weight: 400;
}
.nicegui-editor .q-editor__content h5,
.nicegui-markdown h5 {
  font-size: 1.125rem; /* from 1.25rem */
  line-height: 1.75rem;
  margin-bottom: 0.125rem;
  margin-top: 0.5rem;
  font-weight: 400;
}
.nicegui-editor .q-editor__content h6,
.nicegui-markdown h6 {
  font-size: 1rem; /* from 1.125rem */
  line-height: 1.75rem;
  margin-bottom: 0.125rem;
  margin-top: 0.5rem;
  font-weight: 500;
}
"""

def patch_markdown_font_size():
    ui.add_css(MARKDOWN_FONT_SIZE_CSS)