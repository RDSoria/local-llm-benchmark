# 🚀 Gemma-4 Local Benchmark (OpenCode Edition)

Este repositorio contiene un framework de pruebas automatizado para medir el rendimiento del modelo **Gemma-4-26B-A4B** (Arquitectura MoE) en tareas de ingeniería de software local, utilizando **OpenCode** como orquestador y **LM Studio** como motor de inferencia.

El benchmark separa el flujo de trabajo en dos fases críticas: **Planificación de Arquitectura** y **Ejecución de Código**, almacenando todos los artefactos en una carpeta aislada.

## 📁 Estructura del Proyecto

* `benchmark.sh`: Script de automatización que orquestra los agentes de OpenCode.
* `consolidator.py`: Procesador de métricas que genera el reporte final.
* `prompt.txt`: Archivo de entrada con el requerimiento técnico.
* `/results`: Carpeta autogenerada que contiene:
    * `metrics_raw.jsonl`: Logs de tiempo y TTFT en bruto.
    * `benchmark_report.json`: Reporte consolidado en formato JSON.
    * **Artefactos generados**: Todo el código y archivos `.md` creados por el modelo.

## 📊 Métricas Capturadas

* **TTFT (Time to First Token):** Latencia inicial (ms). Crucial para medir el tiempo de carga de expertos en modelos MoE.
* **Total Time:** Duración completa de la inferencia (segundos).
* **Tasks (Plan):** Cantidad de hitos o pasos detectados en la estrategia del modelo.
* **Tasks (Build):** Cantidad de llamadas a herramientas (`tool_calls`) ejecutadas (escritura de archivos, comandos).

---

## ⚙️ Configuración del Entorno

### Requisitos
1.  **OpenCode CLI** instalado (Versión 2026).
2.  **LM Studio** activo en `http://localhost:1234`.
3.  **Gemma-4-26B-A4B** (o cualquier modelo compatible) cargado.

### Configuración de OpenCode (`opencode.json`)
```json
{
  "model": "lmstudio/google/gemma-4-26b-a4b",
  "provider": {
    "lmstudio": {
      "options": {
        "baseURL": "http://127.0.0.1:1234/v1"
      }
    }
  }
}
```

---

## 🛠️ Ejecución del Benchmark

### 1. Definir el objetivo
Escribe tu requerimiento en `prompt.txt`. 
*Ejemplo: "Crea un script de Python que analice un CSV y genere un gráfico con Matplotlib".*

### 2. Lanzar la prueba
El script ejecutará el agente `plan`, guardará el contexto y luego ejecutará el agente `build` usando el flag `--continue`.

```bash
chmod +x benchmark.sh
./benchmark.sh
```

### 3. Procesar y visualizar
Extrae los datos de la sesión y genera la tabla comparativa:

```bash
python consolidator.py
```

---

## 📈 Ejemplo de Salida en Consola

Al finalizar, verás una comparativa técnica del desempeño:

| MODELO | MODO | TTFT | TOTAL | TAREAS |
| :--- | :--- | :--- | :--- | :--- |
| gemma-4-26b-a4b | plan | 40,474.54ms | 40.64s | 3 |
| gemma-4-26b-a4b | build | 13,377.56ms | 13.41s | 2 |

---

## 🧠 Notas Técnicas sobre Gemma-4 (A4B) en Mac

* **Comportamiento MoE:** Es normal observar un TTFT elevado en la primera ejecución mientras el sistema gestiona la Memoria Unificada para los expertos del modelo.
* **KV Caching:** Gracias al uso de `--continue` en el modo Build, el tiempo de respuesta suele reducirse drásticamente (hasta un 60-70%) al reutilizar los tokens procesados en la fase de Plan.
* **Aislamiento:** Al usar el flag `--dir results`, garantizamos que el benchmark no contamine la raíz del repositorio con código generado.
