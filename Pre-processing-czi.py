# * Image Processing Script to process fish lines @ Baier Lab *
# Author: Keshav Prasad Gubbi
# DONE: Read CZI file from a given folder.
# DONE: Read metadata for each file and based on channel number split into separate channels.
# DONE: Save each channel as a separate tif/tiff file with correct channel name without permission errors.

import time
import nrrd
import numpy as np
import os
import cv2 as cv
import tifffile as tiff
from scipy import ndimage
from numpy import ndarray
from aicsimageio import AICSImage

start = time.time()

# Enter the exact/full path of the folder where images are located.
c_path = r"C:\Users\keshavgubbi\Desktop\LinesReg\210607_shhGFP_HuClyntagRFP"
original_path = c_path + r"\original"
line_path = original_path
processed_path = line_path + "/processed/"
processed_for_average_path = line_path + "/processed_for_average/"

if not os.path.exists(original_path):
    print(f"Creating {original_path}")
    os.makedirs(original_path, exist_ok=True)

ref_ch_num = int(input("Enter Reference Channel Number:"))


def _rotate(src, angle):
    # angle in degrees
    rotated_matrix = ndimage.rotate(src, angle=angle, reshape=False)
    return rotated_matrix


def image_to_nrrd(image, channel_name):
    Header = {'units': ['m', 'm', 'm'], 'spacings': [voxel_width, voxel_height, 1e-6]}
    image_name = f'{line_name}_{fish_number}_{channel_name}'
    print(f'Creating nrrd image with name : {image_name}.nrrd')
    return nrrd.write(os.path.join(processed_path, f"{image_name}.nrrd"), image, header=Header)


def image_to_tiff(image):
    print(f'Creating file {line_name}.tif')
    # metadata={'spacing': ['1./VoxelSizeList[0]', '1./VoxelSizeList[0]', '1'], 'unit': 'um',
    #                                   'axes ': 'ZYX', 'imagej': 'True'}
    return tiff.imwrite(os.path.join(processed_for_average_path, f"{line_name}.tif"), image)


def get_channel_name(f):
    name, ext = file.split(".")
    a, ref_ch_name = name.rsplit('_', 1)
    sig_ch_name, fish_num = a.rsplit('_', 1)
    return name, ref_ch_name, sig_ch_name, fish_num


def get_image_data(f):
    num_stacks, h, w = f.shape[3:]
    # Determine voxel spacing - x, y for use later while writing nrrd files to be of correct pixel spacing. This info
    # can be verified by in Fiji by [ image -> Properties]
    voxel_x, voxel_y, voxel_z = f.get_physical_pixel_size()[:3]  # read_voxel_size(first_channel_data)
    if voxel_z != 1e-6:
        # Warning to user if voxel depth is being reset to 1micron, to be compatible with zebrafish pipeline
        print(f"Unsuitable voxel depth Value: {voxel_z}. Will be reset to : 1e-6.")
    return num_stacks, h, w, voxel_x, voxel_y, voxel_z


def contrast_enhancement(f):
    alpha = 5.0  # Contrast control (1.0-3.0) but 3 is required for my purposes here
    beta = 1  # Brightness control (0-100). Not to be added beyond 5, to not hamper the signal with salt and pepper
    # noise.
    contrast_enhanced_image = cv.convertScaleAbs(f, alpha=alpha, beta=beta)
    return contrast_enhanced_image.astype('uint8')


if not os.path.exists(processed_path) or os.path.exists(processed_for_average_path):
    print(f"Creating {processed_path}")
    os.makedirs(processed_path, exist_ok=True)
    print(f"Creating {processed_for_average_path}")
    os.makedirs(processed_for_average_path, exist_ok=True)


for file in os.listdir(c_path):
    if file.endswith(".czi"):
        print(file)
        line_name, reference_channel_name, signal_channel_name, fish_number = get_channel_name(file)

        # Access the image data and obtain details (metadata) of the image
        c = AICSImage(os.path.join(c_path, file))
        N_stacks, height, width, voxel_width, voxel_height, voxel_depth = get_image_data(c)
        print("Height, Width of image stack:", height, ",", width, f"with {N_stacks} stacks!")
        print("Voxel Details (x, y, depth):", voxel_width, ",", voxel_height, ",", voxel_depth)

        # Obtain the image data from respective channels
        if ref_ch_num == 0:
            ref_channel_data = c.get_image_data("ZYX", C=0, S=0, T=0)
            sig_channel_data = c.get_image_data("ZYX", C=1, S=0, T=0)

        else:
            ref_channel_data = c.get_image_data("ZYX", C=1, S=0, T=0)
            sig_channel_data = c.get_image_data("ZYX", C=0, S=0, T=0)

        ##***********Creating image by stacking the 2D matrix into a 3D Array****##
        RImage: ndarray = np.stack(ref_channel_data).astype('uint8')
        SImage: ndarray = np.stack(sig_channel_data).astype('uint8')

        ##***********Contrast Enhancement*********************************##
        CE_image_R = contrast_enhancement(RImage)
        CE_image_S = contrast_enhancement(SImage)

        ##***********Rotation*********************************##
        print(f'Image stack to be rotated: {file}')

        theta = float(input('Enter the angle by which image to be rotated:'))
        Reference_image_Rotated = _rotate(CE_image_R, theta)
        Signal_image_Rotated = _rotate(CE_image_S, theta)

        # **********Final Saving of Images to respective folders********
        print("Final Saving of Images to respective folders!")
        Reference_nrrd_image: nrrd = image_to_nrrd(RImage, reference_channel_name)
        Reference_tiff_image: tiff = image_to_tiff(RImage)
        # Signal1_nrrd_image: nrrd = image_to_nrrd(1, S1Image, sig_ch1_name)

