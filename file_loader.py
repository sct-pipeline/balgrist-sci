"""
Convert DICOM images to NIfTI format and identify images for the further analysis.

Namely, the script:
    - run dcm2niix command to convert DICOM images to NIfTI format
    - prompts the user to select the images for further processing
    - validates file existence
    - checks for .bval and .bvec files for DWI image
    - provides information about the images' dimensions and pixel sizes

Requirements:
    - dcm2niix -- see the Installation section in the README.md file

Input file structure:

    └── source_data
        └── dir_20231010
            ├── MRc.1.3.12.2.543543
            ├── ...
            └── SRe. 1.3.12.2.5432233

Output file structure:

    ├── bids
    │   └── sub-001
    │       └── ses-01
    │           ├── anat
    │           │   ├── sub-001_ses-01_T2w.json
    │           │   └── sub-001_ses-01_T2w.nii.gz
    │           └── dwi
    │               ├── sub-001_ses-01_dwi.bval
    │               ├── sub-001_ses-01_dwi.bvec
    │               ├── sub-001_ses-01_dwi.json
    │               └── sub-001_ses-01_dwi.nii.gz
    └── source_data
        └── dir_20231010
            ├── MRc.1.3.12.2.543543
            ├── ...
            └── SRe. 1.3.12.2.5432233

Author: Jan Valosek and Claude 3.5 Sonnet
"""

# TODO: write a new entry to the participant.tsv file based on the provided information (add sex and age args?)
# TODO: use logging instead of print statements


import os
import shutil
import argparse
import pandas as pd
import nibabel as nib


