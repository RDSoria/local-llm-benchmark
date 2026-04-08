import csv
import os
from operator import itemgetter

# --- CONFIGURACIÓN ---
HISTORY_CSV = "history.csv"

def format_table():
    if not os.path.exists(HISTORY_CSV):
        print(f"Error: No se encontró {HISTORY_CSV}. Ejecuta un benchmark primero.")
        return

    data = []
    with open(HISTORY_CSV, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(row)

    if not data:
        print("El historial está vacío.")
        return

    # Identificar el más reciente por TIMESTAMP
    latest_run = max(data, key=itemgetter('TIMESTAMP'))
    latest_id = latest_run['ID']

    # Ordenar por SCORE (descendente)
    # Convertimos a float para ordenar correctamente
    data.sort(key=lambda x: float(x['SCORE']), reverse=True)

    # Configuración de anchos de columna
    # RANK(4) | ID(8) | MODEL(22) | PROV(5) | TIME(8) | RAM(10) | TPS(12) | QUAL(6) | SCORE(6)
    col_widths = [4, 8, 22, 5, 8, 10, 12, 6, 6]
    headers = ["RANK", "ID", "MODEL", "PROV", "TIME(s)", "RAM(MB)", "TPS", "QUAL", "SCORE"]
    
    table_width = sum(col_widths) + (len(col_widths) * 3) + 1
    
    # ANSI Colors
    GREEN = "\033[92m"
    BOLD = "\033[1m"
    RESET = "\033[0m"
    YELLOW = "\033[93m"

    print(f"\n{BOLD}{'=' * table_width}{RESET}")
    print(f"{BOLD} RANK | ID       | MODEL                  | PROV  | TIME(s)  | RAM(MB)    | TPS          | QUAL   | SCORE {RESET}")
    print(f"{'-' * table_width}")

    for i, row in enumerate(data, 1):
        is_latest = (row['ID'] == latest_id)
        
        # Preparar strings con formato
        rank_str = f"{i:^4}"
        id_str = f"{row['ID']:<8}"
        model_str = f"{row['MODEL'][:22]:<22}"
        prov_str = f"{row['PROVIDER']:<5}"
        time_str = f"{float(row['TOTAL_SEC']):>8.2f}"
        ram_str = f"{float(row['RAM_MB']):>10.2f}"
        tps_str = f"{float(row['TPS']):>12.1f}"
        qual_str = f"{row['QUALITY']:^6}"
        score_str = f"{float(row['SCORE']):>6.1f}"

        line = f" {rank_str} | {id_str} | {model_str} | {prov_str} | {time_str} | {ram_str} | {tps_str} | {qual_str} | {score_str} "
        
        if is_latest:
            # Resaltar en Amarillo/Negrita y añadir marca
            print(f"{YELLOW}{BOLD}{line} <--- LATEST{RESET}")
        else:
            print(line)

    print(f"{BOLD}{'=' * table_width}{RESET}")
    print(f"Total de ejecuciones: {len(data)}\n")

if __name__ == "__main__":
    format_table()
