# RadioFreeGPT

**RadioFreeGPT** is a terminal-based graphical Spotify client powered by generative AI. It combines AI-driven prompts with Spotify integration to create a visually engaging and smart command-line radio DJ experience. Built using Python and rich CLI components, it turns your terminal into a dynamic radio control deck.

---

![RadioFreeGPT UI](assets/broken_social_scene.png)

---

## Features

- GPT-powered DJ commentary and recommendations
- Spotify integration for playback and control
- Terminal graphics using `rich` and `textual`
- AI-generated playlists, transitions, and chat
- Modular design with plugin support for show scripts

---

## Getting Started

### Prerequisites

- Python 3.10 or newer
- Spotify Developer credentials (Client ID and Secret)

### Setup

```bash
git clone https://github.com/braydio/RadioFreeGPT.git
cd RadioFreeGPT
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp example.env .env
```

Edit `.env` using the keys shown in `example.env`. At minimum provide your
Spotify credentials and `OPENAI_API_KEY`. You may also supply Last.fm
values if you want scrobbling support.

---

## Optional: Last.fm Integration

RadioFreeGPT supports optional Last.fm integration for scrobbling tracks and submitting "now playing" updates to your Last.fm account.

### To enable:

1. Create an account and app at https://www.last.fm/api/account/create
2. Add the following entries to your `.env`:

```env
LASTFM_API_KEY=your_key_here
LASTFM_API_SECRET=your_secret_here
```

3. Run `python main.py` once and follow the authorization link that appears.
   After approving access, a `LASTFM_SESSION_KEY` will be stored in your `.env`
   file for future sessions.

---

## Usage

Run the application from your terminal:

```bash
source .venv/bin/activate
python main.py
```

Controls and navigation are rendered via the terminal interface.

---

## Project Structure

```
RadioFreeGPT/
├── assets/                # UI images and branding
├── scripts/               # CLI utilities and sync tools
├── main.py                # Entry point for terminal UI
├── spotify_utils.py       # Spotify control logic
├── lastfm_utils.py        # Optional Last.fm support
├── prompts/               # GPT prompt configurations
├── requirements.txt       # Python dependencies
└── README.md
```

---

## Contributing

We welcome contributions. To submit a pull request:

- Follow existing modular structure
- Use Python type hints and docstrings
- Test with multiple terminal sizes and themes

---

## License

MIT License © Braydio
