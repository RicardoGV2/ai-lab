#!/bin/bash
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE}")/.." && pwd)"
source "$ROOT_DIR/BRAIN/CONFIG.env"
mkdir -p .tmp
rm -f RUN.log

VERSION="v4.1-smart-memory"
START_TS=$(date "+%Y-%m-%d %H:%M:%S")

log_line() { echo -e "[$(date '+%H:%M:%S')] $1" | tee -a RUN.log; }

measure_ms() {
  python - << 'PYEOF' | tr -d '\r'
import subprocess, sys, time
best = 999999
for _ in range(3):
    t0 = time.perf_counter()
    res = subprocess.run([sys.executable, "verify.py"], capture_output=True)
    dt = int((time.perf_counter() - t0) * 1000)
    if res.returncode != 0:
        print(f"ERR:{dt}"); sys.exit(0)
    if dt < best: best = dt
print(f"OK:{best}")
PYEOF
}

cat << REPORT > REPORT.md
# 📊 Reporte Evolutivo Modular ($VERSION)
- **Inicio:** \`$START_TS\` | **Motor:** \`$MODEL_NAME\` | **Tarea:** \`$(basename "$PWD")\`

| Ciclo | Hora | Modo | Acción / Paper | Antes | Después | Estado | Principio (Chino) |
| :--- | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
REPORT

CYCLE=0
STAGNATION=0
cp target.py .tmp/best_target.py
log_line "🚀 Iniciando Motor Modular [$VERSION] en '$(basename "$PWD")' | Motor: $MODEL_NAME"

while true; do
  source "$ROOT_DIR/BRAIN/CONFIG.env"
  CYCLE=$((CYCLE + 1))
  NOW=$(date "+%H:%M:%S")
  log_line "\n===================================================="
  log_line "🌐 CICLO #$CYCLE | $VERSION | Motor: $MODEL_NAME | Estancamiento: $STAGNATION/2"
  log_line "===================================================="

  if [ $STAGNATION -ge 2 ]; then
    log_line "📚 [Auto-Research] Buscando papers nuevos en arXiv..."
    PAST_QUERIES=$(grep "### " "$ROOT_DIR/BRAIN/PAPERS_DIGEST.md" 2>/dev/null | tail -n 6)
    TOPIC=$(python "$ROOT_DIR/CORE/llm_call.py" "ARXIV_QUERY" "$MODEL_NAME" "$OLLAMA_HOST" "$OLLAMA_PORT" 60 "false" << PROMPT | tr -d '"' | tail -n 1
ALREADY SEARCHED (Do NOT repeat):
$PAST_QUERIES

Output ONLY a NEW 3-word computer science arXiv query about high-performance computing, memory efficiency, or string parsing (no quotes):
PROMPT
)
    log_line "🔎 Query arXiv: '$TOPIC'"
    python "$ROOT_DIR/CORE/arxiv_scout.py" "$TOPIC" > .tmp/arxiv_res.txt
    log_line "📄 Papers:\n$(cat .tmp/arxiv_res.txt)"
    echo -e "\n### [$START_TS $NOW] Query: $TOPIC\n$(cat .tmp/arxiv_res.txt)" >> "$ROOT_DIR/BRAIN/PAPERS_DIGEST.md"

    LESSON=$(python "$ROOT_DIR/CORE/llm_call.py" "ARXIV_DISTILL" "$MODEL_NAME" "$OLLAMA_HOST" "$OLLAMA_PORT" 120 "false" << PROMPT | tr '|' '/' | tail -n 1
Extract ONE general software performance or data-structure optimization principle from these abstracts in ONE brief Chinese sentence (under 30 chars, no anomaly detection fluff):
$(cat .tmp/arxiv_res.txt)
PROMPT
)
    echo "- [论文启发] $LESSON" >> "$ROOT_DIR/BRAIN/PRINCIPLES.md"
    echo "| #$CYCLE | $NOW | 📚 arXiv | $TOPIC | - | - | 🧠 LEARNED | $LESSON |" >> REPORT.md
    log_line "🧠 Aprendido de arXiv: $LESSON"
    STAGNATION=0
  fi

  BEFORE_RAW=$(measure_ms)
  BEFORE=${BEFORE_RAW#OK:}

  IDEA=$(python "$ROOT_DIR/CORE/llm_call.py" "RESEARCHER" "$MODEL_NAME" "$OLLAMA_HOST" "$OLLAMA_PORT" 120 "false" << PROMPT | tr '|' '/' | tail -n 1
PRINCIPLES:
$(cat "$ROOT_DIR/BRAIN/PRINCIPLES.md")

RECENT HISTORY (Do NOT repeat):
$(tail -n 10 REPORT.md)

CODE:
$(cat target.py)

Propose ONE new Python standard-library speed optimization in ONE brief Chinese phrase. Output ONLY that final phrase.
PROMPT
)
  log_line "💡 Hipótesis: $IDEA"

  python "$ROOT_DIR/CORE/llm_call.py" "CODER" "$MODEL_NAME" "$OLLAMA_HOST" "$OLLAMA_PORT" "$NUM_PREDICT" "false" << PROMPT > .tmp/coder_raw.txt
Apply ONLY this optimization: $IDEA
Strictly obey:
$(cat "$ROOT_DIR/BRAIN/PRINCIPLES.md")

Current code:
$(cat target.py)

Output ONLY complete Python code inside a \`\`\`python block.
PROMPT

  python - << 'PYEOF'
import re
out = open(".tmp/coder_raw.txt", encoding="utf-8").read()
m = re.search(r"```(?:python)?\s*(.*?)```", out, re.S)
if m: open("target.py", "w", encoding="utf-8").write(m.group(1).strip() + "\n")
PYEOF

  AFTER_RAW=$(measure_ms)

  if [[ "$AFTER_RAW" == OK:* ]]; then
    AFTER=${AFTER_RAW#OK:}
    if [ "$AFTER" -lt "$BEFORE" ]; then
      cp target.py .tmp/best_target.py
      echo "- [验证提速 ${BEFORE}ms->${AFTER}ms] $IDEA" >> "$ROOT_DIR/BRAIN/PRINCIPLES.md"
      echo "| #$CYCLE | $NOW | ⚡ Optimizar | target.py | ${BEFORE}ms | **${AFTER}ms** | ✅ KEPT | $IDEA |" >> REPORT.md
      log_line "🏆 NUEVO RÉCORD: ${BEFORE}ms -> ${AFTER}ms"
      STAGNATION=0
    else
      cp .tmp/best_target.py target.py
      echo "| #$CYCLE | $NOW | ⚡ Optimizar | target.py | ${BEFORE}ms | ${AFTER}ms | ❌ SLOWER | $IDEA |" >> REPORT.md
      log_line "➖ Sin mejora (${BEFORE}ms vs ${AFTER}ms)"
      STAGNATION=$((STAGNATION + 1))
    fi
  else
    AFTER=${AFTER_RAW#ERR:}
    cp .tmp/best_target.py target.py
    python verify.py > .tmp/err.txt 2>&1
    ERR=$(tail -n 2 .tmp/err.txt | tr '\n' ' ')
    echo "| #$CYCLE | $NOW | ⚡ Optimizar | target.py | ${BEFORE}ms | ${AFTER}ms | ❌ ERROR | $IDEA |" >> REPORT.md
    log_line "❌ REVERTIDO (${AFTER}ms) -> $ERR"
    STAGNATION=$((STAGNATION + 1))
  fi
  PRIN_CNT=$(grep -c "^-" "$ROOT_DIR/BRAIN/PRINCIPLES.md" 2>/dev/null || echo 0)
  log_line "📊 [HUD] Récord actual: ${BEFORE}ms -> ${AFTER}ms | Reglas en cerebro: ${PRIN_CNT}"
  { echo "## 🎯 REPORTE EN VIVO"; cat REPORT.md; echo ""; cat "$ROOT_DIR/BRAIN/PRINCIPLES.md"; } > .tmp/LATEST_CLIP.txt
  if [ $((CYCLE % 8)) -eq 0 ]; then
    log_line "🧹 [Auto-Compact] Podando reglas redundantes del cerebro..."
    python "$ROOT_DIR/CORE/compact_brain.py" | tee -a RUN.log
  fi
  sleep 2
done
