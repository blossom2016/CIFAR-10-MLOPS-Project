import os, argparse, time
import torch
import torch.nn as nn
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR
from tqdm import tqdm
import mlflow
import mlflow.pytorch

from model import build_model
from data import cifar10_loaders, cifar10_classes
from utils import set_seed, accuracy_top1, plot_curves, save_pred_grid, denormalize

def train_one_epoch(model, loader, device, optimizer, loss_fn):
    model.train()
    running = 0.0
    for x, y in loader:
        x, y = x.to(device, non_blocking=True), y.to(device, non_blocking=True)
        optimizer.zero_grad(set_to_none=True)
        logits = model(x)
        loss = loss_fn(logits, y)
        loss.backward()
        optimizer.step()
        running += loss.item() * x.size(0)
    return running / len(loader.dataset)

@torch.no_grad()
def evaluate(model, loader, device, loss_fn):
    model.eval()
    running = 0.0
    correct = 0
    total = 0
    for x, y in loader:
        x, y = x.to(device, non_blocking=True), y.to(device, non_blocking=True)
        logits = model(x)
        loss = loss_fn(logits, y)
        running += loss.item() * x.size(0)
        correct += (logits.argmax(1) == y).sum().item()
        total += y.size(0)
    return running / len(loader.dataset), correct / total

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument('--epochs', type=int, default=5)
    ap.add_argument('--batch-size', type=int, default=128)
    ap.add_argument('--lr', type=float, default=3e-4)
    ap.add_argument('--data-dir', type=str, default='./data')
    ap.add_argument('--out-dir', type=str, default='./artifacts')
    ap.add_argument('--model', type=str, default='resnet18')
    ap.add_argument('--pretrained', type=lambda x: x.lower()=='true', default=True)
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--experiment-name', type=str, default='cifar10-training')
    ap.add_argument('--run-name', type=str, default=None)
    return ap.parse_args()

def main():
    args = parse_args()
    os.makedirs(args.out_dir, exist_ok=True)
    set_seed(args.seed)

    # Set up MLflow
    mlflow.set_experiment(args.experiment_name)
    
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f'Using device: {device}')

    train_loader, val_loader, test_loader = cifar10_loaders(args.data_dir, args.batch_size)
    classes = cifar10_classes()

    model = build_model(num_classes=len(classes), pretrained=args.pretrained).to(device)
    loss_fn = nn.CrossEntropyLoss()
    optimizer = AdamW(model.parameters(), lr=args.lr)
    scheduler = CosineAnnealingLR(optimizer, T_max=args.epochs)

    history = {'train_loss': [], 'val_loss': [], 'val_acc': []}
    best_acc = 0.0
    best_path = os.path.join(args.out_dir, 'model.pt')
    with open(os.path.join(args.out_dir, 'classes.txt'), 'w') as f:
        f.write('\n'.join(classes))

    # Start MLflow run
    with mlflow.start_run(run_name=args.run_name):
        # Log parameters
        mlflow.log_params({
            'epochs': args.epochs,
            'batch_size': args.batch_size,
            'learning_rate': args.lr,
            'model': args.model,
            'pretrained': args.pretrained,
            'seed': args.seed,
            'optimizer': 'AdamW',
            'scheduler': 'CosineAnnealingLR'
        })
        
        # Log model architecture
        mlflow.log_param('num_classes', len(classes))
        mlflow.log_param('device', device)

        for epoch in range(1, args.epochs + 1):
            start = time.time()
            tr_loss = train_one_epoch(model, train_loader, device, optimizer, loss_fn)
            val_loss, val_acc = evaluate(model, val_loader, device, loss_fn)
            scheduler.step()

            history['train_loss'].append(tr_loss)
            history['val_loss'].append(val_loss)
            history['val_acc'].append(val_acc)

            # Log metrics to MLflow
            mlflow.log_metrics({
                'train_loss': tr_loss,
                'val_loss': val_loss,
                'val_accuracy': val_acc,
                'epoch': epoch
            }, step=epoch)

            print(f'Epoch {epoch:02d}/{args.epochs} | train_loss={tr_loss:.4f} val_loss={val_loss:.4f} val_acc={val_acc*100:.2f}% | {time.time()-start:.1f}s')

            if val_acc > best_acc:
                best_acc = val_acc
                torch.save(model.state_dict(), best_path)

        # Reload best model
        model.load_state_dict(torch.load(best_path, map_location=device))

        # Final test accuracy
        test_loss, test_acc = evaluate(model, test_loader, device, loss_fn)
        print(f'Test accuracy: {test_acc*100:.2f}%')

        # Log final metrics
        mlflow.log_metrics({
            'test_loss': test_loss,
            'test_accuracy': test_acc,
            'best_val_accuracy': best_acc
        })

        # Plots
        plot_curves(history, os.path.join(args.out_dir,'losses.png'), os.path.join(args.out_dir,'accuracy.png'))

        # Sample predictions grid
        model.eval()
        x, y = next(iter(test_loader))
        x = x.to(device)
        logits = model(x)
        preds_idx = logits.argmax(1).cpu().tolist()
        preds = [classes[i] for i in preds_idx]
        x_denorm = denormalize(x[:32]).clamp(0,1).cpu()  # first 32 images
        save_pred_grid(x_denorm, preds[:32], os.path.join(args.out_dir, 'preds_grid.png'))

        # Log artifacts
        mlflow.log_artifact(best_path, "model")
        mlflow.log_artifact(os.path.join(args.out_dir, 'classes.txt'), "classes")
        mlflow.log_artifact(os.path.join(args.out_dir, 'losses.png'), "plots")
        mlflow.log_artifact(os.path.join(args.out_dir, 'accuracy.png'), "plots")
        mlflow.log_artifact(os.path.join(args.out_dir, 'preds_grid.png'), "plots")

        # Log the PyTorch model
        mlflow.pytorch.log_model(model, "pytorch_model", registered_model_name=f"{args.model}-cifar10")

if __name__ == '__main__':
    main()
