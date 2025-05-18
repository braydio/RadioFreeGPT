# 🧠 **RadioFreeDJ Dev Plan**

> Building an intelligent, terminal-based Spotify assistant with GPT-powered DJing, real-time control, and persistent music intelligence.

---

## 💾 **Project Summary**

RadioFreeDJ is a terminal-based music assistant that integrates:

* Real-time Spotify playback via the Spotify Web API
* GPT-powered playlist and recommendation logic
* Terminal UI using `rich`
* Lyrics syncing with `lrclib` and Genius
* Custom input handling via `keyboard` for keypress responsiveness

The goal is to evolve it into a **minimal, intelligent music experience** with:

* Fully local and Spotify-integrated queueing
* Song history and feedback
* Persistent user preferences
* GPT prompt control and context memory

---

## 📌 Core Features (Planned)

| Feature                  | Description                                  |
| ------------------------ | -------------------------------------------- |
| 🎧 Playback Control      | Pause, resume, skip, volume, transfer device |
| 🎺 Real-Time Input       | Keyboard input triggers actions immediately  |
| 🧠 GPT as DJ             | GPT recommends and queues tracks only        |
| 📚 History Log           | Store and display song history with metadata |
| 📂 Local Playlists       | Save liked songs/playlists locally for now   |
| 📈 Feedback Tracking     | Record skips, plays, likes, recommendations  |
| 🛠 Configurable Prompts  | System/user prompts loaded from JSON/YAML    |
| 🧠 GPT Contextual Memory | Feed user feedback into GPT prompts          |

---

## ✅ Current Functionality Summary

| Function              | Status                              |
| --------------------- | ----------------------------------- |
| GPT Recommendations   | ✅ Working via `gpt_dj.py`           |
| Spotify Playback      | ✅ Search + play URI                 |
| Terminal UI           | ✅ Rich-powered split layout         |
| Lyrics Sync           | ✅ via `lrclib` + Genius fallback    |
| Keypress Controls     | ✅ via `keyboard` (recent addition)  |
| Menu / Input Dispatch | ✅ Real-time queue + toggle commands |
| Command Logging       | ✅ commands.log exists               |

---

## 📋 Development Checklist

### Phase 1 — Foundation

* [x] Real-time input with `keyboard`
* [x] Spotipy-based playback & control
* [ ] ⏸ `pause()`, `resume()`, `next()`, `previous()` methods added
* [ ] 🎧 Key bindings: `p`, `→`, `←`, `+`, `-`
* [ ] 🧠 GPT recommendations: always queue, never auto-play
* [ ] 📝 Write song history to `song_history.log`

  * Include: time, source (user vs GPT), play/skipped, track/artist
* [ ] 📁 Save liked songs to `~/.radiofreedj/saved_songs.json`

---

### Phase 2 — Enhanced State Management

* [ ] Create `history.py` module

  * Append to and read from song history
  * Flag songs with metadata: source, skip count, like flag
* [ ] Add `feedback.py`

  * Track skip counts, GPT rec counts, user likes
  * Store per-artist and per-track feedback
* [ ] Add `save_song()` and `save_playlist()` commands (local)
* [ ] Save GPT responses with ID → history metadata

---

### Phase 3 — Config & Prompts

* [ ] Create `config.json` or `config.yaml` in project root

  * Load system prompt, user prompt templates
* [ ] Modify `gpt_dj.py` to load prompts from config
* [ ] Allow CLI arg to reload prompts without restarting

---

### Phase 4 — Views, Metrics, UI

* [ ] `[v]` key to toggle between views: GPT log / song history
* [ ] Show song stats panel (skip count, likes, GPT rec count)
* [ ] Migrate command log to `~/.radiofreedj/commands/`
* [ ] Option to export saved songs to Spotify playlist (future)

---

### Phase 5 — Smart GPT Context

* [ ] Feed GPT info on:

  * Previous songs played
  * Songs skipped/liked
  * Recent GPT suggestions
* [ ] Adjust prompt dynamically via template engine
* [ ] Save GPT suggestions to a local `recommendations.log`

---

## 🗂 Suggested File Additions

| File              | Purpose                          |
| ----------------- | -------------------------------- |
| `history.py`      | Log + retrieve played songs      |
| `feedback.py`     | Track likes, skips, GPT stats    |
| `config.json`     | User/system prompts, preferences |
| `~/.radiofreedj/` | Store logs, saved songs, config  |

---

## 📌 Suggested Log Format for Song History

```json
{
  "timestamp": "2025-05-08T12:30:12",
  "track_name": "Seville",
  "artist_name": "Pinback",
  "source": "gpt",  // or "user"
  "action": "played",  // or "skipped", "liked"
  "recommendation_id": "gpt-20250508-xyz"
}
```

---

## 🛝 Next Steps

1. ✅ Add playback control functions (`pause`, `resume`, `next`, `prev`)
2. ✅ Bind `p`, `→`, `←`, etc. in `read_keys()`
3. ✅ Update GPT logic to only queue, not play
4. 🛠 Build song history logger
5. 🛠 Create basic `~/.radiofreedj/saved_songs.json`
