import torch
from torchvision import transforms
from PIL import Image
from model import build_model

# Create model architecture
model = build_model(num_classes=10, pretrained=False)

# Load trained weights
state_dict = torch.load("model.pt", map_location=torch.device('cpu'))
model.load_state_dict(state_dict)
model.eval()

# Prepare image
transform = transforms.Compose([
    transforms.Resize((32,32)),
    transforms.ToTensor()
])
img = Image.open("plane.jpg")
x = transform(img).unsqueeze(0)

# Predict
with torch.no_grad():
    pred = model(x)
print(pred.argmax(dim=1).item())
