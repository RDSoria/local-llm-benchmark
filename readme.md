# 🚀 Local Benchmark (OpenCode Edition)

Este repositorio contiene un framework de pruebas automatizado para medir el rendimiento de modelos de lenguaje locales en tareas de ingeniería de software, utilizando **OpenCode** como orquestador y **LM Studio** como motor de inferencia.

> **Aclaración de Modelos:** Aunque el benchmark está pre-configurado para **Gemma-4-26B-A4B**, es compatible con cualquier modelo local (Llama-3, Mistral, Phi-4, etc.) que sea servido mediante una API compatible con OpenAI en LM Studio.

El benchmark separa el flujo de trabajo en dos fases críticas: **Planificación de Arquitectura** (Plan) y **Ejecución de Código** (Build), almacenando todos los artefactos en una carpeta aislada.

## 📁 Estructura del Proyecto

* `benchmark.sh`: Script de automatización que orquestra los agentes de OpenCode y mide recursos (RAM de proveedores en tiempo real).
* `consolidator.py`: Procesador de métricas que genera el reporte final analizando los mensajes de la sesión y los logs de recursos.
* `prompt.txt`: Archivo de entrada con el requerimiento técnico.
* `/results`: Carpeta autogenerada que contiene:
    * `metrics_raw.jsonl`: Logs de tiempo y TTFT.
    * `resource_plan.log` / `resource_build.log`: Logs de consumo de RAM/CPU de OpenCode (macOS).
    * `prov_peak_plan.tmp` / `prov_peak_build.tmp`: Picos de RAM detectados en los proveedores.
    * `benchmark_report.json`: Reporte consolidado en formato JSON.
    * **Artefactos generados**: Todo el código y archivos `.md` creados por el modelo.

## 📊 Métricas Capturadas

* **TTFT (Time to First Token):** Latencia inicial (ms).
* **Total Time:** Duración completa de la inferencia (segundos).
* **OC RAM:** Consumo máximo de memoria del orquestador OpenCode.
* **Providers RAM (LMS, Ollama, LCPP):** Consumo máximo detectado del motor de inferencia activo. El sistema detecta automáticamente cuál está en uso.
* **TPS (Tokens Per Second):** Velocidad de generación efectiva (Completion Tokens / Generation Time).
* **Tasks (Plan/Build):** Hitos detectados en el plan o cantidad de `tool_calls` ejecutadas.
* **Completeness Check:** Escaneo heurístico de "placeholders" (`TODO`, `...`, `// your code here`) para detectar si el modelo fue perezoso.

---

## 📈 Ejemplo de Salida en Consola

Al finalizar, verás una comparativa técnica detallada y alineada del desempeño:

```text
=================================================================================================================================================
MODELO                 | MODO   |      TTFT       |   TOTAL    |   OC RAM   |    LMS     |   Ollama   |    LCPP    |     TPS      | TAREAS
-------------------------------------------------------------------------------------------------------------------------------------------------
gemma-4-26b-a4b        | plan   |     49,431.99ms |     49.60s |   409.91MB |   362.56MB |          - |          - |     106162.4 | 0
gemma-4-26b-a4b        | build  |      9,432.47ms |     32.47s |   363.23MB |   364.17MB |          - |          - |        927.6 | 1
-------------------------------------------------------------------------------------------------------------------------------------------------
ESTADO DE COMPLETITUD (BUILD): PASS
=================================================================================================================================================
Reporte guardado en: results/benchmark_report.json
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

Al finalizar, verás una comparativa técnica detallada del desempeño:

```text
==================================================================================================================================
MODELO             | MODO  | TTFT       | TOTAL   | OC RAM   | LMS      | Ollama   | LCPP     | TPS   | TAREAS
----------------------------------------------------------------------------------------------------------------------------------
gemma-4-26b-a4b    | plan  | 35,899.79ms|  36.12s | 419.22MB |   8.45GB |        - |        - | 79429 | 0
gemma-4-26b-a4b    | build | 16,806.02ms|  16.88s | 378.06MB |   9.12GB |        - |        - | 27706 | 1
----------------------------------------------------------------------------------------------------------------------------------
ESTADO DE COMPLETITUD (BUILD): PASS
==================================================================================================================================
Reporte guardado en: results/benchmark_report.json
```


---

## 🧠 Notas Técnicas sobre Gemma-4 (A4B) en Mac

* **Comportamiento MoE:** Es normal observar un TTFT elevado en la primera ejecución mientras el sistema gestiona la Memoria Unificada para los expertos del modelo.
* **KV Caching:** Gracias al uso de `--continue` en el modo Build, el tiempo de respuesta suele reducirse drásticamente (hasta un 60-70%) al reutilizar los tokens procesados en la fase de Plan.
* **Aislamiento:** Al usar el flag `--dir results`, garantizamos que el benchmark no contamine la raíz del repositorio con código generado.
