#!/usr/bin/env bash
set -euo pipefail
python train.py --epochs 5 --batch-size 128 --out-dir artifacts
python evaluate.py --weights artifacts/model.pt
