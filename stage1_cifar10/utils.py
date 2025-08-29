import random, torch, numpy as np, matplotlib.pyplot as plt
from typing import List, Tuple
from torchvision.utils import make_grid

def set_seed(seed: int = 42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)

def accuracy_top1(logits: torch.Tensor, targets: torch.Tensor) -> float:
    preds = torch.argmax(logits, dim=1)
    correct = (preds == targets).sum().item()
    return correct / targets.size(0)

def plot_curves(history: dict, out_losses: str, out_accs: str):
    # history = {'train_loss':[], 'val_loss':[], 'val_acc':[]}
    plt.figure()
    plt.plot(history['train_loss'], label='train_loss')
    plt.plot(history['val_loss'], label='val_loss')
    plt.legend()
    plt.xlabel('epoch')
    plt.ylabel('loss')
    plt.title('Loss Curves')
    plt.savefig(out_losses, bbox_inches='tight')
    plt.close()

    plt.figure()
    plt.plot(history['val_acc'], label='val_acc')
    plt.legend()
    plt.xlabel('epoch')
    plt.ylabel('accuracy')
    plt.title('Validation Accuracy')
    plt.savefig(out_accs, bbox_inches='tight')
    plt.close()

def save_pred_grid(images: torch.Tensor, preds: List[str], out_path: str, nrow: int = 8):
    # images: [B,3,H,W] tensor AFTER de-normalization
    grid = make_grid(images, nrow=nrow, padding=2)
    plt.figure(figsize=(12, 6))
    plt.imshow(grid.permute(1,2,0).cpu().numpy())
    plt.axis('off')
    plt.title('Sample Predictions: ' + ', '.join(preds[:nrow]))
    plt.savefig(out_path, bbox_inches='tight')
    plt.close()

def denormalize(imgs: torch.Tensor, mean=(0.485,0.456,0.406), std=(0.229,0.224,0.225)):
    mean = torch.tensor(mean).view(1,3,1,1).to(imgs.device)
    std = torch.tensor(std).view(1,3,1,1).to(imgs.device)
    return imgs * std + mean
