"""
This python script provides interactive prompts for users to retry input if files are not found or if the image
information is not as expected.

Namely, the script:
    - allow users to specify paths for T2w and DWI images
    - validates file existence
    - checks for .bval and .bvec files for DWI image
    - provides information about the images' dimensions and pixel sizes

Author: Jan Valosek and Claude 3.5 Sonnet
"""
import os
import shutil
import argparse
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
    return parser.parse_args()


def get_valid_file_path(prompt):
    """
    Repeatedly prompt the user for a file path until a valid file is specified or the user aborts.

    Args:
    prompt (str): The input prompt to display to the user.

    Returns:
    str: The valid file path.
    """
    while True:
        file_path = input(prompt)
        # Get absolute path, expand user path
        file_path = os.path.abspath(os.path.expanduser(file_path))
        if os.path.isfile(file_path):
            return file_path
        print(f"Error: File does not exist: {file_path}"
              f"\nPlease try again.")


def print_image_info(file_path):
    """
    Print the dimensions and pixel size of the image at the given file path.

    Args:
    file_path (str): Path to the image file.
    """
    img = nib.load(file_path)
    zooms = img.header.get_zooms()
    print(f"Dimensions: {img.shape[0]} x {img.shape[1]} x {img.shape[2]}")
    print(f"Pixel size: {zooms[0]:.2f} mm x {zooms[1]:.2f} mm x {zooms[2]:.2f} mm")


def confirm_image_info(file_path):
    """
    Display the image dimensions and pixel size and ask the user to confirm if it's correct.

    Args:
    file_path (str): Path to the image file.

    Returns:
    bool: True if the user confirms the information, False otherwise.
    """
    while True:
        print_image_info(file_path)
        confirm = input("Do you agree with this image info? (y/n): ").lower()
        if confirm in ['y', 'yes', 'Y', 'YES']:
            return True
        elif confirm in ['n', 'no', 'N', 'NO']:
            return False
        else:
            print("Invalid input. Please enter 'y' or 'n'.")


def run_dcm2niix(dicom_folder, output_folder):
    """
    Run dcm2niix command to convert DICOM images to NIfTI format.

    Args:
    dicom_folder (str): Path to the folder containing DICOM images.
    output_folder (str): Path to the output folder for NIfTI images.

    Returns:
    tuple: Paths to the converted T2w and DWI NIfTI files.
    """
    # Create a temporary output folder to store dcm2niix output before renaming the files
    temp_folder = os.path.join(output_folder, "temp_dcm2niix")
    os.makedirs(temp_folder, exist_ok=True)

    cmd = [
        "dcm2niix",
        "-z", "y",          # Compress output
        "-f", "%f_%p_%s",   # Custom filename format: %f - folder name, %p - protocol name, %s - series number
        "-i", "y",          # Ignore derived, localizer and 2D images
        "-o", temp_folder,
        dicom_folder
    ]

    print("\nInfo: Starting DICOM to NIfTI conversion using dcm2niix.\n")

    os.system(" ".join(cmd))


def get_t2_image_path():
    """
    Get the path to the T2w image and check the image information.

    Returns:
    str: Valid T2w image path.
    """
    print(10*"-")
    print("T2w image")
    print(10*"-")
    # Get T2w image path
    while True:
        path_t2w = get_valid_file_path("Please specify the path to the T2w image: ")

        # If the image info is confirmed, return the image path
        if confirm_image_info(path_t2w):
            return path_t2w
        print("Let's try another T2w image.")


def get_dwi_image_path():
    """
    Get the path to the DWI image and check for the existence of bval and bvec files.

    Returns:
    str: Valid DWI image path.
    """
    print(10*"-")
    print("DWI image")
    print(10*"-")
    # Get DWI image path
    while True:
        # Ask the user for the DWI image path
        path_dwi = get_valid_file_path("Please specify the path to the DWI image: ")

        # Check for bval and bvec files
        dwi_base = path_dwi.replace('.nii', '').replace('.gz', '')
        bval_path = f"{dwi_base}.bval"
        bvec_path = f"{dwi_base}.bvec"

        # Check whether both bval and bvec files exist (we need them for DWI processing to compute DTI model)
        if not os.path.isfile(bval_path) or not os.path.isfile(bvec_path):
            print("Error: bval or bvec file is missing for the provided DWI image."
                  "\nPlease try another DWI image.")
            continue
        else:
            print("bval and bvec files found.")

        # If the image info is confirmed, return the image path
        if confirm_image_info(path_dwi):
            return path_dwi
        print("Let's try another DWI image.")


def copy_files_to_bids_folder(output_folder, participant_id, session_id, path_t2w, path_dwi):
    """
    Copy the converted nii images from the temporary folder to the output BIDS folder
    :param output_folder: temporary folder with the converted nii images
    :param participant_id: participant ID, e.g., sub-001
    :param session_id: session ID, e.g., ses-01
    :param path_t2w: path to the T2w image provided by the user
    :param path_dwi: path to the DWI image provided by the user
    """
    # First, create anat and dwi subfolders if they do not exist
    output_folder_anat = os.path.join(output_folder, "anat")
    os.makedirs(output_folder_anat, exist_ok=True)
    output_folder_dwi = os.path.join(output_folder, "dwi")
    os.makedirs(output_folder_dwi, exist_ok=True)

    # Second, move the images and JSON sidecars to the respective folders
    path_t2w_output = os.path.join(output_folder_anat, f"{participant_id}_{session_id}_T2w.nii.gz")
    path_dwi_output = os.path.join(output_folder_dwi, f"{participant_id}_{session_id}_dwi.nii.gz")
    shutil.copy(path_t2w, path_t2w_output)
    shutil.copy(path_t2w.replace('.nii.gz', '.json'), path_t2w_output.replace('.nii.gz', '.json'))
    # For DWI, we also need to copy the bval and bvec files
    shutil.copy(path_dwi, path_dwi_output)
    shutil.copy(path_dwi.replace('.nii.gz', '.json'), path_dwi_output.replace('.nii.gz', '.json'))
    shutil.copy(path_dwi.replace('.nii.gz', '.bval'), path_dwi_output.replace('.nii.gz', '.bval'))
    shutil.copy(path_dwi.replace('.nii.gz', '.bvec'), path_dwi_output.replace('.nii.gz', '.bvec'))

    # Lastly, remove the temporary folder
    shutil.rmtree(os.path.join(output_folder, "temp_dcm2niix"))


def main():
    """
    Main function
    """
    args = get_parser()

    dicom_folder = args.dicom_folder
    bids_folder = args.bids_folder
    participant_id = args.participant
    session_id = args.session

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

    # Run DICOM to NIfTI conversion using the dcm2niix command
    run_dcm2niix(dicom_folder, output_folder)

    print(100*"-")
    print("DICOM to NIfTI is done. Please review the images and provide paths to the T2w and DWI images.")
    print(100*"-")

    # Get the paths to the converted T2w and DWI images
    path_t2w = get_t2_image_path()
    path_dwi = get_dwi_image_path()

    # Copy the files to the BIDS folder
    copy_files_to_bids_folder(output_folder, participant_id, session_id, path_t2w, path_dwi)

    print("\nAll files have been successfully validated and confirmed.")


if __name__ == "__main__":
    main()