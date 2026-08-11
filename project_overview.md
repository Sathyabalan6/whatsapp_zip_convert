# VChat — Interactive WhatsApp Conversation Viewer

**VChat** is a privacy-focused local web utility designed to parse WhatsApp exports (ZIP archives containing text files and raw attachments, or standalone `.txt` transcripts) and compile them into a high-fidelity, interactive HTML chat simulator. 

The application is structured to feel native, clean, and modern—reproducing the **2024 WhatsApp UI/UX overhaul** specifications (adaptive dark mode, outline icons, mobile navigation rails)—and offers a completely offline-portable output format containing all dynamic assets, audio players, video screens, and emoji reaction widgets.

---

## 1. Core Vision & Use Cases

*   **Preserving Memories**: Allows users to back up, archive, and view personal chat histories (such as transcripts with family, friends, or late loved ones) in a rich, readable format rather than a dry text log.
*   **Legal & Compliance Reviews**: Provides legal firms, compliance officers, and researchers a clean, visual representation of chat transcripts with inline attachments, captions, and emoji reactions, making chats searchable and chronologically readable.
*   **Media Production & Mockups**: Serves as a high-fidelity simulator for creators, novelists, and filmmakers looking to generate screen-accurate WhatsApp interfaces with fully customizable elements.
*   **Local & Secure Processing**: The processing is done entirely in-memory on the user's host environment. No chat contents or attachment bytes are uploaded to remote servers or third-party cloud engines.

---

## 2. Technical Stack

*   **Backend Engine (Python / Flask)**:
    *   **In-Memory File Processing**: Extracts ZIP archives on the fly using `zipfile` and `io.BytesIO`. No disk writes are performed for temporary files.
    *   **Heuristic Transcript Parser**: Matches message log timestamps, captures multi-line continuations, extracts system actions, and links parsed files to local attachments.
    *   **Audio Length Detection**: Reads raw voice note lengths (`.opus`, `.mp3`, etc.) using `mutagen`.
*   **Frontend UI System (HTML5 / Vanilla CSS / JavaScript)**:
    *   **Modern Design Tokens**: HSL variables, transitions, Outfit font structures, and SVG outlines aligning with Meta’s 2024 visual update.
    *   **No Client-Side Dependencies**: Relies completely on vanilla web tech—no large NPM builds or external assets required.
*   **Standalone Packager**:
    *   Serializes message arrays and encodes all attachments (images, voice notes, videos) as Base64 strings.
    *   Injects runtime interactive scripts into a single standalone HTML file for distribution.

---

## 3. Implemented Features & Functionality

### ── Parser & Log Compiler
*   **Regex Timestamp Adaptation**: Employs a fallback regex chain parsing a wide variety of iOS and Android export formats.
*   **Reaction Stitching**: Suppresses standard chat logs that look like `"[Date, Time] Sender reacted with: Emoji"` and aggregates them as metadata on their parent message.
*   **Dynamic Media Detection**: Separates files into inline voice notes, photos, videos, and document attachments based on file extensions.
*   **Caption Extraction**: Detects line breaks following attachment markers and parses subsequent text as media captions.

### ── Layout & Visual System
*   **Responsive Dual Viewport Layout**: 
    *   *Desktop*: Dual-panel system containing a left-hand navigation list and right-hand chat screen.
    *   *Mobile*: A single active viewport. Clicking a contact slides the conversation view into place, utilizing a bottom navigation rail (Chats, Updates, Communities) and outline SVG icons.
*   **Adaptive HSL Names**: Senders are assigned unique name colors calculated dynamically. Color parameters (lightness) automatically adjust based on the current theme to maintain contrast.
*   **Light / Dark Themes**: Toggle between complete light and dark modes with a single click.

### ── Rich Chat Components
*   **Dynamic Audio Nodes**: Custom audio widgets containing play/pause toggles, elapsed timers, and CSS-animated waveforms that flex in height and color based on the parent bubble (incoming vs. outgoing).
*   **Inline Video Attachments**: Incorporates `<video>` cards that play video attachments (`.mp4`, `.mov`, `.webm`) natively.
*   **Image Zoom Overlay**: Lightbox modal for viewing image attachments in full screen, supporting click-outside dismissals.
*   **Smart Link Previews**: Scans incoming text messages for URLs and embeds structural preview cards showing the domain, page title, and clickable anchors.
*   **Unified Search**: Features synchronized dual search inputs (top header + sidebar panel) that filter messages across sender names, text content, media captions, and file names with empty date-header suppression.

### ── Standalone HTML Exports
*   **Fully Self-Contained**: Compiles all CSS variables, SVG icons, raw text manifests, and Base64-encoded attachment assets into a single file.
*   **Interactive Offline Scripts**:
    *   *Offline Audio Players*: Direct playback of Base64 voice note streams.
    *   *Offline Reaction Picker*: Bubble hover elements remain functional. Users can click emojis to toggle local reaction arrays.
    *   *Offline Search Bar*: Searches and filters rows instantly using local document querying.
    *   *Offline Theme Changer*: Switches stylesheet HSL palettes entirely client-side.

---

## 4. Directions for Future Expansion (Ideas to Pitch to another AI)

To further improve the concept, consider the following areas for expansion:

### A. Advanced Analytics Dashboard (Chat Stats)
*   **Interaction Heatmaps**: Visualizes message frequency by day of the week, hour of the day, and seasonal trends.
*   **Engagement Metrics**: Renders charts showing who initiates conversations, average reply latency, word counts, and reaction ratios.
*   **Frequently Used Words**: Word clouds or tables detailing vocabulary trends and favorite emoji indicators.

### B. Machine Learning & Natural Language Processing (NLP)
*   **Topic Modeling & Auto-Tagging**: Groups historical logs into topics (e.g. "Work", "Vacation planning", "Recipes") using lightweight client-side models.
*   **Sentiment Analysis Timeline**: Displays emotional highs and lows throughout the chat's history.
*   **AI Search Assistant**: Integrates semantic search (using local vector embeddings) to query the chat history (e.g., "Where did we say we wanted to go for dinner?").

### C. Enhanced Exporter Output Formats
*   **PDF Report Generator**: Renders the conversation view into a paginated, print-ready PDF containing inline media placements (for evidence submission or physical keepsake books).
*   **Interactive JSON/SQLite Export**: Compiles raw structural data for use in developer environments.

### D. Advanced Media Transcriptions
*   **Voice-to-Text Transcription**: Automatically transcribes voice notes inline using local speech-recognition models (e.g., Whisper API or lightweight WebAssembly modules).
*   **OCR for Images**: Scans image attachments for text and lists recognized words in search indexes.

### E. Collaborative Tools & Annotations
*   **Shared Notes/Bookmarks**: Enables readers to highlight messages, add personal comments, and export curated subsets of the conversation.
*   **Redaction/Anonymizer Mode**: Instantly hides names, phone numbers, and images before exporting, ensuring compliance when sharing sensitive transcripts.
