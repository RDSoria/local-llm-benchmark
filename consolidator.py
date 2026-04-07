import json
import re
import os
import glob

# --- CONFIGURACIÓN DE RUTAS ---
RESULTS_DIR = "results"
METRICS_LOG = os.path.join(RESULTS_DIR, "metrics_raw.jsonl")
FINAL_REPORT = os.path.join(RESULTS_DIR, "benchmark_report.json")

def get_latest_session_dir():
    # La carpeta .opencode suele estar en la raíz del proyecto, no dentro de results
    path = os.path.expanduser("./.opencode/sessions/*")
    sessions = glob.glob(path)
    if not sessions:
        return None
    return max(sessions, key=os.path.getmtime)

def extract_tasks_from_text(text):
    if not text: return 0
    tasks = re.findall(r'(?:[-*]\s?\[\s?\]|^\d+\.\s+|[-*]\s+)', text, re.MULTILINE)
    return len(tasks) if len(tasks) > 0 else 1

def process_benchmark():
    if not os.path.exists(METRICS_LOG):
        print(f"Error: No se encontró {METRICS_LOG}")
        return

    session_dir = get_latest_session_dir()
    report_data = []

    with open(METRICS_LOG, "r") as f:
        for line in f:
            try:
                raw = json.loads(line)
                ttft_ms = (raw['ttft_ns'] - raw['start_ns']) / 1_000_000
                total_s = (raw['end_ns'] - raw['start_ns']) / 1_000_000_000
                
                entry = {
                    "model": raw['model'].split('/')[-1],
                    "mode": raw['step'],
                    "ttft": f"{ttft_ms:,.2f}ms",
                    "total": f"{total_s:.2f}s",
                    "tasks": 0
                }

                if session_dir:
                    hist_path = os.path.join(session_dir, "session.json")
                    if os.path.exists(hist_path):
                        with open(hist_path, 'r') as hf:
                            session_data = json.load(hf)
                            messages = [m for m in session_data.get('messages', []) if m.get('role') == 'assistant']
                            if raw['step'] == "plan" and messages:
                                entry["tasks"] = extract_tasks_from_text(messages[-1].get('content', ''))
                            elif raw['step'] == "build":
                                tool_calls = sum(len(m.get('tool_calls', [])) for m in messages if m.get('tool_calls'))
                                entry["tasks"] = tool_calls if tool_calls > 0 else 1

                report_data.append(entry)
            except Exception as e:
                continue

    # Guardar reporte detallado en la carpeta results
    with open(FINAL_REPORT, "w") as out:
        json.dump(report_data, out, indent=4)

    # Imprimir tabla
    print(f"\n{'='*75}")
    print(f"{'MODELO':<25} | {'MODO':<7} | {'TTFT':<12} | {'TOTAL':<8} | {'TAREAS'}")
    print(f"{'-'*75}")
    for r in report_data:
        print(f"{r['model'][:25]:<25} | {r['mode']:<7} | {r['ttft']:>12} | {r['total']:>8} | {r['tasks']}")
    print(f"{'='*75}")
    print(f"Reporte guardado en: {FINAL_REPORT}\n")

if __name__ == "__main__":
    process_benchmark()