# 🚀 Local Benchmark (OpenCode Edition)

Este repositorio contiene un framework de pruebas automatizado para medir el rendimiento de modelos de lenguaje locales en tareas de ingeniería de software, utilizando **OpenCode** como orquestador y **LM Studio** como motor de inferencia.

> **Aclaración de Modelos:** Aunque el benchmark está pre-configurado para **Gemma-4-26B-A4B**, es compatible con cualquier modelo local (Llama-3, Mistral, Phi-4, etc.) que sea servido mediante una API compatible con OpenAI en LM Studio.

El benchmark separa el flujo de trabajo en dos fases críticas: **Planificación de Arquitectura** (Plan) y **Ejecución de Código** (Build), almacenando todos los artefactos en una carpeta aislada.

## 📁 Estructura del Proyecto

* `benchmark.sh`: Script de automatización que orquestra los agentes de OpenCode y mide recursos (RAM de proveedores en tiempo real).
* `consolidator.py`: Procesador de métricas que genera el reporte final analizando los mensajes de la sesión y los logs de recursos.
* `show_history.py`: Utilidad para visualizar el ranking histórico de ejecuciones almacenado en `history.csv`.
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

## 📊 Historial y Puntuación (Score)

El benchmark mantiene un archivo incremental `history.csv` en la raíz del proyecto. Este archivo consolida las fases de Plan y Build en una sola métrica de rendimiento (Score) calculada de la siguiente manera:

* **Velocidad (40%):** Basado en el TPS promedio. Se normaliza comparando con una referencia de 50 TPS.
* **Latencia (30%):** Basado en el TTFT total acumulado (Plan + Build). Se normaliza comparando con una referencia de 2000ms.
* **Eficiencia (20%):** Basado en el consumo total de RAM (OC + Proveedor). Se normaliza comparando con una referencia de 8192MB (8GB).
* **Calidad (10%):** Basado en el Completeness Check (100 pts si es PASS, 0 pts si es FAIL).

Cada ejecución recibe un **ID único (Short GUID)** de 8 caracteres para evitar colisiones entre dispositivos.

---

## 📈 Visualización del Historial

Para ver una tabla comparativa de todas las ejecuciones, ordenada por puntuación y resaltando la última prueba:

```bash
python show_history.py
```

> **Tip:** Puedes ejecutar todo el flujo (probar, consolidar y ver ranking) con un solo comando:
> ```bash
> ./benchmark.sh && python consolidator.py && python show_history.py
> ```

Esta herramienta te permite comparar fácilmente el rendimiento de diferentes modelos y proveedores a lo largo del tiempo, resaltando automáticamente la ejecución más reciente en amarillo.

**Ejemplo de salida:**

```text
=============================================================================================================
 RANK | ID       | MODEL                  | PROV  | TIME(s)  | RAM(MB)    | TPS          | QUAL   | SCORE 
-------------------------------------------------------------------------------------------------------------
  1   | 1d70e186 | gemma-4-26b-a4b        | LMS   |    37.61 |     609.08 |    1423009.0 |  PASS  |   71.6 
  2   | 79d4e24e | Qwopus3.5-27B-v3-GGUF  | LMS   |   550.03 |     965.86 |     995973.8 |  PASS  |   70.1  <--- LATEST
=============================================================================================================
Total de ejecuciones: 2
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
Extrae los datos de la sesión y genera el reporte consolidado:

```bash
python consolidator.py
```

### 4. Ver Ranking
Compara los resultados con ejecuciones previas:

```bash
python show_history.py
```

---

## 📈 Ejemplo de Salida en Consola (consolidator.py)

Al finalizar `consolidator.py`, verás una comparativa técnica detallada y alineada del desempeño de la sesión actual:

```text
=================================================================================================================================================
MODELO                 | MODO   |      TTFT       |   TOTAL    |   OC RAM   |    LMS     |   Ollama   |    LCPP    |     TPS      | TAREAS
-------------------------------------------------------------------------------------------------------------------------------------------------
gemma-4-26b-a4b        | plan   |     49,431.99ms |     49.60s |   409.91MB |   362.56MB |          - |          - |     106162.4 | 0
gemma-4-26b-a4b        | build  |      9,432.47ms |     32.47s |   363.23MB |   364.17MB |          - |          - |        927.6 | 1
-------------------------------------------------------------------------------------------------------------------------------------------------
ESTADO DE COMPLETITUD (BUILD): PASS
=================================================================================================================================================
ID EJECUCIÓN: 23cb808b | PUNTUACIÓN TOTAL: 71.0
Reporte guardado en: results/benchmark_report.json
Historial actualizado en: history.csv
```


---

## 🧠 Notas Técnicas sobre Gemma-4 (A4B) en Mac

* **Comportamiento MoE:** Es normal observar un TTFT elevado en la primera ejecución mientras el sistema gestiona la Memoria Unificada para los expertos del modelo.
* **KV Caching:** Gracias al uso de `--continue` en el modo Build, el tiempo de respuesta suele reducirse drásticamente (hasta un 60-70%) al reutilizar los tokens procesados en la fase de Plan.
* **Aislamiento:** Al usar el flag `--dir results`, garantizamos que el benchmark no contamine la raíz del repositorio con código generado.
