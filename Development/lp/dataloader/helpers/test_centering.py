import cv2 
import numpy as np 

image = cv2.imread(r"C:\Users\sofic\OneDrive\Documentos\Work\Development\received_fingerprints\image_subject.png")
cv2.imshow("Initial Image", image)
orig_h, orig_w = image.shape[:2]
pad = 20  

padded = cv2.copyMakeBorder(
    image,
    top=pad, bottom=pad,
    left=pad, right=pad,
    borderType=cv2.BORDER_CONSTANT,
    value=[250,250,250]   # white padding; match your background
)
cv2.imshow("Padded", padded)
gray = cv2.cvtColor(padded, cv2.COLOR_BGR2GRAY)

#FIRST PART: ROTATION ------------------------------------------------------------------------
#first threshold
_, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY +cv2.THRESH_OTSU)
cv2.imshow("Binary 1", binary)

cv2.waitKey(0)
cv2.destroyAllWindows()

# draw countours
contours, hierarchy = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)

if len(contours) > 1:
    contours = contours[:-1]
cv2.drawContours(binary, contours, -1,(0,255,0), 6)
cv2.imshow("Countours Connected", binary)

# second  threshold, binary
_, binary = cv2.threshold(binary, 0, 255, cv2.THRESH_BINARY)
cv2.imshow("Binary 2", binary)

# first final countour
contours, hierarchy = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
if len(contours) > 1:
    contours = contours[:-1]
if len(contours) > 0:
    cnt = max(contours, key=cv2.contourArea)
    padded_copy = padded.copy()
    max_idx, max_cnt = max(
        enumerate(contours),
        key=lambda ic: cv2.contourArea(ic[1])
    )
    cv2.drawContours(padded_copy,contours, max_idx, (0, 255, 0), 2)
    cv2.imshow("Main Contour", padded_copy)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    print(len(contours))
    (h, w) = padded.shape[:2]
    cnt = max(contours, key=cv2.contourArea)
    if len(cnt) >= 5:
        ellipse = cv2.fitEllipse(cnt)
        (cx, cy), (MA, ma), phi = cv2.fitEllipse(cnt)
        print(f"Original angle{phi}")
        if phi > 90:
            # For angles > 90°, the correction needed is -(180 - phi)
            rotation_angle = -(180 - phi)
        else:
            # For angles < 90°, the correction needed is -phi
            rotation_angle = -phi
        vis = padded.copy()
        print(f"Adjusted rotation angle: {rotation_angle}")
        cv2.drawContours(vis, [cnt], -1, (0,128,255), 2)
        cv2.ellipse(vis, ellipse, (0,255,0), 2)
        cv2.imshow("Ellipse Fit", vis)
        rotate_center =  (w // 2, h // 2)
        M = cv2.getRotationMatrix2D((int(cx),int(cy)), rotation_angle, 1.0)
        rotated = cv2.warpAffine(
            padded, M, (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE
        )
        rotated_binary= cv2.warpAffine(
            binary, M, (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE
        )
        cv2.imshow("Rotated padded", rotated)
        cv2.imshow("Rotated Binary: ", rotated_binary)
    else:
        print("Contour has too few points to fit an ellipse.")
        rotated = padded.copy()
        rotated_binary = binary.copy()
else:
    print("No contours found.")
    rotated = padded.copy()
    rotated_binary = binary.copy()
    cv2.waitKey(0)
    cv2.destroyAllWindows()

#TAKE OUT WHITE EXCESS ------------------------------------------------------------------------------
rotated_binary_inv = cv2.bitwise_not(rotated_binary)
contours_rot, _ = cv2.findContours(rotated_binary_inv, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
if len(contours_rot) > 0:
    cnt_rot = max(contours_rot, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(cnt_rot)
    margin = 0
    x = max(0, x - margin)
    y = max(0, y - margin)
    w = min(rotated.shape[1] - x, w + 2 * margin)
    h = min(rotated.shape[0] - y, h + 2 * margin)
    result = rotated[y:y+h, x:x+w]
    
else:
    # Fallback to original cropping
    result = rotated[pad:pad+orig_h, pad:pad+orig_w]

cv2.imshow("Final Result:", result)
cv2.waitKey(0)
cv2.destroyAllWindows()

#draw countour per countur
# for i, cnt in enumerate(contours):
#     # Check for hierarchy to distinguish external from internal contours (needs more logic)
#     # Assuming the first contour found is an external contour
#     if hierarchy[0][i][3] == -1: # If it has no parent
#         cv2.drawContours(padded, [cnt], -1, (0, 255, 0), 2) # Green color for external
#     else:
#         cv2.drawContours(padded, [cnt], -1, (0, 0, 255), 2) # Red color for internal
#     print(f"countours:{i} - {len(cnt)}")
#     # cv2.imshow(f"countours {i}", padded)
#     # cv2.waitKey(0)
#     # cv2.destroyAllWindows()

# cv2.imshow("countours 2", padded)
# cv2.waitKey(0)
# cv2.destroyAllWindows()

#CENTERING ----------------------------------------
# contours, hierarchy = cv2.findContours(rotated_binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
# rotated_copy = rotated.copy()
# cv2.drawContours(rotated_copy,contours, 32, (0, 255, 0), 2)
# cv2.imshow("countours rotaded", rotated)
# hh, ww = padded.shape[:2]
# x,y,w,h = cv2.boundingRect(cnt)

# # recenter
# startx = (ww - w)//2
# starty = (hh - h)//2
# result = np.full_like(rotated, 255)
# result_binary = np.full_like(rotated, 255)
# result[starty:starty+h,startx:startx+w] = rotated[y:y+h,x:x+w]
# result_binary[starty:starty+h,startx:startx+w] = rotated_binary[y:y+h,x:x+w]

# # view result
# cv2.imshow("RESULT", result)
# cv2.waitKey(0)
# cv2.destroyAllWindows()


# Crop: rows [pad : pad+orig_h], cols [pad : pad+orig_w]
# final_cropped = result[pad : pad + orig_h, pad : pad + orig_w]
# final_binary_cropped = result_binary[pad : pad + orig_h, pad : pad + orig_w]
# cv2.imshow("Final", final_cropped)
# cv2.imshow("Original", image)
# cv2.waitKey(0)
# cv2.destroyAllWindows()