def get_parser():
    """
    Parse command-line arguments.

    Returns:
    argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Convert DICOM to NIfTI and identify images for the further analysis."
    )
    parser.add_argument(
        "-dicom-folder",
        help="Path to the folder containing DICOM images. "
             "Example: ~/sci-balgrist-study/sourcedata/dir_20230711",
        required=True
    )
    parser.add_argument(
        "-bids-folder",
        help="Path to the BIDS folder where the converted NIfTI images will be stored. "
             "Example: ~/sci-balgrist-study/bids",
        required=True
    )
    parser.add_argument(
        "-participant",
        help="Participant ID. Example: sub-001",
        required=True
    )
    parser.add_argument(
        "-session",
        help="Session ID. Example: ses-01",
        required=True
    )
    parser.add_argument(
        "-contrasts",
        help="MRI contrasts to use. Example: T2w dwi",
        nargs='+',
        default=["T2w", "dwi"],
        type=list,
        required=False
    )

    return parser.parse_args()


def get_image_info(file_path):
    """
    Get the dimensions and pixel size of the image at the given file path.

    :param file_path: Path to the image file
    """
    img = nib.load(file_path)
    zooms = img.header.get_zooms()

    dimensions = f"{img.shape[0]} x {img.shape[1]} x {img.shape[2]}"
    pixel_size = f"{zooms[0]:.2f} mm x {zooms[1]:.2f} mm x {zooms[2]:.2f} mm"

    return dimensions, pixel_size


def run_dcm2niix(dicom_folder, temp_folder):
    """
    Run dcm2niix command to convert DICOM images to NIfTI format.

    :param dicom_folder: Path to the folder containing DICOM images.
    :param temp_folder: Path to the temporary folder where the NIfTI images will be stored.
    """

    cmd = [
        "dcm2niix",
        "-z", "y",      # Compress output
        "-f", "%p_%s",  # Custom filename format: %p - protocol name, %s - series number
        "-i", "y",      # Ignore derived, localizer and 2D images
        "-o", temp_folder,
        dicom_folder
    ]

    print("\nInfo: Starting DICOM to NIfTI conversion using dcm2niix.\n")

    os.system(" ".join(cmd))


def select_image(contrast, nii_info_df, temp_folder):
    """
    Select an image from the list of images and return the selected image path.

    :param contrast: Contrast type, e.g., T2w, dwi
    :param nii_info_df: DataFrame with image information
    :param temp_folder: Path to the temporary folder with NIfTI images
    :return: Path to the selected image
    """
    # Ask the user to provide a row number (df index) corresponding to the image
    while True:
        row_number = int(input(f"Please specify the row number of the {contrast} image you want to use: "))
        if row_number < 0 or row_number >= len(nii_info_df):
            print("Error: Invalid image number. Please try again.")
            continue
        else:
            fname = nii_info_df.iloc[row_number]['File Name']
            if contrast == "dwi":
                if not validate_dwi_image(os.path.join(temp_folder, fname)):
                    continue

            print(f"Selected {contrast} image: {fname}")
            return os.path.join(temp_folder, fname)


def validate_dwi_image(fname):
    """
    Check the existence of bval and bvec files for the DWI image.

    :param fname: DWI image file name
    """

    # Check for bval and bvec files
    dwi_base = fname.replace('.nii', '').replace('.gz', '')
    fname_bval = f"{dwi_base}.bval"
    fname_bvec = f"{dwi_base}.bvec"

    # Check whether both bval and bvec files exist (we need them for DWI processing)
    if not os.path.isfile(fname_bval) or not os.path.isfile(fname_bvec):
        print("Error: bval or bvec file is missing for the provided DWI image."
              "\nPlease try another DWI image.")
        return False
    else:
        return True


def get_nii_info_dataframe(temp_folder):
    """
    Get the information about the NIfTI images in the temporary folder and store it in a DataFrame.

    :param temp_folder: Path to the temporary folder with NIfTI images
    :return: DataFrame with image information
    """
    # Get all nii files in the temporary folder
    nii_files = [f for f in os.listdir(temp_folder) if f.endswith('.nii.gz')]

    # Create lists to store the information
    file_names = []
    dimensions_list = []
    pixel_sizes = []

    # Collect information for each file
    for nii_file in nii_files:
        nii_path = os.path.join(temp_folder, nii_file)
        dimensions, pixel_size = get_image_info(nii_path)

        file_names.append(nii_file)
        dimensions_list.append(dimensions)
        pixel_sizes.append(pixel_size)

    # Create a DataFrame
    df = pd.DataFrame({
        'File Name': file_names,
        'Dimensions': dimensions_list,
        'Pixel Size': pixel_sizes
    })

    return df


def copy_files_to_bids_folder(contrast, fname, output_folder, participant_id, session_id):
    """
    Copy the converted nii image and its accompanying JSON sidecar from the temporary folder to the output BIDS folder.
    For DWI images, also copy the bval and bvec files.

    :param contrast: Contrast type, e.g., T2w, dwi
    :param fname: Path to the converted nii image in the temporary folder
    :param output_folder: temporary folder with the converted nii images
    :param participant_id: participant ID, e.g., sub-001
    :param session_id: session ID, e.g., ses-01
    """
    # First, create anat and dwi subfolders if they do not exist
    if contrast == "dwi":
        contrast_folder = "dwi"
    else:
        contrast_folder = "anat"
    output_folder = os.path.join(output_folder, contrast_folder)
    os.makedirs(output_folder, exist_ok=True)

    # Second, move the images and JSON sidecars to the respective folders
    fname_output = os.path.join(output_folder, f"{participant_id}_{session_id}_{contrast}.nii.gz")
    shutil.copy(fname, fname_output)
    shutil.copy(fname.replace('.nii.gz', '.json'), fname_output.replace('.nii.gz', '.json'))
    # For DWI, we also need to copy the bval and bvec files
    if contrast == "dwi":
        shutil.copy(fname.replace('.nii.gz', '.bval'), fname_output.replace('.nii.gz', '.bval'))
        shutil.copy(fname.replace('.nii.gz', '.bvec'), fname_output.replace('.nii.gz', '.bvec'))


def main():
    """
    Main function
    """
    args = get_parser()

    dicom_folder = os.path.expanduser(args.dicom_folder)
    bids_folder = os.path.expanduser(args.bids_folder)
    participant_id = args.participant
    session_id = args.session
    contrasts = args.contrasts

    print(100*"-")
    print(f'Dicom folder: {dicom_folder}')
    print(f'BIDS folder: {bids_folder}')
    print(f'Participant ID: {participant_id}')
    print(f'Session ID: {session_id}')
    print(100*"-")

    # Check if the folder with DICOMs exists
    if not os.path.isdir(dicom_folder):
        print(f"Error: Provided folder with DICOM images does not exist: {dicom_folder}")
        exit(1)

    # Check whether the BIDS folder already exists, if so, warn the user and exit
    output_folder = os.path.join(bids_folder, participant_id, session_id)
    if os.path.isdir(output_folder):
        print(f"Error: BIDS folder for the provided participant and session already exists: {output_folder}"
              f"\nPlease remove the existing BIDS folder and rerun the script.")
        exit(1)
    else:
        # Create the output folder if it does not exist
        os.makedirs(output_folder, exist_ok=True)
        print(f"\nInfo: Converted NIfTI images will be stored in: {output_folder}")

    # Create a temporary folder to store dcm2niix output before renaming the files
    temp_folder = os.path.join(output_folder, "temp_dcm2niix")
    print(f"\nInfo: Creating a temporary folder for NIfTI images: {temp_folder}")
    os.makedirs(temp_folder, exist_ok=True)
    # Run DICOM to NIfTI conversion using the dcm2niix command
    run_dcm2niix(dicom_folder, temp_folder)

    print(100*"-")
    print("DICOM to NIfTI is done. Please review the images and select images for further processing.")
    print(100*"-")

    nii_info_df = get_nii_info_dataframe(temp_folder)
    # Display the DataFrame
    print(f'{nii_info_df}\n')

    # Select images intended for further processing
    images_to_use_dict = {}
    for contrast in contrasts:
        images_to_use_dict[contrast] = select_image(contrast, nii_info_df, temp_folder)

    # Copy the files to the BIDS folder
    for contrast, fname in images_to_use_dict.items():
        print(f"Copying {contrast} image to the BIDS folder.")
        copy_files_to_bids_folder(contrast, fname, output_folder, participant_id, session_id)

    # Lastly, remove the temporary folder
    print("\nInfo: Removing the temporary folder {temp_folder}")
    shutil.rmtree(os.path.join(output_folder, "temp_dcm2niix"))

    print(100*"-")
    print("All files have been successfully converted and validated. You can find the following images in the "
          "BIDS folder:")
    print(f"\t{output_folder}")
    print(100*"-")


if __name__ == "__main__":
    main()
