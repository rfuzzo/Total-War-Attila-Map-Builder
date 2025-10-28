from PIL import Image
import numpy as np
import cv2

im = Image.open("main_attila_lookup.tga").convert("RGBA")
img = np.array(im)[:, :, ::-1].copy()  # convert RGBA→BGRA

print("Loaded TGA:", img.shape, img.dtype)

# quick check of unique colors
rgba = cv2.cvtColor(img, cv2.COLOR_BGRA2RGBA)
uniq = np.unique(rgba.reshape(-1,4), axis=0)
print("unique colors:", len(uniq))
