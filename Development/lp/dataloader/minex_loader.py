import os 
import numpy as np
import torch 
import torchvision.transforms.functional as VTF

from dataloader.helpers.functions import find_sizeMinex
from flx.data.image_loader import ImageLoader
from flx.data.dataset import Identifier

class MinexLoader(ImageLoader): 
    @staticmethod
    def _extension() -> str: 
        return ".gray"
    
    @staticmethod
    def _file_to_id_fun(subdir: str, filename: str) -> Identifier:
        SKIP_FILES = ['black', 'gradient', 'random_rects', 'white']
        print("filename: " + filename)
        if filename == "black": 
            print("stop here")
        if filename in SKIP_FILES:
            print("filename")
            return Identifier(-1, -1)
        if filename == "b050_10": 
            print("stop")
        name_without_ext = filename.replace('.gray', '')
        impression_char = name_without_ext[0]
        subject_str = name_without_ext[1:4]
        subject_id = int (subject_str)
        impression = 0 if impression_char == "a" else 1
        return Identifier(subject_id, impression)

    @staticmethod
    def _load_image(filepath: str) -> torch.Tensor: 
        with open(filepath, 'rb') as f: 
            raw_data = f.read()
            f_name = os.path.basename(f.name)
            f_name_t = f_name.split(".")[0]
            SKIP_FILES = ['black', 'gradient', 'random_rects', 'white']
            if f_name_t in SKIP_FILES:
                return torch.empty(0) 
            file_size = len(raw_data)
            print(f_name)      
            try: 
                width, height = find_sizeMinex(f_name)
                print(f_name)
            except: 
                raise ValueError(f"Cannot determine image dimensions for file size {file_size}, file name: {f_name}")

        # Convert to numpy array
        img_array = np.frombuffer(raw_data, dtype=np.uint8)
        img_array = img_array.reshape((height, width))
        # Convert to tensor and preprocess
        img_tensor = VTF.to_tensor(img_array)
        h, w = img_tensor.shape[1], img_tensor.shape[2]
        if h % 2 != 0:
            img_tensor = img_tensor[:, :-1, :]  
        if w % 2 != 0:
            img_tensor = img_tensor[:, :, :-1] 
        # Resize to DeepPrint input size (299x299)
        return img_tensor
    
