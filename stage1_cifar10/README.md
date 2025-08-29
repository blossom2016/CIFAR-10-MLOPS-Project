# Stage 1 — CIFAR-10 Image Classifier (PyTorch)

This is a beginner-friendly starter project for **Stage 1** of your MLOps journey:
train a simple image classifier locally using **PyTorch** on the **CIFAR-10** dataset.

## 🚀 Quickstart

```bash
# 1) (Optional) create a virtualenv
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2) Install dependencies
pip install -r requirements.txt

# 3) Train (downloads CIFAR-10 automatically)
python train.py --epochs 5 --batch-size 128 --out-dir artifacts

# 4) Evaluate on the test set
python evaluate.py --weights artifacts/model.pt

# 5) See training curves and sample predictions
ls artifacts/
# -> accuracy.png, losses.png, preds_grid.png, model.pt, classes.txt
```

### Arguments

- `--epochs` (default: 5)  
- `--batch-size` (default: 128)  
- `--lr` learning rate (default: 3e-4)  
- `--data-dir` where CIFAR-10 will be stored (default: `./data`)  
- `--out-dir` where artifacts are saved (default: `./artifacts`)  
- `--model` backbone (default: `resnet18`)  
- `--pretrained` use ImageNet pretrained weights (default: True)  

## 📦 Files

- `train.py` – training loop and plots  
- `model.py` – model factory  
- `data.py` – dataset & transforms  
- `evaluate.py` – load weights and report test accuracy  
- `utils.py` – helpers (metrics, plots, seed)  
- `requirements.txt` – Python dependencies  
- `scripts/run_train.sh` – example training command  
- `tests/test_shapes.py` – quick unit test for sanity checks  

## ✅ What you’ll learn
- Loading a vision dataset with torchvision
- Transfer learning with ResNet-18
- Training loop (forward, loss, backward, step)
- Saving/loading model weights
- Plotting training curves and making prediction grids

---

When you're ready, we’ll move to **Stage 2** (wrapping the model with a FastAPI service).
