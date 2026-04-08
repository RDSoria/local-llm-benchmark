import json
import re
import os
import glob

# --- CONFIGURACIÓN DE RUTAS ---
RESULTS_DIR = "results"
METRICS_LOG = os.path.join(RESULTS_DIR, "metrics_raw.jsonl")
FINAL_REPORT = os.path.join(RESULTS_DIR, "benchmark_report.json")
STORAGE_BASE = os.path.expanduser("~/.local/share/opencode/storage")
PROJECT_ID = "299cb18bde341dd9de3c76e22d4bbfcaedad8c01"

def extract_tasks_from_text(text):
    if not text: return 0
    tasks = re.findall(r'(?:[-*]\s?\[\s?\]|^\d+\.\s+|[-*]\s+)', text, re.MULTILINE)
    return len(tasks) if len(tasks) > 0 else 1

def get_latest_message_dirs(limit=2):
    # Buscamos en el storage de mensajes de opencode
    msg_path = os.path.join(STORAGE_BASE, "message", "ses_*")
    sessions = glob.glob(msg_path)
    if not sessions:
        return []
    # Retornamos las N carpetas de sesión más recientes
    sessions.sort(key=os.path.getmtime, reverse=True)
    return sessions[:limit]

def extract_metadata_from_messages(msg_dirs, mode):
    metadata = {"tokens": 0, "tasks": 0, "content": ""}
    if not msg_dirs:
        return metadata

    tool_calls_count = 0
    # Buscamos en las últimas sesiones (por si el plan y build se separaron)
    for msg_dir in msg_dirs:
        msg_files = glob.glob(os.path.join(msg_dir, "msg_*.json"))
        msg_files.sort(key=os.path.getmtime)

        for msg_file in msg_files:
            try:
                with open(msg_file, 'r') as f:
                    data = json.load(f)
                    if data.get('role') == 'assistant':
                        # Normalizar el modo para comparación (plan, build, architect, etc)
                        msg_mode = str(data.get('mode', data.get('agent', ''))).lower()
                        target_mode = mode.lower()
                        
                        # Coincidencia flexible
                        if target_mode in msg_mode or (target_mode == "plan" and "architect" in msg_mode):
                            # Extraer tokens de salida
                            tokens = data.get('tokens', {})
                            metadata["tokens"] += tokens.get('output', 0)
                            
                            # Si es el último mensaje del modo, extraer contenido para tareas
                            content = data.get('content', '')
                            if content:
                                metadata["content"] = content
                            
                            # Contar tool_calls si existen
                            t_calls = data.get('tool_calls', [])
                            if t_calls:
                                tool_calls_count += len(t_calls)
            except:
                continue
    
    if mode == "plan":
        metadata["tasks"] = extract_tasks_from_text(metadata["content"])
    elif mode == "build":
        metadata["tasks"] = tool_calls_count if tool_calls_count > 0 else 1
        
    return metadata

def extract_ram_usage(mode):

    log_path = os.path.join(RESULTS_DIR, f"resource_{mode}.log")
    if not os.path.exists(log_path): return "N/A"
    try:
        with open(log_path, 'r') as f:
            content = f.read()
            # En macOS: "maximum resident set size" es el pico de RAM en bytes
            match = re.search(r"(\d+)\s+maximum resident set size", content)
            if match:
                ram_mb = int(match.group(1)) / (1024 * 1024)
                return f"{ram_mb:.2f}MB"
    except:
        pass
    return "N/A"

def check_placeholders():
    patterns = [r"TODO:", r"\.\.\.", r"\[Insert code here\]", r"// your code here"]
    files = glob.glob(os.path.join(RESULTS_DIR, "**/*.*"), recursive=True)
    placeholders_found = 0
    for file in files:
        if os.path.basename(file) in ["metrics_raw.jsonl", "benchmark_report.json"]: continue
        if "resource_" in file: continue
        try:
            with open(file, 'r') as f:
                content = f.read()
                for p in patterns:
                    if re.search(p, content, re.IGNORECASE):
                        placeholders_found += 1
                        break
        except:
            continue
    return "FAIL" if placeholders_found > 0 else "PASS"

