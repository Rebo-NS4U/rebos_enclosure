# Screen text

Press **Super+Ctrl+T** (or run `wayland-screenshot ocr`) and drag a box around
text in any application, image, or video. Escape cancels selection.
An editable result window offers **Copy** and **Web Search**. Copy closes the
window; paste into your destination with Ctrl+V (Ctrl+Shift+V in terminals).
Escape closes the result window; Ctrl+Enter copies it.

Recognition uses local Tesseract with English data; no capture is uploaded and
temporary images are deleted even when recognition fails. Web Search explicitly
sends the edited text to Google through your default browser. OCR can misread
small or stylized text: review the result before copying or searching.

Dependencies (`desktop/packages/core.txt`): Quickshell, Python, grim, slurp,
wl-clipboard, tesseract and tesseract-data-eng. No additional packages are needed.
