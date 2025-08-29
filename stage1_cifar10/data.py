from typing import Tuple
from torchvision import datasets, transforms
from torch.utils.data import DataLoader, random_split

def cifar10_loaders(data_dir: str = "./data", batch_size: int = 128, num_workers: int = 0, val_split: int = 5000) -> Tuple[DataLoader, DataLoader, DataLoader]:
    # Standard normalization for ImageNet-pretrained backbones
    mean = (0.485, 0.456, 0.406)
    std = (0.229, 0.224, 0.225)

    train_tfm = transforms.Compose([
        transforms.Resize(224),
        transforms.RandomCrop(224, padding=4),
        transforms.RandomHorizontalFlip(),
        transforms.ToTensor(),
        transforms.Normalize(mean, std),
    ])
    test_tfm = transforms.Compose([
        transforms.Resize(224),
        transforms.ToTensor(),
        transforms.Normalize(mean, std),
    ])

    train_full = datasets.CIFAR10(root=data_dir, train=True, download=True, transform=train_tfm)
    val_size = val_split
    train_size = len(train_full) - val_size
    train_set, val_set = random_split(train_full, [train_size, val_size])

    test_set = datasets.CIFAR10(root=data_dir, train=False, download=True, transform=test_tfm)

    train_loader = DataLoader(train_set, batch_size=batch_size, shuffle=True, num_workers=num_workers, pin_memory=False)
    val_loader = DataLoader(val_set, batch_size=batch_size, shuffle=False, num_workers=num_workers, pin_memory=False)
    test_loader = DataLoader(test_set, batch_size=batch_size, shuffle=False, num_workers=num_workers, pin_memory=False)

    return train_loader, val_loader, test_loader

def cifar10_classes() -> list:
    return ['airplane','automobile','bird','cat','deer','dog','frog','horse','ship','truck']
