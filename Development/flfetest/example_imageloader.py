import os
from flx.data.image_loader import ImageLoader
from flx.data.dataset import Identifier, IdentifierSet, Dataset
from flx.data.image_helpers import pad_and_resize_to_deepprint_input_size
import torch
import torchvision.transforms.functional as VTF
import PIL
from IPython.display import display

# # NOTE: If this does not work, enter the absolute path to the notebooks/example-dataset directory here! 
example_dataset_path = os.path.abspath(r"C:\Users\sofic\OneDrive\Documentos\Work\fixed-length-fingerprint-extractors\notebooks\example-dataset")
# list_files(example_dataset_path)

class ExampleImageLoader(ImageLoader):
    # We do not need to override the __init__ method. In case you need to do it, call
    # super().__init__(<my_root_dir>)
    # with the root dir of the image dataset inside your __init__ method.
    
    @staticmethod
    def _extension() -> str:
        return ".png"

    @staticmethod
    def _file_to_id_fun(subdir: str, filename: str) -> Identifier:
        # We can ignore the subdir
        # But the filename has the pattern: <subject>_<impression>.png
        subject_id, impression_id = filename.split("_")
        return Identifier(int(subject_id), int(impression_id))
        
    @staticmethod
    def _load_image(filepath: str) -> torch.Tensor:
        img = PIL.Image.open(filepath)
        img = PIL.ImageOps.grayscale(img)
        img_tensor=VTF.to_tensor(img)
        return pad_and_resize_to_deepprint_input_size(img_tensor, fill=1.0)


    
image_loader = ExampleImageLoader(example_dataset_path)
expected_ids = IdentifierSet([Identifier(i, j) for i in range(1, 11) for j in range(1, 11)])
assert image_loader.ids == expected_ids # Not all DataLoaders have an identifier set, but ImageLoaders always have

image_dataset = Dataset(image_loader, expected_ids)
print("result")
img = image_dataset[0]
print(img.shape)
