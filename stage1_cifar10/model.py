import torch
import torch.nn as nn
from torchvision.models import resnet18, ResNet18_Weights

def build_model(num_classes: int = 10, pretrained: bool = True) -> nn.Module:
    weights = ResNet18_Weights.DEFAULT if pretrained else None
    model = resnet18(weights=weights)
    # Replace final layer to match CIFAR-10 classes
    in_features = model.fc.in_features
    model.fc = nn.Sequential(
        nn.Dropout(0.2),
        nn.Linear(in_features, num_classes)
    )
    return model
