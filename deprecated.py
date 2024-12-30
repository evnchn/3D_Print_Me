from nicegui import ui

@ui.page('/upload_test')
def main_page():
    ui.label("Upload test").classes('text-2xl')

    # submit a file
    ui.upload(on_upload=lambda e: process_file(e)).classes('max-w-full')

    def process_file(e):
        print(e) # UploadEventArguments(sender=<nicegui.elements.upload.Upload object at 0x00000214AAB4E270>, client=<nicegui.client.Client object at 0x00000214AAB4DD90>, content=<tempfile.SpooledTemporaryFile object at 0x00000214AA921AE0>, name='justcard.pdf', type='application/pdf')
        # name is accessed by e.name
        # type is accessed by e.type
        content = e.content
        print("Got file", content)
        
        # save the content to a file
        with open("file", "wb") as f:
            f.write(content.read())

ui.run()