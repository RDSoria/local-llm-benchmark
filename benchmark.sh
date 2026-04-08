#!/bin/bash

# --- PREPARACIÓN ---
# Crear carpeta de resultados si no existe
mkdir -p results
# Limpiar métricas anteriores dentro de results
rm -f results/metrics_raw.jsonl

# Función para capturar RAM de proveedores (macOS)
get_provider_ram() {
    # Buscamos consumos para LM Studio, Ollama y llama.cpp
    local lms=$(ps -ax -o rss,comm | grep -i "LM Studio" | grep -v grep | awk '{sum+=$1} END {print sum/1024}')
    local ollama=$(ps -ax -o rss,comm | grep -i "ollama" | grep -v grep | awk '{sum+=$1} END {print sum/1024}')
    local lcpp=$(ps -ax -o rss,comm | grep -iE "llama-server|llama.cpp" | grep -v grep | awk '{sum+=$1} END {print sum/1024}')
    
    # Asegurar que los valores vacíos sean 0
    lms=${lms:-0}
    ollama=${ollama:-0}
    lcpp=${lcpp:-0}
    
    echo "$lms:$ollama:$lcpp"
}

# Función para ejecutar y medir
run_benchmark() {
    local MODEL_ID=$1
    local AGENT_NAME=$2
    local MESSAGE=$3
    local CONTINUE_FLAG=$4

    echo "------------------------------------------------"
    echo "EJECUTANDO: $MODEL_ID | AGENTE: $AGENT_NAME"
    
    # Iniciar monitor de proveedores en segundo plano
    rm -f "results/prov_peak_$AGENT_NAME.tmp"
    (
        peak_lms=0
        peak_ollama=0
        peak_lcpp=0
        while true; do
            IFS=":" read -r curr_lms curr_ollama curr_lcpp <<< "$(get_provider_ram)"
            
            # Comparar y guardar picos
            if (( $(echo "$curr_lms > $peak_lms" | bc -l) )); then peak_lms=$curr_lms; fi
            if (( $(echo "$curr_ollama > $peak_ollama" | bc -l) )); then peak_ollama=$curr_ollama; fi
            if (( $(echo "$curr_lcpp > $peak_lcpp" | bc -l) )); then peak_lcpp=$curr_lcpp; fi
            
            echo "$peak_lms:$peak_ollama:$peak_lcpp" > "results/prov_peak_$AGENT_NAME.tmp"
            sleep 1
        done
    ) &
    PROV_MONITOR_PID=$!

    start_time=$(date +%s%N)
    
    # Ejecutamos usando /usr/bin/time -l para capturar RAM y CPU (macOS)
    /usr/bin/time -l opencode run $CONTINUE_FLAG \
        --agent "$AGENT_NAME" \
        --model "$MODEL_ID" \
        --dir "results" \
        "$MESSAGE" 2> "results/resource_$AGENT_NAME.log" | awk 'NR==1 { system("date +%s%N > .ttft_tmp") } { print }'
    
    end_time=$(date +%s%N)
    
    # Detener monitor silenciosamente
    kill $PROV_MONITOR_PID 2>/dev/null
    wait $PROV_MONITOR_PID 2>/dev/null
    
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
#MODEL="lmstudio/google/gemma-4-26b-a4b"
MODEL="lmstudio/Jackrong/Qwopus3.5-27B-v3-GGUF"
PROMPT_CONTENT=$(cat prompt.txt)

# PASO A: PLAN
run_benchmark "$MODEL" "plan" "$PROMPT_CONTENT" ""

# PASO B: BUILD
run_benchmark "$MODEL" "build" "Execute the plan" "--continue"

echo "Benchmark completado. Los archivos generados y las métricas están en /results"