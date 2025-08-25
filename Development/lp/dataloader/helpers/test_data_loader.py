import os 
from lp.dataloader.helpers.functions import on_key
from flx.data.dataset import Dataset
from minex_loader import MinexLoader
import matplotlib.pyplot as plt 
from flx.extractor.fixed_length_extractor import get_DeepPrint_TexMinu, DeepPrintExtractor
from flx.models.torch_helpers import get_device

MINEX_PATH = r"C:\Users\sofic\OneDrive\Documentos\Work\Development\minex\minexiii\validation\validation_imagery_raw"
MODEL_PATH = r"fixed-length-fingerprint-extractors\models\best_model.pyt"
loader = MinexLoader(MINEX_PATH)
dataset = Dataset(loader, loader.ids)

print(f"Found {len(dataset)} fingerprint images")
print(f"Number of unique subjects (fingers): {dataset.num_subjects}")

for i in range(11):
    identifier = dataset.ids[i]
    image = dataset[i]
    if (image.numel() != 0): 

        print(f"\nImage {i}:")
        print(f"  Subject (finger): {identifier.subject}")
        print(f"  Impression: {identifier.impression}")
        print(f"Tensor shape: {image.shape}")
        print(f"Tensor dtype: {image.dtype}")
        print(f"Tensor min/max values: {image.min()}, {image.max()}")
        print(f"  Image shape: {image.shape}")
        print(f"  Value range: [{image.min():.3f}, {image.max():.3f}]")

        # Display image
        fig = plt.figure(figsize=(4, 4))
        fig.canvas.mpl_connect('key_press_event', on_key)
        plt.imshow(image.squeeze(), cmap='gray')
        plt.title(f"Subject {identifier.subject}, Impression {identifier.impression}")
        plt.show()
        plt.close()

#test creation of embeddings
# device = get_device()
# print(f"Using device: {device}")

# embedding_size = 512 
# extractor: DeepPrintExtractor = get_DeepPrint_TexMinu (8000, 256)
# extractor.load_best_models(MODEL_PATH)