# for item in os.listdir(line_path):
#     if item.endswith(".tif") and re.search("ref", str(item)):
#         print(f"Image stack to be saved: {item}")
#         # Read the data back from file
#         readdata = tiff.imread(os.path.join(line_path, item))
#         name, fn = split_and_rename(item)
#
#         print(f"Creating {name}_{fn}_{reference_channel_name}.nrrd")
#         nrrd.write(os.path.join(processed_path, f"{name}_{fn}_{reference_channel_name}.nrrd"),readdata,index_order="C",)
#
#         print(f"Creating {name}_{fn}_{reference_channel_name}.tif")
#         with tiff.TiffWriter(os.path.join(processed_for_average_path, f"{name}_{fn}_{reference_channel_name}.tif"),imagej=True,) as tifw:
#             tifw.write(readdata.astype("uint8"),metadata={"spacing": 1.0, "unit": "um", "axes": "ZYX"},)
##################################################################################################
end = time.time()
t = end - start
print(f'Totally took {t}s')

# rotated_page_list = []
# rotated_image = tiff_unstackAndrestackForRotate(os.path.join(line_path, item))
# print(f'Creating Rotated Image: rotated_{item}')
# with tiff.TiffWriter(os.path.join(line_path, f"{item}"), imagej=True) as tifw:
#     tifw.write(rotated_image.astype('uint8'), metadata={'spacing': 1.0, 'unit': 'um', 'axes': 'ZYX'})


# def tiff_unstackAndrestackForRotate(f):
#     """
#     :param f: tiff file
#     :return: rotated_image_stack
#     #1. Iterate through each file as a tiff file.
#     #2. split into individual pages //Unstacking
#     #3. rotate each page and save the rotated_page into a new list
#     #4. restack each array from the list
#     """
#     with tiff.TiffFile(f, mode="r+b") as tif:
#         print(f" Processing {tif} for rotation...")
#         for page in tif.pages:
#             rotated_page = _rotate(page.asarray(), theta)
#             rotated_page_list.append(rotated_page)
#             rotated_image_stack = np.stack(rotated_page_list)
#     return rotated_image_stack.astype("uint8")


# #Contrast Enhancement Function
# alpha = 10.0 # Contrast control (1.0-3.0) but 5 is required for my purposes here
# beta = 5 # Brightness control (0-100). Not to be added beyond 5, to not hamper the signal with unnecesary salt and peper noise.
#
# def tiff_UnstackAndrestackForContrastEnhancement(f):
#     """
#     :param f: tiff file
#     :return: contrast_enhanced_image_stack
#     #1. Iterate through each file as a tiff file.
#     #2. Split into individual pages //Unstacking and convert each page into an 2D array
#     #3. Enhance Contrast for each page and save the contrast_enhanced_page
#     #3a. then pass through bilat filter to remove any residual salt and pepper noise
#     #4. Add each page into contrast_enhanced_list and stack the list
#     #5. Return the stack.
#     """
#     contrast_enhanced_list = []
#     with tiff.TiffFile(f, mode="r+b") as tif:
#         print(f" Processing {tif} for Enhancing Contrast...")
#         for page in tif.pages:
#             contrast_enhanced_page = cv.convertScaleAbs(page.asarray(), alpha=alpha, beta=beta)
#             #Adding a Bilat filter to reduce salt and pepper noise
#             contrast_enhanced_page= cv.bilateralFilter(contrast_enhanced_page, 9, 75, 75)
#             contrast_enhanced_list.append(contrast_enhanced_page)
#             contrast_enhanced_stack = np.stack(contrast_enhanced_list)
#     return contrast_enhanced_stack.astype("uint8")

# def split_and_rename(f):
#     filename, exte = f.split(".")
#     _first, _last = filename.split("_", 1)
#     fishnum, tag = _last.split("_", 1)
#     # print(_first, fishnum, ext)