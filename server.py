"""
Investigation Server — Serves both the Case Input Form and the Timeline Viewer.

Routes:
    /              → Case Input form (main working page with calendar, dual clocks, grouped speakers)
    /timeline      → Interactive timeline (opens in separate tab, live coordinated)
    /api/case      → GET: returns current case_input.json
    /api/save      → POST: saves case_input.json
    /api/run       → POST: runs the pipeline (live Groq LLM or fast mock)
    /api/status    → GET: pipeline run status
    /output/<file> → serves generated files from output/ directory

Usage:
    python server.py          # starts on http://localhost:8500
    python server.py 9000     # starts on custom port
"""

from __future__ import annotations

import json
import os
import sys
import threading
import traceback
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
CASES_DIR = ROOT / "cases"
CASES_DIR.mkdir(parents=True, exist_ok=True)

# Pipeline execution status
_pipeline_status = {
    "running": False,
    "last_run": None,
    "error": None,
    "result": None,
    "message": "Idle",
}
_pipeline_lock = threading.Lock()


class InvestigationHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        # Clean logging
        pass

    def _send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html: str, status=200):
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path, content_type: str):
        if not path.exists():
            self.send_error(404, f"File not found: {path.name}")
            return
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/input":
            self._send_html(_INPUT_HTML)

        elif path == "/timeline":
            tl_path = ROOT / "output" / "timeline.html"
            if tl_path.exists():
                self._send_file(tl_path, "text/html; charset=utf-8")
            else:
                self._send_html(
                    "<html><body style='background:#06080f;color:#e8ecf4;font-family:Inter,sans-serif;"
                    "display:flex;align-items:center;justify-content:center;height:100vh;'>"
                    "<div style='text-align:center'><h2>No timeline generated yet</h2>"
                    "<p style='color:#8b95a8'>Run the pipeline from the Case Input tab to generate the timeline.</p>"
                    "<p><a href='/' style='color:#3b82f6'>← Go to Case Input</a></p></div></body></html>"
                )

        elif path == "/api/cases":
            cases_list = []
            if CASES_DIR.exists():
                for f in sorted(CASES_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
                    try:
                        cdata = json.loads(f.read_text(encoding="utf-8"))
                        speakers = list(dict.fromkeys(
                            st.get("speaker_name", "Unknown") for st in cdata.get("statements", [])
                        ))
                        cases_list.append({
                            "case_id": cdata.get("case_id", f.stem),
                            "incident": cdata.get("incident", ""),
                            "incident_date": cdata.get("incident_date", ""),
                            "incident_timeframe": cdata.get("incident_timeframe", ""),
                            "statement_count": len(cdata.get("statements", [])),
                            "speakers": speakers,
                            "filename": f.name,
                            "modified_at": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                        })
                    except Exception as err:
                        cases_list.append({
                            "case_id": f.stem,
                            "incident": f"Error reading file: {err}",
                            "statement_count": 0,
                            "speakers": [],
                            "filename": f.name,
                            "modified_at": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                        })
            self._send_json({"ok": True, "cases": cases_list})
            return

        elif path == "/api/case":
            query = parse_qs(parsed.query)
            req_id = query.get("id", [None])[0]
            if req_id:
                safe_req_id = "".join(c for c in req_id if c.isalnum() or c in ("-", "_")).strip()
                target_path = CASES_DIR / f"{safe_req_id}.json"
                if not target_path.exists():
                    target_path = CASES_DIR / f"{req_id}.json"
                if not target_path.exists():
                    target_path = CASES_DIR / req_id
                if target_path.exists():
                    try:
                        data = json.loads(target_path.read_text(encoding="utf-8"))
                        # Sync active case buffer
                        try:
                            (ROOT / "case_input.json").write_text(json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8")
                        except Exception:
                            pass
                        self._send_json(data)
                        return
                    except Exception as exc:
                        self._send_json({"error": str(exc)}, 500)
                        return
                else:
                    self._send_json({"error": f"Case '{req_id}' not found in cases/"}, 404)
                    return

            case_path = ROOT / "case_input.json"
            if case_path.exists():
                try:
                    data = json.loads(case_path.read_text(encoding="utf-8"))
                    self._send_json(data)
                    return
                except Exception as exc:
                    self._send_json({"error": str(exc)}, 500)
                    return
            all_cases = sorted(CASES_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
            if all_cases:
                try:
                    data = json.loads(all_cases[0].read_text(encoding="utf-8"))
                    self._send_json(data)
                    return
                except Exception:
                    pass
            self._send_json({
                "case_id": "CASE-2026-0824",
                "incident": "",
                "incident_date": datetime.now().strftime("%Y-%m-%d"),
                "incident_timeframe": "20:30 – 22:00",
                "statements": []
            })

        elif path == "/api/status":
            with _pipeline_lock:
                self._send_json(_pipeline_status)

        elif path.startswith("/output/"):
            fname = path.split("/output/", 1)[1]
            fpath = ROOT / "output" / fname
            ct = "text/html; charset=utf-8" if fname.endswith(".html") else "application/json"
            self._send_file(fpath, ct)

        else:
            self.send_error(404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length else b""

        if path == "/api/save":
            try:
                data = json.loads(body.decode("utf-8"))
                raw_id = data.get("case_id", "").strip() or "CASE-2026-0824"
                safe_id = "".join(c for c in raw_id if c.isalnum() or c in ("-", "_")).strip()
                if not safe_id:
                    safe_id = "CASE-" + datetime.now().strftime("%Y%m%d-%H%M%S")
                data["case_id"] = safe_id

                # 1. Save individual JSON inside cases/ folder
                case_file = CASES_DIR / f"{safe_id}.json"
                with open(case_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)

                # 2. Mirror into case_input.json for active pipeline execution
                with open(ROOT / "case_input.json", "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)

                self._send_json({
                    "ok": True,
                    "message": f"Case '{safe_id}' saved to cases/ and active buffer.",
                    "case_id": safe_id
                })
            except Exception as exc:
                self._send_json({"ok": False, "message": str(exc)}, 400)

        elif path == "/api/case/delete":
            query = parse_qs(parsed.query)
            del_id = query.get("id", [None])[0]
            if not del_id and body:
                try:
                    bdata = json.loads(body.decode("utf-8"))
                    del_id = bdata.get("id") or bdata.get("case_id")
                except Exception:
                    pass
            if not del_id:
                self._send_json({"ok": False, "message": "Missing case 'id' parameter to delete."}, 400)
                return

            safe_del_id = "".join(c for c in del_id if c.isalnum() or c in ("-", "_")).strip()
            target = CASES_DIR / f"{safe_del_id}.json"
            if not target.exists():
                target = CASES_DIR / f"{del_id}.json"
            if not target.exists():
                target = CASES_DIR / del_id

            if target.exists():
                try:
                    target.unlink()
                    self._send_json({
                        "ok": True,
                        "message": f"Case file {target.name} permanently deleted from disk.",
                        "deleted_id": del_id
                    })
                except Exception as exc:
                    self._send_json({"ok": False, "message": f"Failed to delete case file: {exc}"}, 500)
            else:
                self._send_json({"ok": False, "message": f"Case '{del_id}' file not found in cases/ folder."}, 404)

        elif path == "/api/run":
            query = parse_qs(parsed.query)
            use_mock = query.get("mode", ["live"])[0] == "mock"

            with _pipeline_lock:
                if _pipeline_status["running"]:
                    self._send_json({"ok": False, "message": "Pipeline is already running."}, 409)
                    return
                _pipeline_status["running"] = True
                _pipeline_status["error"] = None
                _pipeline_status["message"] = "Initializing analysis..."

            def run_bg():
                try:
                    case_path = ROOT / "case_input.json"
                    from timeline_generator import generate as gen_timeline

                    if use_mock:
                        with _pipeline_lock:
                            _pipeline_status["message"] = "Running fast mock pipeline..."
                        from mock_pipeline import run_mock_pipeline
                        run_mock_pipeline()
                        result_path = ROOT / "output" / "case_result.json"
                        with open(result_path, encoding="utf-8") as rf:
                            res_data = json.load(rf)
                        gen_timeline(res_data, str(ROOT / "output" / "timeline.html"))
                    else:
                        with _pipeline_lock:
                            _pipeline_status["message"] = "Calling Gemini API & running 6 algorithms..."
                        try:
                            import main
                            res_data = main.run(str(case_path), str(ROOT / "output"))
                        except Exception as gemini_err:
                            print(f"Gemini run error: {gemini_err}. Falling back to offline engine.")
                            with _pipeline_lock:
                                _pipeline_status["message"] = f"Gemini note: {str(gemini_err)[:40]}... running algorithms..."
                            from mock_pipeline import run_mock_pipeline
                            run_mock_pipeline()
                            result_path = ROOT / "output" / "case_result.json"
                            with open(result_path, encoding="utf-8") as rf:
                                res_data = json.load(rf)
                            gen_timeline(res_data, str(ROOT / "output" / "timeline.html"))

                    with _pipeline_lock:
                        _pipeline_status["running"] = False
                        _pipeline_status["last_run"] = datetime.now().isoformat()
                        _pipeline_status["result"] = "success"
                        _pipeline_status["error"] = None
                        _pipeline_status["message"] = "Completed successfully."
                except Exception as exc:
                    err_msg = traceback.format_exc()
                    with _pipeline_lock:
                        _pipeline_status["running"] = False
                        _pipeline_status["error"] = err_msg
                        _pipeline_status["result"] = "error"
                        _pipeline_status["message"] = f"Error: {str(exc)}"

            threading.Thread(target=run_bg, daemon=True).start()
            self._send_json({"ok": True, "message": "Pipeline started."})

        else:
            self.send_error(404)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


# ═══════════════════════════════════════════════════════════════════════════
# The Case Input Frontend HTML
# ═══════════════════════════════════════════════════════════════════════════

_INPUT_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Forensic Case Input & Timeline Studio</title>
<meta name="description" content="Investigation case intake console: calendar date picker, dual clock spin controls, grouped speaker statements, and live-coordinated timeline viewer.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root {
  --bg-primary: #06080f;
  --bg-secondary: #0c1220;
  --bg-card: rgba(14, 22, 40, 0.75);
  --bg-card-hover: rgba(20, 30, 55, 0.85);
  --bg-input: rgba(8, 14, 28, 0.9);
  --border: rgba(255,255,255,0.08);
  --border-hover: rgba(255,255,255,0.18);
  --border-focus: rgba(59,130,246,0.6);
  --text-primary: #e8ecf4;
  --text-secondary: #8b95a8;
  --text-muted: #5a6478;
  --accent-blue: #3b82f6;
  --accent-purple: #8b5cf6;
  --accent-cyan: #06b6d4;
  --green: #10b981;
  --red: #ef4444;
  --amber: #f59e0b;
  --radius: 14px;
  --radius-sm: 8px;
  --shadow: 0 8px 32px rgba(0,0,0,0.4);
}

* { margin:0; padding:0; box-sizing:border-box; }

body {
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
  background: var(--bg-primary);
  color: var(--text-primary);
  line-height: 1.6;
  min-height: 100vh;
  background-image:
    radial-gradient(ellipse 80% 50% at 50% -20%, rgba(59,130,246,0.1), transparent),
    radial-gradient(ellipse 60% 40% at 80% 100%, rgba(139,92,246,0.08), transparent);
}

#app { max-width: 1060px; margin: 0 auto; padding: 28px 24px 110px; }

/* ─── Top Header ─── */
.page-header {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 24px 32px;
  margin-bottom: 24px;
  backdrop-filter: blur(20px);
  position: relative;
  overflow: hidden;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
}
.page-header::before {
  content: '';
  position: absolute; top: 0; left: 0; right: 0; height: 3px;
  background: linear-gradient(90deg, var(--accent-blue), var(--accent-purple), var(--accent-cyan));
}
.header-title-group h1 {
  font-size: 22px; font-weight: 800;
  background: linear-gradient(135deg, #fff 30%, var(--accent-blue));
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  display: flex; align-items: center; gap: 10px;
}
.header-title-group .subtitle {
  font-size: 13px; color: var(--text-muted); margin-top: 2px;
}
.header-actions {
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
}

/* ─── Buttons ─── */
.btn {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 9px 18px; border-radius: 9px;
  font-size: 13px; font-weight: 600;
  cursor: pointer; border: none;
  transition: all 0.2s;
  font-family: inherit;
  user-select: none;
}
.btn-primary {
  background: linear-gradient(135deg, var(--accent-blue), var(--accent-purple));
  color: #fff;
  box-shadow: 0 2px 12px rgba(59,130,246,0.3);
}
.btn-primary:hover { box-shadow: 0 4px 20px rgba(59,130,246,0.5); transform: translateY(-1px); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
.btn-secondary {
  background: rgba(255,255,255,0.05);
  color: var(--text-primary);
  border: 1px solid var(--border);
}
.btn-secondary:hover { border-color: var(--border-hover); background: rgba(255,255,255,0.09); transform: translateY(-1px); }
.btn-green {
  background: linear-gradient(135deg, var(--green), #059669);
  color: #fff;
  box-shadow: 0 2px 12px rgba(16,185,129,0.3);
}
.btn-green:hover { box-shadow: 0 4px 20px rgba(16,185,129,0.5); transform: translateY(-1px); }
.btn-green:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
.btn-amber {
  background: rgba(245,158,11,0.12);
  color: var(--amber);
  border: 1px solid rgba(245,158,11,0.25);
}
.btn-amber:hover { background: rgba(245,158,11,0.22); }
.btn-red {
  background: rgba(239,68,68,0.12);
  color: var(--red);
  border: 1px solid rgba(239,68,68,0.25);
}
.btn-red:hover { background: rgba(239,68,68,0.22); }
.btn-sm { padding: 6px 13px; font-size: 12px; border-radius: 7px; }
.btn-icon { width: 30px; height: 30px; padding: 0; display: flex; align-items: center; justify-content: center; border-radius: 7px; }

/* ─── Sync Status Badge ─── */
.sync-badge {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 5px 12px; border-radius: 20px;
  font-size: 11px; font-weight: 600;
  background: rgba(16,185,129,0.1);
  color: #10b981;
  border: 1px solid rgba(16,185,129,0.25);
  font-family: 'JetBrains Mono', monospace;
}
.sync-badge .dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: #10b981; box-shadow: 0 0 8px #10b981;
}

/* ─── Form Section Cards ─── */
.form-section {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 24px 28px;
  margin-bottom: 22px;
  backdrop-filter: blur(20px);
}
.form-section-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 20px;
}
.form-section-title {
  font-size: 13px; font-weight: 700; color: var(--text-muted);
  text-transform: uppercase; letter-spacing: 1px;
  display: flex; align-items: center; gap: 8px;
}
.form-row {
  display: grid; grid-template-columns: 1fr 1fr; gap: 16px;
  margin-bottom: 16px;
}
.form-row.full { grid-template-columns: 1fr; }
.form-group { display: flex; flex-direction: column; gap: 6px; position: relative; }
.form-label {
  font-size: 11px; font-weight: 600; color: var(--text-secondary);
  text-transform: uppercase; letter-spacing: 0.5px;
  display: flex; align-items: center; justify-content: space-between;
}
.form-input, .form-select {
  background: var(--bg-input);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 10px 14px;
  font-size: 13.5px;
  color: var(--text-primary);
  font-family: inherit;
  transition: all 0.2s;
  outline: none;
  width: 100%;
}
.form-input:focus, .form-select:focus {
  border-color: var(--border-focus);
  box-shadow: 0 0 0 3px rgba(59,130,246,0.15);
}
.form-input::placeholder { color: var(--text-muted); }

/* ─── Interactive Calendar Picker Popup ─── */
.date-input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}
.date-input-wrapper .form-input {
  padding-right: 42px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
}
.date-cal-btn {
  position: absolute; right: 8px;
  background: transparent; border: none;
  color: var(--accent-blue);
  cursor: pointer; padding: 6px;
  font-size: 16px; border-radius: 6px;
  display: flex; align-items: center; justify-content: center;
  transition: background 0.15s;
}
.date-cal-btn:hover { background: rgba(59,130,246,0.15); }

.calendar-popup {
  position: absolute; top: calc(100% + 6px); left: 0;
  width: 290px;
  background: #0d1527;
  border: 1px solid rgba(59,130,246,0.3);
  border-radius: 12px;
  padding: 14px;
  box-shadow: 0 16px 40px rgba(0,0,0,0.6);
  z-index: 1000;
  display: none;
  backdrop-filter: blur(25px);
  animation: fadeIn 0.15s ease;
}
.calendar-popup.open { display: block; }
.cal-nav {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 12px;
}
.cal-nav button {
  background: rgba(255,255,255,0.06); border: 1px solid var(--border);
  color: var(--text-primary); width: 26px; height: 26px;
  border-radius: 6px; cursor: pointer; font-size: 11px;
  display: flex; align-items: center; justify-content: center;
  transition: background 0.15s;
}
.cal-nav button:hover { background: rgba(59,130,246,0.2); border-color: var(--accent-blue); }
.cal-title {
  font-size: 13px; font-weight: 700; color: #fff;
  font-family: 'Inter', sans-serif;
}
.cal-weekdays {
  display: grid; grid-template-columns: repeat(7, 1fr);
  text-align: center; font-size: 10px; font-weight: 600;
  color: var(--text-muted); margin-bottom: 6px;
}
.cal-days {
  display: grid; grid-template-columns: repeat(7, 1fr); gap: 2px;
}
.cal-day {
  aspect-ratio: 1; display: flex; align-items: center; justify-content: center;
  font-size: 12px; border-radius: 6px; cursor: pointer;
  color: var(--text-primary); transition: all 0.15s;
  font-family: 'JetBrains Mono', monospace;
}
.cal-day:hover { background: rgba(59,130,246,0.25); }
.cal-day.other-month { color: var(--text-muted); opacity: 0.35; }
.cal-day.today { border: 1px solid var(--accent-cyan); color: var(--accent-cyan); font-weight: 700; }
.cal-day.selected {
  background: linear-gradient(135deg, var(--accent-blue), var(--accent-purple));
  color: #fff; font-weight: 700; box-shadow: 0 0 10px rgba(59,130,246,0.5);
}
.cal-footer {
  display: flex; justify-content: space-between; margin-top: 10px;
  padding-top: 8px; border-top: 1px solid var(--border);
}
.cal-quick-btn {
  background: none; border: none; font-size: 11px; font-weight: 600;
  color: var(--accent-blue); cursor: pointer; padding: 2px 6px; border-radius: 4px;
}
.cal-quick-btn:hover { text-decoration: underline; }

/* ─── Dual Clock Controls (Start & End) ─── */
.dual-clock-container {
  display: grid; grid-template-columns: 1fr auto 1fr; gap: 16px;
  align-items: center;
  background: rgba(8, 14, 28, 0.6);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 16px 20px;
}
.clock-card {
  display: flex; flex-direction: column; align-items: center; gap: 6px;
}
.clock-card-title {
  font-size: 10.5px; font-weight: 700; color: var(--text-muted);
  text-transform: uppercase; letter-spacing: 0.8px;
}
.clock-widget {
  display: flex; align-items: center; gap: 8px;
}
.clock-col {
  display: flex; flex-direction: column; align-items: center; gap: 3px;
}
.clock-btn {
  width: 38px; height: 24px;
  background: rgba(255,255,255,0.06);
  border: 1px solid var(--border);
  border-radius: 5px;
  color: var(--text-secondary);
  font-size: 11px; font-weight: bold;
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: all 0.15s;
  user-select: none;
}
.clock-btn:hover {
  background: rgba(59,130,246,0.2);
  border-color: var(--accent-blue);
  color: #fff;
  transform: scale(1.05);
}
.clock-btn:active { transform: scale(0.95); }
.clock-display {
  font-family: 'JetBrains Mono', monospace;
  font-size: 22px; font-weight: 700;
  color: #fff;
  width: 44px; height: 38px;
  background: rgba(0,0,0,0.3);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 6px;
  display: flex; align-items: center; justify-content: center;
  box-shadow: inset 0 2px 4px rgba(0,0,0,0.5);
}
.clock-sep {
  font-size: 24px; font-weight: 700; color: var(--accent-cyan);
  padding: 0 2px; align-self: center;
}
.clock-quick {
  display: flex; gap: 4px; margin-top: 2px;
}
.clock-quick-btn {
  background: rgba(255,255,255,0.04); border: 1px solid var(--border);
  color: var(--text-muted); font-size: 9px; padding: 2px 6px;
  border-radius: 4px; cursor: pointer; font-family: 'JetBrains Mono', monospace;
  transition: all 0.15s;
}
.clock-quick-btn:hover { background: rgba(59,130,246,0.15); color: var(--accent-blue); border-color: var(--accent-blue); }
.clock-divider {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  color: var(--text-muted); font-size: 18px; padding: 0 4px;
}
.clock-duration {
  font-size: 10px; color: var(--accent-cyan); font-family: 'JetBrains Mono', monospace;
  margin-top: 4px; font-weight: 600;
}

/* ─── Speaker Cards (Grouped by Speaker) ─── */
.speaker-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  margin-bottom: 20px;
  overflow: hidden;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.speaker-card:hover { border-color: var(--border-hover); }
.speaker-header {
  padding: 18px 24px;
  background: rgba(255,255,255,0.02);
  border-bottom: 1px solid var(--border);
  display: flex; justify-content: space-between; align-items: center;
  flex-wrap: wrap; gap: 14px;
}
.speaker-meta {
  display: flex; align-items: center; gap: 12px; flex: 1; min-width: 280px;
}
.speaker-avatar {
  width: 38px; height: 38px; border-radius: 10px;
  background: linear-gradient(135deg, rgba(59,130,246,0.2), rgba(139,92,246,0.2));
  border: 1px solid rgba(59,130,246,0.3);
  display: flex; align-items: center; justify-content: center;
  font-size: 18px; color: var(--accent-cyan); flex-shrink: 0;
}
.speaker-id-badge {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px; font-weight: 600;
  color: var(--accent-blue);
  background: rgba(59,130,246,0.1);
  border: 1px solid rgba(59,130,246,0.2);
  padding: 3px 8px; border-radius: 6px;
}
.speaker-name-input {
  font-size: 15px; font-weight: 700; color: #fff;
  background: transparent; border: none;
  border-bottom: 1px dashed rgba(255,255,255,0.2);
  padding: 4px 6px; outline: none; transition: border-color 0.2s;
  min-width: 140px;
}
.speaker-name-input:focus {
  border-bottom: 1px solid var(--accent-blue);
  background: rgba(255,255,255,0.03);
}
.speaker-role-select {
  font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;
  padding: 4px 10px; border-radius: 20px; outline: none; cursor: pointer;
  border: 1px solid transparent; transition: all 0.2s;
}
.speaker-role-select.victim { background: rgba(239,68,68,0.15); color: #f87171; border-color: rgba(239,68,68,0.3); }
.speaker-role-select.witness { background: rgba(59,130,246,0.15); color: #60a5fa; border-color: rgba(59,130,246,0.3); }
.speaker-role-select.suspect { background: rgba(245,158,11,0.15); color: #fbbf24; border-color: rgba(245,158,11,0.3); }
.speaker-role-select.informant { background: rgba(139,92,246,0.15); color: #c084fc; border-color: rgba(139,92,246,0.3); }
.speaker-role-select.officer { background: rgba(16,185,129,0.15); color: #34d399; border-color: rgba(16,185,129,0.3); }
.speaker-role-select option { background: #0c1220; color: #e8ecf4; }

.speaker-actions {
  display: flex; align-items: center; gap: 10px;
}
.stmt-count-pill {
  font-size: 11px; color: var(--text-muted);
  font-family: 'JetBrains Mono', monospace;
}

/* ─── Statement Items inside Speaker Card ─── */
.statements-wrapper {
  padding: 20px 24px;
}
.statement-item {
  background: rgba(8, 14, 28, 0.7);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 16px 20px;
  margin-bottom: 14px;
  transition: border-color 0.2s;
}
.statement-item:hover { border-color: rgba(255,255,255,0.14); }
.statement-meta-row {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 12px; flex-wrap: wrap; gap: 8px;
}
.stmt-id-tag {
  font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 600;
  color: var(--accent-cyan);
}
.recorded-auto-pill {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 3px 10px; border-radius: 20px;
  background: rgba(16,185,129,0.08);
  border: 1px solid rgba(16,185,129,0.2);
  color: #34d399; font-size: 11px;
  font-family: 'JetBrains Mono', monospace;
}
.recorded-auto-pill .clock-icon { font-size: 12px; }
.recorded-note {
  font-size: 9.5px; color: var(--text-muted);
}
.restamp-btn {
  background: transparent; border: none; color: var(--text-muted);
  cursor: pointer; font-size: 11px; padding: 2px 5px; border-radius: 4px;
  transition: all 0.15s;
}
.restamp-btn:hover { color: var(--accent-blue); background: rgba(59,130,246,0.1); }

.statement-textarea {
  width: 100%;
  background: rgba(4, 8, 18, 0.75);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px 14px;
  color: var(--text-primary);
  font-family: inherit;
  font-size: 13.5px;
  line-height: 1.65;
  resize: vertical;
  min-height: 110px;
  outline: none;
  transition: border-color 0.2s;
}
.statement-textarea:focus {
  border-color: var(--border-focus);
  box-shadow: 0 0 0 2px rgba(59,130,246,0.12);
}
.statement-footer-counts {
  display: flex; justify-content: flex-end; gap: 14px;
  font-size: 10.5px; color: var(--text-muted);
  font-family: 'JetBrains Mono', monospace;
  margin-top: 6px;
}

.add-stmt-under-speaker-btn {
  width: 100%;
  padding: 9px;
  background: rgba(255,255,255,0.03);
  border: 1px dashed var(--border);
  border-radius: 8px;
  color: var(--accent-blue);
  font-size: 12px; font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  display: flex; align-items: center; justify-content: center; gap: 6px;
  font-family: inherit;
}
.add-stmt-under-speaker-btn:hover {
  background: rgba(59,130,246,0.08);
  border-color: var(--accent-blue);
}

/* ─── Sticky Action Bar ─── */
.action-bar {
  position: fixed; bottom: 0; left: 0; right: 0;
  background: rgba(6, 8, 15, 0.95);
  border-top: 1px solid var(--border);
  backdrop-filter: blur(25px);
  padding: 14px 28px;
  display: flex; justify-content: space-between; align-items: center;
  z-index: 500;
  box-shadow: 0 -8px 30px rgba(0,0,0,0.5);
}
.action-bar-left {
  display: flex; align-items: center; gap: 12px;
}
.action-bar-center {
  display: flex; align-items: center; gap: 10px;
}
.action-bar-right {
  display: flex; align-items: center; gap: 12px;
}

.pipeline-status-text {
  font-size: 12px; font-family: 'JetBrains Mono', monospace;
  color: var(--text-muted);
}
.pipeline-status-text.running { color: var(--amber); }
.pipeline-status-text.done { color: var(--green); }
.pipeline-status-text.error { color: var(--red); }

@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.35; } }
.pulsing { animation: pulse 1.4s infinite; }

/* ─── Toast Alerts ─── */
.toast {
  position: fixed; top: 24px; right: 24px;
  padding: 14px 22px; border-radius: 10px;
  font-size: 13px; font-weight: 600;
  z-index: 2000; display: none;
  box-shadow: 0 10px 35px rgba(0,0,0,0.6);
  backdrop-filter: blur(20px);
  animation: slideIn 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  max-width: 450px;
}
.toast.success { background: rgba(16,185,129,0.95); color: #fff; border: 1px solid #10b981; }
.toast.error { background: rgba(239,68,68,0.95); color: #fff; border: 1px solid #ef4444; }
.toast.info { background: rgba(59,130,246,0.95); color: #fff; border: 1px solid #3b82f6; }
.toast.visible { display: flex; align-items: center; gap: 10px; }

@keyframes fadeIn { from { opacity: 0; transform: translateY(-6px); } to { opacity: 1; transform: translateY(0); } }
@keyframes slideIn { from { opacity: 0; transform: translateX(50px); } to { opacity: 1; transform: translateX(0); } }

/* ─── Case Inventory Side Panel Drawer & Overlay ─── */
.sidebar-overlay {
  position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
  background: rgba(4, 7, 15, 0.7);
  backdrop-filter: blur(5px);
  z-index: 1200;
  opacity: 0; pointer-events: none;
  transition: opacity 0.25s ease;
}
.sidebar-overlay.open {
  opacity: 1; pointer-events: auto;
}
.case-sidebar {
  position: fixed; top: 0; left: 0; bottom: 0;
  width: 400px; max-width: 90vw;
  background: #090e1c;
  border-right: 1px solid var(--border);
  box-shadow: 12px 0 45px rgba(0,0,0,0.75);
  z-index: 1300;
  transform: translateX(-100%);
  transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  display: flex; flex-direction: column;
}
.case-sidebar.open {
  transform: translateX(0);
}
.sidebar-header {
  padding: 22px 24px;
  border-bottom: 1px solid var(--border);
  display: flex; justify-content: space-between; align-items: center;
  background: rgba(255,255,255,0.02);
  position: relative;
}
.sidebar-header::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
  background: linear-gradient(90deg, var(--accent-blue), var(--accent-cyan));
}
.sidebar-title-group {
  display: flex; align-items: center; gap: 12px;
}
.sidebar-icon {
  font-size: 24px;
}
.sidebar-heading {
  font-size: 16px; font-weight: 800; color: #fff;
  letter-spacing: -0.3px;
}
.sidebar-subheading {
  font-size: 11px; color: var(--text-muted); font-family: 'JetBrains Mono', monospace;
  margin-top: 1px;
}
.sidebar-close-btn {
  width: 32px; height: 32px; border-radius: 8px;
  background: rgba(255,255,255,0.05); border: 1px solid var(--border);
  color: var(--text-secondary); cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  font-size: 14px; transition: all 0.15s;
}
.sidebar-close-btn:hover {
  background: rgba(239,68,68,0.2); border-color: var(--red); color: #fff;
}
.sidebar-controls {
  padding: 16px 20px;
  display: flex; flex-direction: column; gap: 12px;
  border-bottom: 1px solid var(--border);
  background: rgba(0,0,0,0.2);
}
.btn-new-case {
  width: 100%; justify-content: center; padding: 11px 16px;
  font-size: 13.5px; font-weight: 700;
  background: linear-gradient(135deg, var(--accent-blue), var(--accent-purple));
}
.search-box-wrapper {
  position: relative; display: flex; align-items: center;
}
.search-icon {
  position: absolute; left: 12px; font-size: 13px; color: var(--text-muted);
  pointer-events: none;
}
.search-input {
  width: 100%;
  background: var(--bg-input);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 9px 34px 9px 34px;
  font-size: 12.5px;
  color: var(--text-primary);
  outline: none; transition: all 0.2s;
  font-family: inherit;
}
.search-input:focus {
  border-color: var(--border-focus);
  box-shadow: 0 0 0 2px rgba(59,130,246,0.15);
}
.search-clear-btn {
  position: absolute; right: 10px;
  background: none; border: none; color: var(--text-muted);
  font-size: 11px; cursor: pointer; padding: 3px; display: none;
}
.search-clear-btn:hover { color: #fff; }
.sidebar-inventory-list {
  flex: 1; overflow-y: auto; padding: 16px;
  display: flex; flex-direction: column; gap: 12px;
}
.inventory-case-card {
  background: rgba(14, 22, 40, 0.7);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 15px;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
  overflow: hidden;
}
.inventory-case-card:hover {
  background: rgba(20, 32, 58, 0.9);
  border-color: var(--border-hover);
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(0,0,0,0.4);
}
.inventory-case-card.active-case {
  border-color: var(--accent-cyan);
  background: rgba(6, 182, 212, 0.09);
  box-shadow: inset 3px 0 0 var(--accent-cyan), 0 4px 18px rgba(6,182,212,0.18);
}
.card-header-row {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 8px;
}
.card-case-id {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11.5px; font-weight: 700;
  color: var(--accent-blue);
  background: rgba(59,130,246,0.12);
  border: 1px solid rgba(59,130,246,0.25);
  padding: 2px 8px; border-radius: 6px;
}
.card-active-pill {
  font-size: 9.5px; font-weight: 700; letter-spacing: 0.5px;
  text-transform: uppercase;
  background: rgba(6, 182, 212, 0.2);
  color: var(--accent-cyan);
  border: 1px solid rgba(6, 182, 212, 0.4);
  padding: 2px 7px; border-radius: 12px;
  display: inline-flex; align-items: center; gap: 5px;
}
.card-active-pill .pulse-dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--accent-cyan); box-shadow: 0 0 6px var(--accent-cyan);
}
.card-incident-title {
  font-size: 13.5px; font-weight: 600; color: #fff;
  margin-bottom: 8px; line-height: 1.45;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
  overflow: hidden;
}
.card-meta-row {
  display: flex; align-items: center; justify-content: space-between;
  font-size: 11px; color: var(--text-muted);
  font-family: 'JetBrains Mono', monospace;
  margin-top: 6px; padding-top: 8px;
  border-top: 1px solid rgba(255,255,255,0.05);
}
.card-meta-item { display: flex; align-items: center; gap: 4px; }
.card-actions-row {
  display: flex; justify-content: space-between; align-items: center;
  margin-top: 10px; padding-top: 8px;
  border-top: 1px solid rgba(255,255,255,0.05);
}
.card-open-btn {
  background: rgba(59,130,246,0.12); color: var(--accent-blue);
  border: 1px solid rgba(59,130,246,0.25);
  border-radius: 6px; padding: 4px 11px; font-size: 11px; font-weight: 600;
  cursor: pointer; transition: all 0.15s; font-family: inherit;
}
.card-open-btn:hover {
  background: var(--accent-blue); color: #fff;
}
.card-delete-btn {
  background: rgba(239,68,68,0.1); color: var(--red);
  border: 1px solid rgba(239,68,68,0.2);
  border-radius: 6px; padding: 4px 9px; font-size: 11px; font-weight: 600;
  cursor: pointer; transition: all 0.15s;
  display: inline-flex; align-items: center; gap: 4px; font-family: inherit;
}
.card-delete-btn:hover {
  background: var(--red); color: #fff;
}
.inventory-count-pill {
  background: rgba(59,130,246,0.2); color: var(--accent-blue);
  border: 1px solid rgba(59,130,246,0.4);
  padding: 1px 7px; border-radius: 10px;
  font-size: 11px; font-weight: 700;
  font-family: 'JetBrains Mono', monospace;
  margin-left: 4px;
}
.inventory-empty-state {
  text-align: center; padding: 40px 16px; color: var(--text-muted); font-size: 13px;
}

/* ─── Scrollbar ─── */
::-webkit-scrollbar { width: 7px; height: 7px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.2); }
</style>
</head>
<body>

<!-- Case Inventory Side Panel Overlay -->
<div id="sidebar-overlay" class="sidebar-overlay" onclick="toggleCaseSidebar(false)"></div>

<!-- Case Inventory Side Panel Drawer -->
<aside id="case-sidebar" class="case-sidebar" aria-label="Case Inventory">
  <div class="sidebar-header">
    <div class="sidebar-title-group">
      <span class="sidebar-icon">🗂</span>
      <div>
        <div class="sidebar-heading">Case Inventory</div>
        <div class="sidebar-subheading" id="inventory-stats">Loading cases...</div>
      </div>
    </div>
    <button type="button" class="sidebar-close-btn" onclick="toggleCaseSidebar(false)" title="Close Sidebar">✕</button>
  </div>

  <div class="sidebar-controls">
    <button type="button" class="btn btn-primary btn-new-case" onclick="createNewCase()">
      <span>+</span> New Case Intake
    </button>
    <div class="search-box-wrapper">
      <span class="search-icon">🔍</span>
      <input type="text" id="case-search-input" class="search-input" placeholder="Search case ID, title, speaker..." oninput="filterCaseInventory(this.value)">
      <button type="button" class="search-clear-btn" id="search-clear-btn" onclick="clearCaseSearch()">✕</button>
    </div>
  </div>

  <div class="sidebar-inventory-list" id="case-inventory-list">
    <!-- Dynamically loaded case cards -->
  </div>
</aside>

<div id="app">

  <!-- Header -->
  <div class="page-header">
    <div class="header-title-group">
      <h1>🔍 Case Intake & Intelligence Studio</h1>
      <div class="subtitle">Multi-statement forensic ingestion with synchronized graph timeline & analytical modules</div>
    </div>
    <div class="header-actions">
      <button class="btn btn-secondary btn-sm" onclick="toggleCaseSidebar()" id="btn-inventory-toggle" title="Open Case Inventory side panel">
        <span>🗂</span> Case Inventory <span class="inventory-count-pill" id="inventory-count-badge">0</span>
      </button>
      <div class="sync-badge" id="sync-status"><span class="dot"></span> Tab Coordinated</div>
      <button class="btn btn-secondary btn-sm" onclick="openTimeline()" title="Open Interactive Timeline in a new Chrome tab">📊 Open Timeline</button>
      <button class="btn btn-secondary btn-sm" onclick="openReport()" title="Open Analytical Report in a new Chrome tab">📋 View Report</button>
    </div>
  </div>

  <!-- Case Information Section -->
  <div class="form-section">
    <div class="form-section-header">
      <div class="form-section-title">📁 Case Parameters</div>
      <div style="font-size:11px;color:var(--text-muted);font-family:'JetBrains Mono',monospace;">Matches case_input.json schema</div>
    </div>

    <div class="form-row">
      <!-- Case ID -->
      <div class="form-group">
        <label class="form-label" for="case-id">Case Identifier</label>
        <input type="text" class="form-input" id="case-id" placeholder="CASE-2026-0824" style="font-family:'JetBrains Mono',monospace;">
      </div>

      <!-- Incident Date with Calendar -->
      <div class="form-group">
        <label class="form-label" for="incident-date">
          <span>Incident Date</span>
          <span style="font-size:10px;color:var(--text-muted);text-transform:none;">Interactive Calendar</span>
        </label>
        <div class="date-input-wrapper">
          <input type="text" class="form-input" id="incident-date" placeholder="YYYY-MM-DD" readonly onclick="toggleCalendar(event)">
          <button type="button" class="date-cal-btn" onclick="toggleCalendar(event)" title="Open Monthly Calendar">📅</button>
          
          <!-- Small Monthly Calendar Dropdown -->
          <div class="calendar-popup" id="calendar-popup" onclick="event.stopPropagation()">
            <div class="cal-nav">
              <button type="button" onclick="calPrevMonth()">◀</button>
              <div class="cal-title" id="cal-month-year">August 2026</div>
              <button type="button" onclick="calNextMonth()">▶</button>
            </div>
            <div class="cal-weekdays">
              <div>Su</div><div>Mo</div><div>Tu</div><div>We</div><div>Th</div><div>Fr</div><div>Sa</div>
            </div>
            <div class="cal-days" id="cal-days-grid"></div>
            <div class="cal-footer">
              <button type="button" class="cal-quick-btn" onclick="calSelectToday()">Today</button>
              <button type="button" class="cal-quick-btn" onclick="calClearDate()" style="color:var(--text-muted)">Clear</button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Case Name / Incident Description -->
    <div class="form-row full">
      <div class="form-group">
        <label class="form-label" for="incident-desc">Incident Description / Case Name</label>
        <input type="text" class="form-input" id="incident-desc" placeholder="e.g. Armed Robbery at Mehta Jewellers, Karol Bagh, New Delhi">
      </div>
    </div>

    <!-- Incident Timeframe Dual Clock -->
    <div class="form-row full">
      <div class="form-group">
        <label class="form-label">
          <span>Incident Timeframe (Start & End Times)</span>
          <span id="timeframe-preview-pill" style="font-size:11px;color:var(--accent-cyan);font-family:'JetBrains Mono',monospace;">20:30 – 22:00</span>
        </label>
        
        <div class="dual-clock-container">
          <!-- Start Time Clock -->
          <div class="clock-card">
            <div class="clock-card-title">🕒 Start Time</div>
            <div class="clock-widget">
              <div class="clock-col">
                <button type="button" class="clock-btn" onclick="spinHour('start', 1)">+</button>
                <div class="clock-display" id="clock-start-h">20</div>
                <button type="button" class="clock-btn" onclick="spinHour('start', -1)">-</button>
              </div>
              <div class="clock-sep">:</div>
              <div class="clock-col">
                <button type="button" class="clock-btn" onclick="spinMin('start', 5)">+</button>
                <div class="clock-display" id="clock-start-m">30</div>
                <button type="button" class="clock-btn" onclick="spinMin('start', -5)">-</button>
              </div>
            </div>
            <div class="clock-quick">
              <button type="button" class="clock-quick-btn" onclick="spinHour('start', 1)">+1h</button>
              <button type="button" class="clock-quick-btn" onclick="spinHour('start', -1)">-1h</button>
              <button type="button" class="clock-quick-btn" onclick="spinMin('start', 15)">+15m</button>
              <button type="button" class="clock-quick-btn" onclick="spinMin('start', -15)">-15m</button>
            </div>
          </div>

          <!-- Divider -->
          <div class="clock-divider">
            <div>⟶</div>
            <div class="clock-duration" id="clock-duration-text">1h 30m</div>
          </div>

          <!-- End Time Clock -->
          <div class="clock-card">
            <div class="clock-card-title">🕒 End Time</div>
            <div class="clock-widget">
              <div class="clock-col">
                <button type="button" class="clock-btn" onclick="spinHour('end', 1)">+</button>
                <div class="clock-display" id="clock-end-h">22</div>
                <button type="button" class="clock-btn" onclick="spinHour('end', -1)">-</button>
              </div>
              <div class="clock-sep">:</div>
              <div class="clock-col">
                <button type="button" class="clock-btn" onclick="spinMin('end', 5)">+</button>
                <div class="clock-display" id="clock-end-m">00</div>
                <button type="button" class="clock-btn" onclick="spinMin('end', -5)">-</button>
              </div>
            </div>
            <div class="clock-quick">
              <button type="button" class="clock-quick-btn" onclick="spinHour('end', 1)">+1h</button>
              <button type="button" class="clock-quick-btn" onclick="spinHour('end', -1)">-1h</button>
              <button type="button" class="clock-quick-btn" onclick="spinMin('end', 15)">+15m</button>
              <button type="button" class="clock-quick-btn" onclick="spinMin('end', -15)">-15m</button>
            </div>
          </div>
        </div>
      </div>
    </div>

  </div>

  <!-- Statements Section (Grouped by Speaker ID) -->
  <div class="form-section">
    <div class="form-section-header">
      <div>
        <div class="form-section-title">🗣 Case Statements (Grouped by Speaker)</div>
        <div style="font-size:11.5px;color:var(--text-muted);margin-top:2px;">
          Speakers hold multiple statements recorded at distinct dates & times. Auto-stamped at moment of addition.
        </div>
      </div>
      <button class="btn btn-primary btn-sm" onclick="addNewSpeaker()">+ Add New Speaker</button>
    </div>

    <!-- Container for Grouped Speaker Cards -->
    <div id="speakers-container"></div>
  </div>

</div>

<!-- Sticky Action Bar -->
<div class="action-bar">
  <div class="action-bar-left">
    <button class="btn btn-primary" onclick="saveCase()" id="btn-save">💾 Save Case</button>
    <button class="btn btn-green" onclick="runPipeline('live')" id="btn-run">▶ Run Pipeline (Gemini AI)</button>
    <button class="btn btn-amber btn-sm" onclick="runPipeline('mock')" id="btn-run-mock" title="Fast offline run with algorithms">⚡ Fast Offline Run</button>
  </div>
  <div class="action-bar-center">
    <span class="pipeline-status-text" id="pipeline-status-text">● Ready</span>
  </div>
  <div class="action-bar-right">
    <button class="btn btn-secondary" onclick="openTimeline()">📊 Open Timeline (New Tab)</button>
  </div>
</div>

<!-- Floating Toast -->
<div class="toast" id="toast"></div>

<script>
// ═══════════════════════════════════════════════════════════════════════════
// State Management
// ═══════════════════════════════════════════════════════════════════════════

// Array of Speakers: each speaker has speaker_id, speaker_name, speaker_role, and statements []
let speakers = [];
let speakerCounter = 0;
let statementCounter = 0;

// Timeframe state
let startH = 20, startM = 30;
let endH = 22, endM = 0;

// Calendar picker state
let calCurrentYear = 2026;
let calCurrentMonth = 7; // 0-indexed (7 = August)
let calSelectedDate = '2026-08-23';

// Cross-tab broadcast channel
const syncChannel = typeof BroadcastChannel !== 'undefined' ? new BroadcastChannel('investigation_channel') : null;

// ═══════════════════════════════════════════════════════════════════════════
// Dual Clock Spinners
// ═══════════════════════════════════════════════════════════════════════════

function spinHour(which, delta) {
  if (which === 'start') {
    startH = (startH + delta + 24) % 24;
  } else {
    endH = (endH + delta + 24) % 24;
  }
  updateClockDisplay();
}

function spinMin(which, delta) {
  if (which === 'start') {
    startM = (startM + delta + 60) % 60;
  } else {
    endM = (endM + delta + 60) % 60;
  }
  updateClockDisplay();
}

function updateClockDisplay() {
  document.getElementById('clock-start-h').textContent = String(startH).padStart(2, '0');
  document.getElementById('clock-start-m').textContent = String(startM).padStart(2, '0');
  document.getElementById('clock-end-h').textContent = String(endH).padStart(2, '0');
  document.getElementById('clock-end-m').textContent = String(endM).padStart(2, '0');

  const tf = `${String(startH).padStart(2, '0')}:${String(startM).padStart(2, '0')} – ${String(endH).padStart(2, '0')}:${String(endM).padStart(2, '0')}`;
  document.getElementById('timeframe-preview-pill').textContent = tf;

  // Duration
  let diffMin = (endH * 60 + endM) - (startH * 60 + startM);
  if (diffMin < 0) diffMin += 24 * 60;
  const dh = Math.floor(diffMin / 60);
  const dm = diffMin % 60;
  document.getElementById('clock-duration-text').textContent = `${dh}h ${dm}m`;
}

// ═══════════════════════════════════════════════════════════════════════════
// Monthly Calendar Picker
// ═══════════════════════════════════════════════════════════════════════════

const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December"
];

function toggleCalendar(e) {
  e.stopPropagation();
  const popup = document.getElementById('calendar-popup');
  popup.classList.toggle('open');
  if (popup.classList.contains('open')) {
    if (calSelectedDate) {
      const parts = calSelectedDate.split('-');
      if (parts.length === 3) {
        calCurrentYear = parseInt(parts[0], 10);
        calCurrentMonth = parseInt(parts[1], 10) - 1;
      }
    }
    renderCalendar();
  }
}

document.addEventListener('click', (e) => {
  const popup = document.getElementById('calendar-popup');
  if (popup && popup.classList.contains('open')) {
    popup.classList.remove('open');
  }
});

function calPrevMonth() {
  calCurrentMonth--;
  if (calCurrentMonth < 0) {
    calCurrentMonth = 11;
    calCurrentYear--;
  }
  renderCalendar();
}

function calNextMonth() {
  calCurrentMonth++;
  if (calCurrentMonth > 11) {
    calCurrentMonth = 0;
    calCurrentYear++;
  }
  renderCalendar();
}

function renderCalendar() {
  document.getElementById('cal-month-year').textContent = `${MONTH_NAMES[calCurrentMonth]} ${calCurrentYear}`;
  const grid = document.getElementById('cal-days-grid');
  grid.innerHTML = '';

  const firstDay = new Date(calCurrentYear, calCurrentMonth, 1).getDay(); // 0 = Sun
  const daysInMonth = new Date(calCurrentYear, calCurrentMonth + 1, 0).getDate();
  const prevMonthDays = new Date(calCurrentYear, calCurrentMonth, 0).getDate();

  const todayStr = new Date().toISOString().slice(0, 10);

  // Prev month padding
  for (let i = firstDay - 1; i >= 0; i--) {
    const d = prevMonthDays - i;
    const cell = document.createElement('div');
    cell.className = 'cal-day other-month';
    cell.textContent = d;
    grid.appendChild(cell);
  }

  // Current month days
  for (let d = 1; d <= daysInMonth; d++) {
    const dayStr = `${calCurrentYear}-${String(calCurrentMonth + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
    const cell = document.createElement('div');
    cell.className = 'cal-day';
    cell.textContent = d;

    if (dayStr === todayStr) cell.classList.add('today');
    if (dayStr === calSelectedDate) cell.classList.add('selected');

    cell.onclick = (e) => {
      e.stopPropagation();
      calSelectedDate = dayStr;
      document.getElementById('incident-date').value = dayStr;
      document.getElementById('calendar-popup').classList.remove('open');
    };
    grid.appendChild(cell);
  }
}

function calSelectToday() {
  const now = new Date();
  calCurrentYear = now.getFullYear();
  calCurrentMonth = now.getMonth();
  calSelectedDate = now.toISOString().slice(0, 10);
  document.getElementById('incident-date').value = calSelectedDate;
  document.getElementById('calendar-popup').classList.remove('open');
}

function calClearDate() {
  calSelectedDate = '';
  document.getElementById('incident-date').value = '';
  document.getElementById('calendar-popup').classList.remove('open');
}

// ═══════════════════════════════════════════════════════════════════════════
// Grouped Speakers & Statements Management
// ═══════════════════════════════════════════════════════════════════════════

function formatTimestamp(isoStr) {
  if (!isoStr) return '';
  try {
    const d = new Date(isoStr);
    if (isNaN(d.getTime())) return isoStr;
    const pad = n => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
  } catch(e) {
    return isoStr;
  }
}

function getNowTimestamp() {
  const d = new Date();
  const pad = n => String(n).padStart(2, '0');
  const tzo = -d.getTimezoneOffset();
  const sign = tzo >= 0 ? '+' : '-';
  const tzH = pad(Math.floor(Math.abs(tzo) / 60));
  const tzM = pad(Math.abs(tzo) % 60);
  return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}${sign}${tzH}:${tzM}`;
}

function addNewSpeaker(data) {
  speakerCounter++;
  const spkId = data?.speaker_id || `SPK_${String(speakerCounter).padStart(2, '0')}`;
  
  const speaker = {
    _uid: speakerCounter,
    speaker_id: spkId,
    speaker_name: data?.speaker_name || '',
    speaker_role: data?.speaker_role || 'witness',
    statements: []
  };

  if (data?.statements && data.statements.length) {
    data.statements.forEach(st => {
      statementCounter++;
      speaker.statements.push({
        _uid: statementCounter,
        id: st.id || `STMT_${String(statementCounter).padStart(2, '0')}`,
        recorded_at: st.recorded_at || getNowTimestamp(),
        statement_text: st.statement_text || '',
      });
    });
  } else {
    // Default initial statement, auto-recorded now!
    statementCounter++;
    speaker.statements.push({
      _uid: statementCounter,
      id: `STMT_${String(statementCounter).padStart(2, '0')}`,
      recorded_at: getNowTimestamp(), // Auto-recorded at creation!
      statement_text: '',
    });
  }

  speakers.push(speaker);
  renderSpeakers();
}

function removeSpeaker(spkUid) {
  if (confirm("Are you sure you want to remove this speaker and all associated statements?")) {
    speakers = speakers.filter(s => s._uid !== spkUid);
    renderSpeakers();
  }
}

function addStatementToSpeaker(spkUid) {
  const spk = speakers.find(s => s._uid === spkUid);
  if (!spk) return;

  statementCounter++;
  const nextId = `STMT_${String(statementCounter).padStart(2, '0')}`;
  spk.statements.push({
    _uid: statementCounter,
    id: nextId,
    recorded_at: getNowTimestamp(), // Automatically recorded at creation time!
    statement_text: '',
  });
  renderSpeakers();
  showToast(`Added Statement ${nextId} under ${spk.speaker_name || spk.speaker_id}. Auto-timestamp recorded.`, 'info');
}

function removeStatementFromSpeaker(spkUid, stmtUid) {
  const spk = speakers.find(s => s._uid === spkUid);
  if (!spk) return;
  if (spk.statements.length <= 1) {
    showToast("A speaker must have at least one statement transcript.", 'error');
    return;
  }
  spk.statements = spk.statements.filter(st => st._uid !== stmtUid);
  renderSpeakers();
}

function restampStatement(spkUid, stmtUid) {
  const spk = speakers.find(s => s._uid === spkUid);
  if (!spk) return;
  const stmt = spk.statements.find(st => st._uid === stmtUid);
  if (stmt) {
    stmt.recorded_at = getNowTimestamp();
    renderSpeakers();
    showToast(`Re-stamped ${stmt.id} to current time.`, 'info');
  }
}

function updateSpeakerField(spkUid, field, val) {
  const spk = speakers.find(s => s._uid === spkUid);
  if (spk) {
    spk[field] = val;
    if (field === 'speaker_role') renderSpeakers();
  }
}

function updateStatementField(spkUid, stmtUid, field, val) {
  const spk = speakers.find(s => s._uid === spkUid);
  if (!spk) return;
  const stmt = spk.statements.find(st => st._uid === stmtUid);
  if (stmt) {
    stmt[field] = val;
    if (field === 'statement_text') {
      updateCounts(stmtUid, val);
    }
  }
}

function updateCounts(stmtUid, text) {
  const words = text.trim() ? text.trim().split(/\s+/).length : 0;
  const chars = text.length;
  const el = document.getElementById(`counts-${stmtUid}`);
  if (el) el.textContent = `${words} words · ${chars} characters`;
}

function autoResize(textarea) {
  textarea.style.height = 'auto';
  textarea.style.height = (textarea.scrollHeight + 4) + 'px';
}

function renderSpeakers() {
  const container = document.getElementById('speakers-container');
  if (!speakers.length) {
    container.innerHTML = `
      <div style="text-align:center;padding:48px 20px;color:var(--text-muted);font-size:14px;">
        No speakers yet. Click <strong>+ Add New Speaker</strong> above to add witnesses, victims, or suspects.
      </div>`;
    return;
  }

  container.innerHTML = speakers.map(spk => {
    const roleClass = spk.speaker_role || 'witness';
    const stmtCountText = `${spk.statements.length} ${spk.statements.length === 1 ? 'Statement' : 'Statements'}`;

    const statementsHtml = spk.statements.map(st => {
      const formattedTime = formatTimestamp(st.recorded_at);
      const wordCount = st.statement_text.trim() ? st.statement_text.trim().split(/\s+/).length : 0;
      const charCount = st.statement_text.length;

      return `
        <div class="statement-item" id="stmt-item-${st._uid}">
          <div class="statement-meta-row">
            <div style="display:flex;align-items:center;gap:10px;">
              <span class="stmt-id-tag">${esc(st.id)}</span>
              <div class="recorded-auto-pill" title="Recorded automatically at the moment of addition">
                <span class="clock-icon">🕒</span>
                <span>Auto-recorded: ${esc(formattedTime)}</span>
              </div>
              <button type="button" class="restamp-btn" onclick="restampStatement(${spk._uid}, ${st._uid})" title="Update timestamp to current time">⏱ Now</button>
            </div>
            ${spk.statements.length > 1 ? `
              <button class="btn btn-red btn-icon" onclick="removeStatementFromSpeaker(${spk._uid}, ${st._uid})" title="Remove this statement">✕</button>
            ` : ''}
          </div>
          <div style="margin-bottom:6px;display:flex;justify-content:space-between;align-items:center;">
            <label class="form-label" style="font-size:10px;margin-bottom:0;">Verbatim Statement Transcript</label>
          </div>
          <textarea class="statement-textarea" rows="4"
                    placeholder="Enter verbatim transcript (can be as long as required)..."
                    oninput="updateStatementField(${spk._uid}, ${st._uid}, 'statement_text', this.value); autoResize(this);"
                    onchange="updateStatementField(${spk._uid}, ${st._uid}, 'statement_text', this.value);">${esc(st.statement_text)}</textarea>
          <div class="statement-footer-counts" id="counts-${st._uid}">
            ${wordCount} words · ${charCount} characters
          </div>
        </div>
      `;
    }).join('');

    return `
      <div class="speaker-card" id="speaker-card-${spk._uid}">
        <div class="speaker-header">
          <div class="speaker-meta">
            <div class="speaker-avatar">👤</div>
            <span class="speaker-id-badge">${esc(spk.speaker_id)}</span>
            <input type="text" class="speaker-name-input" value="${esc(spk.speaker_name)}"
                   placeholder="Speaker Name (e.g. Rajesh Mehta)"
                   onchange="updateSpeakerField(${spk._uid}, 'speaker_name', this.value)">
            <select class="speaker-role-select ${roleClass}"
                    onchange="updateSpeakerField(${spk._uid}, 'speaker_role', this.value)">
              <option value="victim" ${spk.speaker_role === 'victim' ? 'selected' : ''}>Victim</option>
              <option value="witness" ${spk.speaker_role === 'witness' ? 'selected' : ''}>Witness</option>
              <option value="suspect" ${spk.speaker_role === 'suspect' ? 'selected' : ''}>Suspect</option>
              <option value="informant" ${spk.speaker_role === 'informant' ? 'selected' : ''}>Informant</option>
              <option value="officer" ${spk.speaker_role === 'officer' ? 'selected' : ''}>Officer</option>
            </select>
          </div>
          <div class="speaker-actions">
            <span class="stmt-count-pill">${stmtCountText}</span>
            <button class="btn btn-red btn-sm" onclick="removeSpeaker(${spk._uid})" title="Delete Speaker">✕ Delete Speaker</button>
          </div>
        </div>
        <div class="statements-wrapper">
          ${statementsHtml}
          <button type="button" class="add-stmt-under-speaker-btn" onclick="addStatementToSpeaker(${spk._uid})">
            + Add Another Statement for this Speaker (Separate Date & Time)
          </button>
        </div>
      </div>
    `;
  }).join('');

  // Auto-resize textareas to fit content
  document.querySelectorAll('.statement-textarea').forEach(ta => autoResize(ta));
}

// ═══════════════════════════════════════════════════════════════════════════
// Save / Run / Load Data
// ═══════════════════════════════════════════════════════════════════════════

function gatherCaseData() {
  const caseData = {
    case_id: document.getElementById('case-id').value.trim() || 'CASE-2026-0824',
    incident: document.getElementById('incident-desc').value.trim(),
    incident_date: document.getElementById('incident-date').value.trim(),
    incident_timeframe: `${String(startH).padStart(2, '0')}:${String(startM).padStart(2, '0')} – ${String(endH).padStart(2, '0')}:${String(endM).padStart(2, '0')}`,
    statements: []
  };

  speakers.forEach(spk => {
    spk.statements.forEach(st => {
      caseData.statements.push({
        id: st.id,
        speaker_name: spk.speaker_name || 'Unknown',
        speaker_role: spk.speaker_role || 'witness',
        recorded_at: st.recorded_at,
        statement_text: st.statement_text || ''
      });
    });
  });

  return caseData;
}

async function saveCase() {
  const data = gatherCaseData();
  const btn = document.getElementById('btn-save');
  btn.disabled = true;
  btn.textContent = '⏳ Saving...';

  try {
    const resp = await fetch('/api/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    const res = await resp.json();
    if (res.ok) {
      activeCaseId = res.case_id || data.case_id;
      showToast(`✓ Case '${activeCaseId}' saved to cases/ folder!`, 'success');
      // Cross-tab broadcast
      if (syncChannel) syncChannel.postMessage({ type: 'CASE_SAVED', timestamp: Date.now(), caseId: activeCaseId });
      localStorage.setItem('investigation_case_saved', Date.now());
      // Refresh inventory so sidebar has latest counts and metadata
      await loadCaseInventory();
    } else {
      showToast('Save failed: ' + res.message, 'error');
    }
  } catch(e) {
    showToast('Save error: ' + e.message, 'error');
  }

  btn.disabled = false;
  btn.textContent = '💾 Save Case';
}

async function runPipeline(mode = 'live') {
  // Always save latest state first
  await saveCase();

  const btnLive = document.getElementById('btn-run');
  const btnMock = document.getElementById('btn-run-mock');
  btnLive.disabled = true;
  btnMock.disabled = true;

  const statusText = document.getElementById('pipeline-status-text');
  statusText.className = 'pipeline-status-text running pulsing';
  statusText.textContent = mode === 'mock' ? '● Running fast offline pipeline...' : '● Calling Gemini AI & running 6 algorithms...';

  try {
    const resp = await fetch(`/api/run?mode=${mode}`, { method: 'POST' });
    const res = await resp.json();
    if (!res.ok) {
      showToast(res.message, 'error');
      btnLive.disabled = false;
      btnMock.disabled = false;
      statusText.className = 'pipeline-status-text error';
      statusText.textContent = '✗ Error: ' + res.message;
      return;
    }

    // Poll status until done
    const pollInterval = setInterval(async () => {
      try {
        const sr = await fetch('/api/status');
        const st = await sr.json();
        if (st.message) {
          statusText.textContent = `● ${st.message}`;
        }
        if (!st.running) {
          clearInterval(pollInterval);
          btnLive.disabled = false;
          btnMock.disabled = false;

          if (st.result === 'success') {
            statusText.className = 'pipeline-status-text done';
            statusText.textContent = `✓ Complete (${(st.last_run || '').slice(11, 19)})`;
            showToast('🎉 Analysis complete! Master timeline updated. Switch to the Timeline tab to inspect.', 'success');

            // Notify Timeline tab via BroadcastChannel & localStorage
            if (syncChannel) syncChannel.postMessage({ type: 'PIPELINE_COMPLETE', timestamp: Date.now() });
            localStorage.setItem('investigation_last_run', Date.now());
          } else {
            statusText.className = 'pipeline-status-text error';
            statusText.textContent = '✗ Pipeline execution error';
            showToast('Pipeline error: ' + (st.message || 'Check console.'), 'error');
            console.error(st.error);
          }
        }
      } catch(e) {
        console.error('Polling error:', e);
      }
    }, 1200);

  } catch(e) {
    showToast('Network error: ' + e.message, 'error');
    btnLive.disabled = false;
    btnMock.disabled = false;
    statusText.className = 'pipeline-status-text error';
    statusText.textContent = '✗ Network Error';
  }
}

async function loadCaseData(targetCaseId = null) {
  try {
    const url = targetCaseId ? `/api/case?id=${encodeURIComponent(targetCaseId)}` : '/api/case';
    const resp = await fetch(url);
    if (!resp.ok) {
      throw new Error(`Server returned ${resp.status}`);
    }
    const data = await resp.json();

    activeCaseId = data.case_id || 'CASE-2026-0824';
    document.getElementById('case-id').value = activeCaseId;
    document.getElementById('incident-desc').value = data.incident || '';
    
    // Incident Date
    calSelectedDate = data.incident_date || new Date().toISOString().slice(0, 10);
    document.getElementById('incident-date').value = calSelectedDate;

    // Timeframe
    const tf = data.incident_timeframe || '20:30 – 22:00';
    const match = tf.match(/(\d{2}):(\d{2})\s*[–-]\s*(\d{2}):(\d{2})/);
    if (match) {
      startH = parseInt(match[1], 10);
      startM = parseInt(match[2], 10);
      endH = parseInt(match[3], 10);
      endM = parseInt(match[4], 10);
    }
    updateClockDisplay();

    // Group statements by speaker_name
    speakers = [];
    speakerCounter = 0;
    statementCounter = 0;

    const speakerMap = new Map();
    (data.statements || []).forEach(st => {
      const spkName = st.speaker_name || 'Unknown';
      if (!speakerMap.has(spkName)) {
        speakerCounter++;
        speakerMap.set(spkName, {
          _uid: speakerCounter,
          speaker_id: `SPK_${String(speakerCounter).padStart(2, '0')}`,
          speaker_name: spkName,
          speaker_role: st.speaker_role || 'witness',
          statements: []
        });
      }
      statementCounter++;
      const spk = speakerMap.get(spkName);
      spk.statements.push({
        _uid: statementCounter,
        id: st.id || `STMT_${String(statementCounter).padStart(2, '0')}`,
        recorded_at: st.recorded_at || getNowTimestamp(),
        statement_text: st.statement_text || '',
      });
    });

    speakers = Array.from(speakerMap.values());
    if (!speakers.length) {
      addNewSpeaker();
    } else {
      renderSpeakers();
    }

    // Refresh inventory cards so this card is highlighted as active
    renderCaseInventory();

  } catch(e) {
    console.warn('Could not load case data, initializing fresh.', e);
    updateClockDisplay();
    addNewSpeaker();
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// Case Inventory Side Panel Management
// ═══════════════════════════════════════════════════════════════════════════

let activeCaseId = '';
let inventoryCases = [];

function toggleCaseSidebar(forceState) {
  const sidebar = document.getElementById('case-sidebar');
  const overlay = document.getElementById('sidebar-overlay');
  const shouldOpen = forceState !== undefined ? forceState : !sidebar.classList.contains('open');
  if (shouldOpen) {
    sidebar.classList.add('open');
    overlay.classList.add('open');
    loadCaseInventory();
  } else {
    sidebar.classList.remove('open');
    overlay.classList.remove('open');
  }
}

async function loadCaseInventory() {
  const statsEl = document.getElementById('inventory-stats');
  const badgeEl = document.getElementById('inventory-count-badge');
  try {
    const resp = await fetch('/api/cases');
    const res = await resp.json();
    if (res.ok && res.cases) {
      inventoryCases = res.cases;
      const count = inventoryCases.length;
      if (badgeEl) badgeEl.textContent = count;
      if (statsEl) statsEl.textContent = `${count} ${count === 1 ? 'case file' : 'case files'} in /cases`;
      renderCaseInventory();
    }
  } catch(e) {
    console.error('Failed to load case inventory:', e);
    if (statsEl) statsEl.textContent = 'Error loading cases';
  }
}

function renderCaseInventory(filteredList = null) {
  const container = document.getElementById('case-inventory-list');
  if (!container) return;
  const list = filteredList !== null ? filteredList : inventoryCases;

  if (!list.length) {
    container.innerHTML = `
      <div class="inventory-empty-state">
        <div style="font-size:26px;margin-bottom:8px;">📁</div>
        <div style="font-weight:600;color:var(--text-primary);">No cases in inventory</div>
        <div style="font-size:11px;margin-top:4px;">Click <strong>+ New Case Intake</strong> above to create one.</div>
      </div>
    `;
    return;
  }

  const currentFormId = document.getElementById('case-id') ? document.getElementById('case-id').value.trim() : '';

  container.innerHTML = list.map(c => {
    const isActive = (c.case_id === activeCaseId) || (c.case_id === currentFormId);
    const stCount = c.statement_count || 0;
    const spkCount = (c.speakers || []).length;
    const title = c.incident ? c.incident : 'Untitled Incident';
    const dateStr = c.incident_date || 'No Date';

    return `
      <div class="inventory-case-card ${isActive ? 'active-case' : ''}" onclick="openCase('${esc(c.case_id)}')">
        <div class="card-header-row">
          <span class="card-case-id">${esc(c.case_id)}</span>
          ${isActive ? '<span class="card-active-pill"><span class="pulse-dot"></span>ACTIVE</span>' : ''}
        </div>
        <div class="card-incident-title" title="${esc(title)}">${esc(title)}</div>
        <div class="card-meta-row">
          <div class="card-meta-item"><span>📅</span> ${esc(dateStr)}</div>
          <div class="card-meta-item"><span>🗣</span> ${stCount} stmt${stCount === 1 ? '' : 's'} (${spkCount} spk)</div>
        </div>
        <div class="card-actions-row">
          <button type="button" class="card-open-btn" onclick="event.stopPropagation(); openCase('${esc(c.case_id)}')">
            📂 Reopen Case
          </button>
          <button type="button" class="card-delete-btn" onclick="deleteCase('${esc(c.case_id)}', event)" title="Permanently delete case JSON file from disk">
            <span>🗑</span> Close & Delete
          </button>
        </div>
      </div>
    `;
  }).join('');
}

function filterCaseInventory(query) {
  const q = (query || '').trim().toLowerCase();
  const clearBtn = document.getElementById('search-clear-btn');
  if (clearBtn) clearBtn.style.display = q ? 'block' : 'none';

  if (!q) {
    renderCaseInventory();
    return;
  }

  const filtered = inventoryCases.filter(c => {
    const idMatch = (c.case_id || '').toLowerCase().includes(q);
    const incMatch = (c.incident || '').toLowerCase().includes(q);
    const spkMatch = (c.speakers || []).some(s => s.toLowerCase().includes(q));
    const dateMatch = (c.incident_date || '').toLowerCase().includes(q);
    return idMatch || incMatch || spkMatch || dateMatch;
  });

  renderCaseInventory(filtered);
}

function clearCaseSearch() {
  const input = document.getElementById('case-search-input');
  if (input) input.value = '';
  filterCaseInventory('');
}

async function openCase(caseId) {
  await loadCaseData(caseId);
  toggleCaseSidebar(false);
  showToast(`📂 Reopened case ${caseId} from cases/ folder`, 'info');
}

function createNewCase() {
  const year = new Date().getFullYear();
  const randId = 'CASE-' + year + '-' + String(Math.floor(1000 + Math.random() * 9000));
  
  activeCaseId = randId;
  document.getElementById('case-id').value = randId;
  document.getElementById('incident-desc').value = '';

  // Today's date
  calSelectedDate = new Date().toISOString().slice(0, 10);
  document.getElementById('incident-date').value = calSelectedDate;

  // Default timeframe
  startH = 20; startM = 30;
  endH = 22; endM = 0;
  updateClockDisplay();

  // Reset speakers to single blank speaker
  speakers = [];
  speakerCounter = 0;
  statementCounter = 0;
  addNewSpeaker();

  // Refresh sidebar & close
  renderCaseInventory();
  toggleCaseSidebar(false);
  showToast(`✨ Initialized fresh case: ${randId}. Fill details and click "Save Case" to store in cases/.`, 'info');
}

async function deleteCase(caseId, e) {
  if (e) e.stopPropagation();

  const confirmed = confirm(`Are you sure you want to close and permanently delete case "${caseId}"?\n\nThis action cannot be undone. The JSON file will be deleted from the cases/ folder.`);
  if (!confirmed) return;

  try {
    const resp = await fetch(`/api/case/delete?id=${encodeURIComponent(caseId)}`, { method: 'POST' });
    const res = await resp.json();
    if (res.ok) {
      showToast(`🗑 ${res.message || 'Case file deleted.'}`, 'info');
      // Reload inventory
      await loadCaseInventory();
      
      // If deleted case was currently open, switch to first remaining or create fresh
      const currentFormId = document.getElementById('case-id').value.trim();
      if (currentFormId === caseId) {
        if (inventoryCases.length > 0) {
          await loadCaseData(inventoryCases[0].case_id);
          showToast(`Switched active view to ${inventoryCases[0].case_id}`, 'info');
        } else {
          createNewCase();
        }
      }
    } else {
      showToast('Delete failed: ' + res.message, 'error');
    }
  } catch(err) {
    showToast('Delete error: ' + err.message, 'error');
  }
}

function openTimeline() {
  window.open('/timeline', '_blank');
}

function openReport() {
  window.open('/output/report.html', '_blank');
}

// ═══════════════════════════════════════════════════════════════════════════
// UI Helpers
// ═══════════════════════════════════════════════════════════════════════════

function showToast(msg, type = 'info') {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'toast visible ' + type;
  setTimeout(() => { t.classList.remove('visible'); }, 4000);
}

function esc(s) {
  if (s == null) return '';
  const d = document.createElement('div');
  d.textContent = String(s);
  return d.innerHTML;
}

// Initialize on page load
loadCaseData();
loadCaseInventory();
</script>
</body>
</html>"""


# ═══════════════════════════════════════════════════════════════════════════
# Server Launcher
# ═══════════════════════════════════════════════════════════════════════════

def main():
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8500
    server = HTTPServer(("127.0.0.1", port), InvestigationHandler)
    print(f"\n{'='*60}")
    print(f"  [+] Investigation Server Running")
    print(f"  --------------------------------------------------------")
    print(f"  Case Input Form : http://localhost:{port}/")
    print(f"  Timeline View   : http://localhost:{port}/timeline")
    print(f"  Analytical Rep  : http://localhost:{port}/output/report.html")
    print(f"{'='*60}\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        server.server_close()


if __name__ == "__main__":
    main()
