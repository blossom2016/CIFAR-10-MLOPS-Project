import torch
from model import build_model

def test_forward_shape():
    model = build_model(num_classes=10, pretrained=False)
    model.eval()
    x = torch.randn(2,3,224,224)
    with torch.no_grad():
        y = model(x)
    assert y.shape == (2,10)
