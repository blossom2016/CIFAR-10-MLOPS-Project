import argparse, torch
from model import build_model
from data import cifar10_loaders, cifar10_classes
from utils import set_seed

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument('--weights', type=str, required=True, help='Path to model.pt')
    ap.add_argument('--data-dir', type=str, default='./data')
    ap.add_argument('--batch-size', type=int, default=256)
    return ap.parse_args()

@torch.no_grad()
def main():
    args = parse_args()
    set_seed(42)
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    _, _, test_loader = cifar10_loaders(args.data_dir, batch_size=args.batch_size)
    classes = cifar10_classes()
    model = build_model(num_classes=len(classes), pretrained=False).to(device)
    model.load_state_dict(torch.load(args.weights, map_location=device))
    model.eval()

    correct = 0
    total = 0
    for x, y in test_loader:
        x, y = x.to(device), y.to(device)
        logits = model(x)
        correct += (logits.argmax(1) == y).sum().item()
        total += y.size(0)
    print(f'Test accuracy: {correct/total*100:.2f}%')

if __name__ == '__main__':
    main()
