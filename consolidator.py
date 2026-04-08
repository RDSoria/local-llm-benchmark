import json
import re
import os
import glob
import uuid
from datetime import datetime
import csv

# --- CONFIGURACIÓN DE RUTAS ---
RESULTS_DIR = "results"
METRICS_LOG = os.path.join(RESULTS_DIR, "metrics_raw.jsonl")
FINAL_REPORT = os.path.join(RESULTS_DIR, "benchmark_report.json")
HISTORY_CSV = "history.csv"
STORAGE_BASE = os.path.expanduser("~/.local/share/opencode/storage")
PROJECT_ID = "299cb18bde341dd9de3c76e22d4bbfcaedad8c01"

# --- REFERENCIAS PARA EL SCORE (0-100) ---
REF_TPS = 50.0        # 50 TPS es un 100% en velocidad
REF_TTFT_MS = 2000.0  # 2s de TTFT total es un 100% en latencia
REF_RAM_MB = 8192.0   # 8GB de RAM total es un 100% en eficiencia

def calculate_score(avg_tps, total_ttft_ms, peak_ram_mb, completeness_pass):
    # Pesos: TPS(40%), Latencia(30%), RAM(20%), Calidad(10%)
    
    # Puntuación de Velocidad (TPS)
    s_tps = min(100, (avg_tps / REF_TPS) * 100) if avg_tps > 0 else 0
    
    # Puntuación de Latencia (TTFT) - Menor es mejor
    s_ttft = min(100, (REF_TTFT_MS / max(1, total_ttft_ms)) * 100)
    
    # Puntuación de RAM - Menor es mejor
    s_ram = min(100, (REF_RAM_MB / max(1, peak_ram_mb)) * 100)
    
    # Puntuación de Calidad
    s_qual = 100 if completeness_pass else 0
    
    final_score = (s_tps * 0.4) + (s_ttft * 0.3) + (s_ram * 0.2) + (s_qual * 0.1)
    return round(final_score, 1)

def save_to_history(report_data):
    if not report_data: return "N/A", 0
    
    # Consolidar Plan y Build en una sola fila
    model = report_data[0]['model']
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    run_id = str(uuid.uuid4())[:8]
    
    total_time = 0.0
    total_ttft = 0.0
    peak_ram_oc = 0.0
    peak_ram_prov = 0.0
    sum_tps = 0.0
    tps_count = 0
    quality = "FAIL"
    provider = "N/A"

    for r in report_data:
        # Tiempos
        try:
            total_time += float(r['total'].replace('s', ''))
            total_ttft += float(r['ttft'].replace('ms', '').replace(',', ''))
            
            # RAM OC
            ram_oc_mb = float(r['ram'].replace('MB', '')) if 'MB' in r['ram'] else 0.0
            if 'GB' in r['ram']: ram_oc_mb = float(r['ram'].replace('GB', '')) * 1024
            peak_ram_oc = max(peak_ram_oc, ram_oc_mb)
            
            # RAM Provider (LMS, Ollama, LCPP)
            for p in ['lms', 'ollama', 'lcpp']:
                val = r.get(p, '-')
                if val != '-':
                    provider = p.upper()
                    mb = float(val.replace('MB', '')) if 'MB' in val else 0.0
                    if 'GB' in val: mb = float(val.replace('GB', '')) * 1024
                    peak_ram_prov = max(peak_ram_prov, mb)
            
            # TPS
            if r['tps'] != "N/A":
                sum_tps += float(r['tps'])
                tps_count += 1
                
            # Calidad (solo del build)
            if r['mode'] == 'build':
                quality = r['status']
        except:
            continue

    avg_tps = round(sum_tps / tps_count, 1) if tps_count > 0 else 0.0
    total_ram = peak_ram_oc + peak_ram_prov
    score = calculate_score(avg_tps, total_ttft, total_ram, quality == "PASS")

    file_exists = os.path.isfile(HISTORY_CSV)
    with open(HISTORY_CSV, 'a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["ID", "TIMESTAMP", "MODEL", "PROVIDER", "TOTAL_SEC", "TTFT_MS", "RAM_MB", "TPS", "QUALITY", "SCORE"])
        writer.writerow([run_id, timestamp, model, provider, round(total_time, 2), round(total_ttft, 2), round(total_ram, 2), avg_tps, quality, score])
    
    return run_id, score

def extract_tasks_from_text(text):
    if not text: return 0
    tasks = re.findall(r'(?:[-*]\s?\[\s?\]|^\d+\.\s+|[-*]\s+)', text, re.MULTILINE)
    return len(tasks) if len(tasks) > 0 else 1

def get_latest_message_dirs(limit=5):
    # Buscamos en el storage de mensajes de opencode
    msg_path = os.path.join(STORAGE_BASE, "message", "ses_*")
    sessions = glob.glob(msg_path)
    if not sessions:
        return []
    # Retornamos las N carpetas de sesión más recientes que tengan mensajes
    sessions.sort(key=os.path.getmtime, reverse=True)
    return [s for s in sessions if glob.glob(os.path.join(s, "msg_*.json"))][:limit]

def extract_metadata_from_messages(msg_dirs, mode):
    metadata = {"tokens": 0, "tasks": 0, "content": ""}
    if not msg_dirs:
        return metadata

    tool_calls_count = 0
    target_mode = mode.lower()
    
    # Buscamos en las últimas sesiones (por si el plan y build se separaron)
    for msg_dir in msg_dirs:
        msg_files = glob.glob(os.path.join(msg_dir, "msg_*.json"))
        msg_files.sort(key=os.path.getmtime)

        for msg_file in msg_files:
            try:
                with open(msg_file, 'r') as f:
                    data = json.load(f)
                    if data.get('role') == 'assistant':
                        # Normalizar el modo para comparación
                        msg_mode = str(data.get('mode', data.get('agent', ''))).lower()
                        
                        # Coincidencia flexible: si el modo está en el nombre del agente o modo
                        if target_mode in msg_mode or (target_mode == "plan" and "architect" in msg_mode):
                            # Extraer tokens de salida
                            tokens = data.get('tokens', {})
                            metadata["tokens"] += tokens.get('output', 0)
                            
                            content = data.get('content', '')
                            if content:
                                metadata["content"] = content
                            
                            t_calls = data.get('tool_calls', [])
                            if t_calls:
                                tool_calls_count += len(t_calls)
            except:
                continue
    
    if target_mode == "plan":
        metadata["tasks"] = extract_tasks_from_text(metadata["content"])
    elif target_mode == "build":
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

    msg_dirs = get_latest_message_dirs(limit=10)
    report_data = []

    with open(METRICS_LOG, "r") as f:
        lines = f.readlines()
        if not lines:
            print("Error: metrics_raw.jsonl está vacío")
            return
            
        for line in lines:
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
                print(f"Error en linea: {e}")
                continue

    if not report_data:
        print("No se pudo procesar ninguna métrica.")
        return

    # Guardar reporte detallado en la carpeta results
    with open(FINAL_REPORT, "w") as out:
        json.dump(report_data, out, indent=4)

    # Guardar en historial CSV
    run_id, final_score = save_to_history(report_data)

    # Imprimir tabla
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
    print(f"ID EJECUCIÓN: {run_id} | PUNTUACIÓN TOTAL: {final_score}")
    print(f"Reporte guardado en: {FINAL_REPORT}")
    print(f"Historial actualizado en: {HISTORY_CSV}\n")

if __name__ == "__main__":
    process_benchmark()