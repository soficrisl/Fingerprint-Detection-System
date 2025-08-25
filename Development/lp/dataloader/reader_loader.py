import os 
import numpy as np
import torch 
import torchvision.transforms.functional as VTF
import cv2
from flx.data.image_loader import ImageLoader
from flx.data.dataset import Identifier

class ReaderLoader(ImageLoader): 
    @staticmethod
    def _extension() -> str: 
        return ".png"
    
    @staticmethod
    def _file_to_id_fun(subdir: str, filename: str) -> Identifier:
        impression = 0
        subject_id = 0
        return Identifier(subject_id, impression)

    @staticmethod
    def _load_image(filepath: str) -> torch.Tensor: 
        img = cv2.imread(filepath, flags=cv2.IMREAD_GRAYSCALE)
        img_tensor = VTF.to_tensor(img)
        h, w = img_tensor.shape[1], img_tensor.shape[2]
        if h % 2 != 0:
            img_tensor = img_tensor[:, :-1, :]  
        if w % 2 != 0:
            img_tensor = img_tensor[:, :, :-1] 
        return img_tensor
    
