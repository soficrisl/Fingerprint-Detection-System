import os
import torch 
import torchvision.transforms.functional as VTF
import cv2
from flx.data.image_loader import ImageLoader
from flx.data.dataset import Identifier

class UareULoader(ImageLoader): 
    SUBJECT_FINGER_MAPPING = {
    ('012', '1'): 0,
    ('012', '10'): 1,
    ('012', '2'): 2,
    ('012', '3'): 3,
    ('012', '4'): 4,
    ('012', '5'): 5,
    ('012', '6'): 6,
    ('012', '7'): 7,
    ('012', '8'): 8,
    ('012', '9'): 9,
    ('013', '1'): 10,
    ('013', '10'): 11,
    ('013', '2'): 12,
    ('013', '3'): 13,
    ('013', '4'): 14,
    ('013', '5'): 15,
    ('013', '6'): 16,
    ('013', '7'): 17,
    ('013', '8'): 18,
    ('013', '9'): 19,
    ('017', '1'): 20,
    ('017', '10'): 21,
    ('017', '2'): 22,
    ('017', '3'): 23,
    ('017', '4'): 24,
    ('017', '5'): 25,
    ('017', '6'): 26,
    ('017', '7'): 27,
    ('017', '8'): 28,
    ('017', '9'): 29,
    ('022', '1'): 30,
    ('022', '10'): 31,
    ('022', '2'): 32,
    ('022', '3'): 33,
    ('022', '4'): 34,
    ('022', '5'): 35,
    ('022', '6'): 36,
    ('022', '7'): 37,
    ('022', '8'): 38,
    ('022', '9'): 39,
    ('027', '1'): 40,
    ('027', '10'): 41,
    ('027', '2'): 42,
    ('027', '3'): 43,
    ('027', '4'): 44,
    ('027', '5'): 45,
    ('027', '6'): 46,
    ('027', '7'): 47,
    ('027', '8'): 48,
    ('027', '9'): 49,
    ('057', '1'): 50,
    ('057', '2'): 51,
    ('057', '3'): 52,
    ('057', '4'): 53,
    ('057', '5'): 54,
    ('076', '1'): 55,
    ('076', '10'): 56,
    ('076', '2'): 57,
    ('076', '3'): 58,
    ('076', '4'): 59,
    ('076', '5'): 60,
    ('076', '6'): 61,
    ('076', '7'): 62,
    ('076', '8'): 63,
    ('076', '9'): 64,
}
    @staticmethod
    def _extension() -> str: 
        return ".tif"

    @staticmethod
    def _file_to_id_fun(subdir: str, filename: str) -> Identifier:
        name_without_ext = filename.replace('.tif', '')
        parts = name_without_ext.split("_")
        if len(parts) != 3:
            raise ValueError(f"Invalid filename format: {filename}")
        subject = parts[0]
        finger = parts[1]
        impression = int(parts[2])
        key = (subject, finger)
        if key not in UareULoader.SUBJECT_FINGER_MAPPING:
            raise KeyError(f"Unknown subject-finger combination: {key}")
        
        subject_id = UareULoader.SUBJECT_FINGER_MAPPING[key]
        
        return Identifier(subject_id, impression -1 )

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