# ScrapeLite

A small local web app that searches scientific databases for papers and pulls
structured data out of them using a local LLM (Ollama) — no code or terminal needed.

**The whole flow:** type search terms → pick websites → **Search** → open-access
papers are fetched → an LLM reads the full text and extracts whatever you asked
for → everything lands in an Excel file in the `output/` folder.

---

## Quick start (for someone who doesn't write code)

1. **One time only:** double-click `setup.bat`.
   It installs Python (if missing), creates an isolated Python environment,
   installs the packages, installs Ollama (if missing) and downloads the model.
2. **Every time:** double-click `start.bat`.
   A browser opens at http://127.0.0.1:5000 — that's the whole app.
3. Search for papers, then click **Extract data** and describe what you want
   (e.g. *"every mutation tested and whether it increased or decreased function"*).
4. Results are saved automatically in the `output/` folder. Use the
   **📂 Open output folder** button in the app to jump straight there.

That's it. The Excel files are the output; the browser is just the control panel.



## Requirements

- Windows 10/11 (macOS/Linux also work if you run `python app.py` directly)
- Python 3.10+ (installed automatically by `setup.bat` via winget if missing)
- [Ollama](https://ollama.com) (installed automatically by `setup.bat` if missing)
- ~8 GB free disk for the model, plus a few GB of RAM to run it
