# VChat — WhatsApp Chat Viewer

Convert a WhatsApp export `.zip` or a standalone `_chat.txt` file into a fully viewable interactive chat — in the browser or as a shareable standalone HTML file.

---

## Project Structure

```
VChat/
├── app.py                ← Flask web server
├── requirements.txt      ← Dependency list
├── templates/
│   └── index.html        ← Web UI (runs in browser)
└── claude.md             ← Complete technical specifications & details
```

---

## Installation & How to Run

1. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Start the local server**:
   ```bash
   python app.py
   ```

3. **Open in browser**:
   Go to [http://localhost:5000](http://localhost:5000)

---

## Usage

1. Export a chat from WhatsApp (either with media to get a `.zip` file, or without media to get a `.txt` file).
2. Upload the `.zip` or `.txt` file to the VChat web app.
3. Select your name from the dropdown to align the message bubbles properly (your messages will be on the right, others on the left).
4. Click **View Chat** to view the interactive thread.
5. Click **Download HTML** at the top right to download a single self-contained, offline-viewable `.html` file.
