#!/usr/bin/env bash
#SBATCH --job-name=panda-eval-video-publish
#SBATCH --output=/cluster/scratch/jiaxia/logs/panda_eval_video_publish_%j.out
#SBATCH --error=/cluster/scratch/jiaxia/logs/panda_eval_video_publish_%j.err
#SBATCH --partition=cpupr.4h
#SBATCH --time=04:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem-per-cpu=4G
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=jiaxia@student.ethz.ch
#SBATCH --chdir=/cluster/scratch/jiaxia/panda_eval6062_video_publish

set -euo pipefail

module load eth_proxy

PYTHON=/cluster/project/rsl/jiaxia/miniconda3/bin/python
OUTPUT_ROOT=/cluster/scratch/jiaxia/panda_eval6062_video_publish
SCRIPT_ROOT=${OUTPUT_ROOT}/scripts
RUSTFS_ENV=/cluster/home/jiaxia/.config/panda_rustfs.env

mkdir -p /cluster/scratch/jiaxia/logs "${OUTPUT_ROOT}/staging"
source "${RUSTFS_ENV}"
export PYTHONPATH="/cluster/home/jiaxia/panda_data_processing:${PYTHONPATH:-}"

"${PYTHON}" "${SCRIPT_ROOT}/publish_panda_eval_videos.py" \
  --manifest "${OUTPUT_ROOT}/panda_eval_video_manifest.json" \
  --status-jsonl "${OUTPUT_ROOT}/status.jsonl" \
  --summary-output "${OUTPUT_ROOT}/summary.json" \
  --staging-root "${OUTPUT_ROOT}/staging" \
  --workers 8 \
  --crf 20
