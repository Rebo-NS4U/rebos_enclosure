# Screen text

Press **Super+Ctrl+T** (or run `wayland-screenshot ocr`) and drag a box around
text in any application, image, or video. A full-screen frosted-glass overlay
freezes each active display. While you drag, an accent outline shows the box
and its dimensions. Release to morph the glass into the selected region over
480 ms; the surrounding desktop blurs and an editable glass card appears.
Escape cancels selection. The card offers **Copy** and **Web Search**. Copy closes the
window; paste into your destination with Ctrl+V (Ctrl+Shift+V in terminals).
Escape closes the result window; Ctrl+Enter copies it.

Recognition uses local Tesseract with English data; no capture is uploaded and
temporary images are deleted when the window closes, including after recognition
fails. Selection coordinates map to native screenshot pixels on scaled displays. Web Search explicitly
sends the edited text to Google through your default browser. OCR can misread
small or stylized text: review the result before copying or searching.

Dependencies (`desktop/packages/core.txt`): Quickshell (Qt Quick Effects), Python, python-pillow, grim,
wl-clipboard, tesseract and tesseract-data-eng. No additional packages are needed.