def extract_provider_ram(mode):
    tmp_path = os.path.join(RESULTS_DIR, f"prov_peak_{mode}.tmp")
    res = {"lms": "-", "ollama": "-", "lcpp": "-"}
    if not os.path.exists(tmp_path): return res
    
    try:
        with open(tmp_path, 'r') as f:
            parts = f.read().strip().split(':')
            if len(parts) == 3:
                lms, ollama, lcpp = [float(p) for p in parts]
                
                # Formatear solo el que tenga consumo > 0
                if lms > 1.0: res["lms"] = f"{lms/1024:.2f}GB" if lms > 1024 else f"{lms:.2f}MB"
                if ollama > 1.0: res["ollama"] = f"{ollama/1024:.2f}GB" if ollama > 1024 else f"{ollama:.2f}MB"
                if lcpp > 1.0: res["lcpp"] = f"{lcpp/1024:.2f}GB" if lcpp > 1024 else f"{lcpp:.2f}MB"
    except:
        pass
    return res

def process_benchmark():
    if not os.path.exists(METRICS_LOG):
        print(f"Error: No se encontró {METRICS_LOG}")
        return

    msg_dirs = get_latest_message_dirs(limit=3)
    report_data = []

    with open(METRICS_LOG, "r") as f:
        for line in f:
            try:
                raw = json.loads(line)
                ttft_ms = (raw['ttft_ns'] - raw['start_ns']) / 1_000_000
                total_s = (raw['end_ns'] - raw['start_ns']) / 1_000_000_000
                
                prov_ram = extract_provider_ram(raw['step'])
                entry = {
                    "model": raw['model'].split('/')[-1],
                    "mode": raw['step'],
                    "ttft": f"{ttft_ms:,.2f}ms",
                    "total": f"{total_s:.2f}s",
                    "ram": extract_ram_usage(raw['step']),
                    "lms": prov_ram["lms"],
                    "ollama": prov_ram["ollama"],
                    "lcpp": prov_ram["lcpp"],
                    "tps": "N/A",
                    "tasks": 0,
                    "status": "N/A"
                }

                if msg_dirs:
                    metadata = extract_metadata_from_messages(msg_dirs, raw['step'])
                    comp_tokens = metadata.get('tokens', 0)
                    
                    if comp_tokens > 0 and (total_s - (ttft_ms/1000)) > 0:
                        tps = comp_tokens / (total_s - (ttft_ms/1000))
                        entry["tps"] = f"{tps:.1f}"

                    entry["tasks"] = metadata.get('tasks', 0)
                    if raw['step'] == "build":
                        entry["status"] = check_placeholders()

                report_data.append(entry)
            except Exception as e:
                continue

    # Guardar reporte detallado en la carpeta results
    with open(FINAL_REPORT, "w") as out:
        json.dump(report_data, out, indent=4)

    # Imprimir tabla
    # Calculamos el ancho total para las líneas decorativas
    # MODELO(22) + MODO(6) + TTFT(15) + TOTAL(10) + OC RAM(10) + LMS(10) + Ollama(10) + LCPP(10) + TPS(12) + TAREAS(6) + separadores
    table_width = 145
    print(f"\n{'='*table_width}")
    print(f"{'MODELO':<22} | {'MODO':<6} | {'TTFT':^15} | {'TOTAL':^10} | {'OC RAM':^10} | {'LMS':^10} | {'Ollama':^10} | {'LCPP':^10} | {'TPS':^12} | {'TAREAS'}")
    print(f"{'-'*table_width}")
    for r in report_data:
        print(f"{r['model'][:22]:<22} | {r['mode']:<6} | {r['ttft']:>15} | {r['total']:>10} | {r['ram']:>10} | {r['lms']:>10} | {r['ollama']:>10} | {r['lcpp']:>10} | {r['tps']:>12} | {r['tasks']}")
    
    if any(r['status'] != "N/A" for r in report_data):
        status = next((r['status'] for r in report_data if r['status'] != "N/A"), "N/A")
        print(f"{'-'*table_width}")
        print(f"ESTADO DE COMPLETITUD (BUILD): {status}")
    
    print(f"{'='*table_width}")
    print(f"Reporte guardado en: {FINAL_REPORT}\n")

if __name__ == "__main__":
    process_benchmark()