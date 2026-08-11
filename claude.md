# VChat — WhatsApp Chat Viewer Documentation

VChat is a web application designed to convert a WhatsApp export (either a `.zip` archive containing media and the text chat, or just a standalone `_chat.txt` file) into a fully-interactive, responsive chat viewer matching the style of the WhatsApp desktop app.

---

## Project Structure

```
VChat/
├── app.py                ← Flask web server (backend parsing logic & API)
├── requirements.txt      ← Python dependency list
├── templates/
│   └── index.html        ← HTML/CSS/JS frontend template (runs in browser)
└── claude.md             ← This documentation file
```

---

## Key Features

1. **Dual Upload Formats**:
   - Supports uploading the original WhatsApp export `.zip` containing all message records and attached media (voice notes, images, documents).
   - Supports uploading just the extracted text file (e.g. `_chat.txt`) to quickly view the chat history with placeholders for any missing media.
2. **Interactive Web Interface**:
   - High-fidelity dark theme resembling the official WhatsApp Desktop app, featuring the custom doodle background.
   - Distinct, tail-bordered bubbles (dark green for sender/self, dark grey for other participants).
   - Responsive layouts, date separators, and user identity selector.
3. **Smart Media Integration**:
   - Decodes and base64-embeds voice notes (`.opus`) and images (`.jpg`, `.jpeg`, `.png`, `.webp`) dynamically.
   - Dynamic, animated waveform for voice notes with customized side-specific colors.
4. **Standalone HTML Export**:
   - Features a "Download HTML" button to compile the entire conversation, styling, and base64-encoded media into a single self-contained `.html` file that can be opened offline in any browser.

---

## Technical Specifications

### Regex Parsing Logic

The text messages are parsed using a fallback regex chain to cover Android (12-hour/24-hour), iOS format, and dot-separated date formats:

- **Android 12hr**: `^(\d{1,2}/\d{1,2}/\d{2,4}),\s*(\d{1,2}:\d{2}\s*[AP]M)\s*[-\u2013]\s*([^:]+?):\s*(.+)$`
- **Android 24hr**: `^(\d{1,2}/\d{1,2}/\d{2,4}),\s*(\d{1,2}:\d{2})\s*[-\u2013]\s*([^:]+?):\s*(.+)$`
- **iOS**: `^\[(\d{1,2}/\d{1,2}/\d{2,4}),\s*(\d{1,2}:\d{2}(?::\d{2})?)\]\s*([^:]+?):\s*(.+)$`
- **Dot Separator**: `^(\d{1,2}\.\d{1,2}\.\d{2,4}),\s*(\d{1,2}:\d{2})\s*[-\u2013]\s*([^:]+?):\s*(.+)$`
- **Attachment Pattern**: `^(\S.+?)\s*\(file attached\)$`

### Python Dependencies (`requirements.txt`)
- `flask`: Serves the application and handles conversion requests.
- `mutagen`: Extracts duration for audio/voice notes.
- `cryptography`: AES encryption support.
- `Pillow`: Image decoding and handling.

---

## How to Run the Project

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Start the Flask Web App**:
   ```bash
   python app.py
   ```

3. **View the Application**:
   Open [http://localhost:5000](http://localhost:5000) in your web browser.
