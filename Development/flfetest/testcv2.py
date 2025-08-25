import cv2
import os
import torchvision.transforms as transforms
import torch
import numpy as np

picpath = os.path.abspath(r"C:\Users\sofic\OneDrive\Documentos\Work\flfetest\fingerprintimage\black-and-white-fingerprint-logo-vector.jpg")

img = cv2.imread(picpath, flags=cv2.IMREAD_GRAYSCALE)
cv2.imshow("img", img)
cv2.waitKey(0)
cv2.destroyAllWindows()
print(img)
img2 = cv2.imread(r"C:\Users\sofic\OneDrive\Documentos\Work\flfetest\fingerprintimage\WIN_20250701_14_07_48_Pro.jpg", flags=cv2.IMREAD_GRAYSCALE)
cv2.imshow("img", img2)
cv2.waitKey(0)
cv2.destroyAllWindows()


transform = transforms.ToTensor()
tensor_image2 = transform(img2)
tensor_image1 = transform(img)
np_array = tensor_image1.numpy()

print(np_array)
print(f"fingerprint:{tensor_image1}")
print(f"Shape: {tensor_image1.shape}")
print(f"Dtype: {tensor_image1.dtype}")
print(f"Min/Max: {tensor_image1.min()}/{tensor_image1.max()}")
print(f"Mean: {tensor_image1.mean():.2f}")
print(f"my image:{tensor_image1}")