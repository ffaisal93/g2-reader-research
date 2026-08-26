#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 4 ]]; then
  echo "usage: $0 QUESTION_ID GRAPH_MEMORY_DIR OUTPUT_DIR INPUT_JSONL" >&2
  exit 2
fi

question_id=$1
graph_memory_dir=$(realpath "$2")
output_dir=$(realpath -m "$3")
input_jsonl=$(realpath "$4")

lab_root=/mnt/maxtox-nfs-student/zff/g2-reader/g2_reader_lab
source_root=$lab_root/experiments/low_resource_content_graph/implementations/student_8b_behavior_preserving

if [[ ! -f "$graph_memory_dir/${question_id}_iter_1/memories.pkl" ]]; then
  echo "missing graph: $graph_memory_dir/${question_id}_iter_1/memories.pkl" >&2
  exit 1
fi
if [[ -e "$output_dir/local-qwen-vl_dag_rag_1.jsonl" ]]; then
  echo "refusing to overwrite completed output: $output_dir" >&2
  exit 1
fi

mkdir -p "$output_dir"

export G2_USE_LOCAL_RUNTIME=1
export G2_LAB_ROOT=$lab_root
export G2_LLM_BASE_URL=http://127.0.0.1:18000/v1
export G2_EMBED_BASE_URL=http://127.0.0.1:18001/v1
export G2_API_KEY=local
export G2_EMBED_API_KEY=local
export G2_CHAT_MODEL=local-qwen-vl
export G2_EMBED_MODEL=local-bge-m3
export G2_MEMORY_DIR=$graph_memory_dir
export G2_RANDOM_SEED=42
export PYTHONHASHSEED=42

cd "$source_root"
exec "$lab_root/.venv/bin/python" -u -m scripts.test_rag \
  --data_path "$input_jsonl" \
  --save_dir "$output_dir" \
  --model local-qwen-vl \
  --n_proc 1 \
  --debug \
  --use_dag \
  --top_k 5

