#!/bin/bash

# --- PREPARACIÓN ---
# Crear carpeta de resultados si no existe
mkdir -p results
# Limpiar métricas anteriores dentro de results
rm -f results/metrics_raw.jsonl

# Función para ejecutar y medir
run_benchmark() {
    local MODEL_ID=$1
    local AGENT_NAME=$2
    local MESSAGE=$3
    local CONTINUE_FLAG=$4

    echo "------------------------------------------------"
    echo "EJECUTANDO: $MODEL_ID | AGENTE: $AGENT_NAME"
    
    start_time=$(date +%s%N)
    
    # Ejecutamos usando --dir results para que el código generado caiga ahí
    opencode run $CONTINUE_FLAG \
        --agent "$AGENT_NAME" \
        --model "$MODEL_ID" \
        --dir "results" \
        "$MESSAGE" | awk 'NR==1 { system("date +%s%N > .ttft_tmp") } { print }'
    
    # Nota: Si tu versión de opencode no soporta --dir, podemos usar cd results && opencode ... && cd ..
    
    end_time=$(date +%s%N)
    
    # Captura de TTFT
    if [ -f .ttft_tmp ]; then
        ttft_time=$(cat .ttft_tmp)
        rm .ttft_tmp
    else
        ttft_time=$end_time
    fi

    # Guardamos el JSONL dentro de la carpeta results
    echo "{\"model\": \"$MODEL_ID\", \"step\": \"$AGENT_NAME\", \"start_ns\": $start_time, \"ttft_ns\": $ttft_time, \"end_ns\": $end_time}" >> results/metrics_raw.jsonl
}

# --- FLUJO ---
MODEL="lmstudio/google/gemma-4-26b-a4b"
PROMPT_CONTENT=$(cat prompt.txt)

# PASO A: PLAN
run_benchmark "$MODEL" "plan" "$PROMPT_CONTENT" ""

# PASO B: BUILD
run_benchmark "$MODEL" "build" "Execute the plan" "--continue"

echo "Benchmark completado. Los archivos generados y las métricas están en /results"