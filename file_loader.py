"""
Convert DICOM images to NIfTI format and identify images for further analysis.

Namely, the script:
    - run dcm2niix command to convert DICOM images to NIfTI format
    - prompts the user to select the images for further processing
    - validates file existence
    - checks for .bval and .bvec files for DWI image
    - provides information about the images' dimensions and pixel sizes

Requirements:
    - dcm2niix -- see the Installation section in the README.md file

Example usage:
    # Activate SCT conda environment (assuming that it contains dcm2niix)
    cd $SCT_DIR
    source ./python/etc/profile.d/conda.sh
    conda activate venv_sct

    # Run the script
    python ~/balgrist-sci/file_loader.py \
      -dicom-folder ~/data/experiments/balgrist-sci/source_data/dir_20231010 \
      -bids-folder ~/data/experiments/balgrist-sci/bids \
      -participant sub-001 \
      -session ses-01 \
      -contrasts T2w dwi

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

Author: Jan Valosek
AI assistance: Claude 3.5 Sonnet, ChatGPT-4o, and GitHub Copilot
"""
import os
import shutil
import argparse
import pandas as pd
import nibabel as nib
import logging
import time
import csv
from datetime import datetime


def get_parser():
    """
    Parse command-line arguments.

    Returns:
    argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Convert DICOM to NIfTI and identify images for the further analysis.",
        formatter_class=argparse.RawTextHelpFormatter
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
        help="MRI contrasts to use. Separate multiple contrasts with a space. Example: 'T2w dwi'\n"
             "To distinguish between two images of the same contrast with different orientation, use the 'acq' tag, "
             "for example: 'acq-axial_T2w acq-sag_T2w'",
        nargs='+',
        default=["T2w", "dwi"],
        required=False
    )
    parser.add_argument(
        "-age",
        help="Age of the subject at the time of the MRI scan. "
             "Example: 25. Default: n/a",
        default='n/a',
        required=False
    )
    parser.add_argument(
        "-sex",
        help="Sex of the subject. "
             "Example: M. Default: n/a",
        default='n/a',
        choices=['M', 'F', 'n/a'],
        required=False
    )
    parser.add_argument(
        "-debug",
        help="If used, the temporary folder with NIfTI images will NOT be removed.",
        action="store_true",
        default=False,
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

    dimensions = f"{img.shape[0]}×{img.shape[1]}×{img.shape[2]}"
    pixel_size = f"{zooms[0]:.2f}×{zooms[1]:.2f}×{zooms[2]:.2f}"

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
        "-f", "%d_%s",  # Custom filename format: %d - series description, %s - series number
        "-i", "y",      # Ignore derived, localizer and 2D images
        "-o", temp_folder,
        dicom_folder
    ]

    logging.info("\nInfo: Starting DICOM to NIfTI conversion using dcm2niix...\n")

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
        time.sleep(0.5)
        logging.info(f"Please specify the row number (from 0 to {len(nii_info_df)-1}) of the {contrast} "
                     f"image you want to use: ")
        user_input = input("")

        # Check for empty input
        if not user_input.strip():
            logging.info("Warning: Input cannot be empty. Please try again.")
            continue

        # Check for non-integer input
        try:
            row_number = int(user_input)
        except ValueError:
            logging.info("Warning: Invalid input. Please enter a valid row number.")
            continue

        if row_number < 0 or row_number >= len(nii_info_df):
            logging.info("Warning: Invalid image number. Please try again.")
            continue
        else:
            fname = nii_info_df.iloc[row_number]['File Name']
            if contrast == "dwi":
                if not validate_dwi_image(os.path.join(temp_folder, fname)):
                    continue

            logging.info(f"Selected {contrast} image: {fname}")
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
        logging.info("Warning: bval or bvec file is missing for the provided DWI image."
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

    # Check if there are any NIfTI files in the folder, if not, print error message and exit
    if not nii_files:
        logging.error("Error: No NIfTI files found in the temporary folder.")
        exit(1)

    # Sort nii files based on the series number (the last number in the file name before the .nii.gz extension)
    nii_files.sort(key=lambda x: int(x.split('_')[-1].split('.')[0]))

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
        'Pixel Size [mm]': pixel_sizes
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
    :return: Path to the copied image in the BIDS folder
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
    logging.info(f"Copying {fname} to {fname_output}")
    shutil.copy(fname, fname_output)
    shutil.copy(fname.replace('.nii.gz', '.json'), fname_output.replace('.nii.gz', '.json'))
    # For DWI, we also need to copy the bval and bvec files
    if contrast == "dwi":
        shutil.copy(fname.replace('.nii.gz', '.bval'), fname_output.replace('.nii.gz', '.bval'))
        shutil.copy(fname.replace('.nii.gz', '.bvec'), fname_output.replace('.nii.gz', '.bvec'))

    return fname_output


def write_participants_tsv(bids_folder, participant_id, session_id, source_id, age=None, sex=None):
    """
    Write a new entry into the participants.tsv file.

    :param bids_folder: Path to the BIDS folder
    :param participant_id: Participant ID (e.g., 'sub-001')
    :param session_id: Session ID (e.g., 'ses-01')
    :param source_id: Source ID (e.g., 'dir_20230711')
    :param age: Age of the participant (optional)
    :param sex: Sex of the participant (optional)
    """
    participants_file = os.path.join(bids_folder, 'participants.tsv')
    file_exists = os.path.isfile(participants_file)

    with open(participants_file, 'a', newline='') as tsvfile:
        writer = csv.writer(tsvfile, delimiter='\t')

        # Write header if file is new
        if not file_exists:
            writer.writerow(['participant_id', 'ses_id', 'source_id', 'age', 'sex'])
            logging.info(f"Created new participants.tsv file at {participants_file}")

        # Write participant data
        writer.writerow([
            participant_id,
            session_id,
            source_id,
            age if age is not None else 'n/a',
            sex if sex is not None else 'n/a'
        ])
        logging.info(f"Info: Added entry for {participant_id}/{session_id} to participants.tsv")

def print_script_finished():
    """
    Print a message that the script has finished successfully.
    """
    logging.info(100 * "-")
    logging.info(f'{os.path.abspath(__file__)} finished successfully.')
    logging.info(100 * "-")


def main():
    """
    Main function
    """
    args = get_parser()

    dicom_folder = os.path.abspath(os.path.expanduser(args.dicom_folder))
    bids_folder = os.path.abspath(os.path.expanduser(args.bids_folder))
    participant_id = args.participant
    session_id = args.session
    contrasts = args.contrasts

    # Configure logging
    log_directory = os.path.join(bids_folder, "logs")
    os.makedirs(log_directory, exist_ok=True)
    log_filename = f"dicom_to_nifti_{participant_id}_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    log_filepath = os.path.join(log_directory, log_filename)

    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s',
        handlers=[
            logging.FileHandler(log_filepath),
            logging.StreamHandler()  # This will maintain console output
        ]
    )

    logging.info(100*"-")
    logging.info(f'Starting DICOM to NIfTI conversion using the script: {os.path.abspath(__file__)}')
    logging.info(100*"-")
    logging.info(f'Dicom folder: {dicom_folder}')
    logging.info(f'BIDS folder: {bids_folder}')
    logging.info(f'Participant ID: {participant_id}')
    logging.info(f'Session ID: {session_id}')
    logging.info(f'MRI contrasts to use: {contrasts}')
    logging.info(f'Age: {args.age}')
    logging.info(f'Sex: {args.sex}')
    logging.info(100*"-")
    logging.info(f"Log file will be stored in: {log_filepath}")

    # Check if the folder with DICOMs exists
    if not os.path.isdir(dicom_folder):
        logging.error(f"Error: Provided folder with DICOM images does not exist: {dicom_folder}")
        exit(1)

    # Check whether the BIDS folder already exists, if so, ask user whether to overwrite it
    output_folder = os.path.join(bids_folder, participant_id, session_id)
    if os.path.isdir(output_folder):
        logging.info(f"Warning: BIDS folder for the provided participant and session already exists: {output_folder}")
        while True:
            user_input = input("Do you want to overwrite the existing folder? [yes/no]: ").lower()
            if user_input in ['y', 'yes']:
                logging.info("Overwriting the existing folder.")
                try:
                    shutil.rmtree(output_folder)
                    logging.info(f"Removed existing folder: {output_folder}")
                except Exception as e:
                    logging.error(f"Failed to remove existing folder: {e}")
                    raise
                break
            elif user_input in ['n', 'no']:
                logging.info("Skipping the DICOM to NIfTI conversion.")
                print_script_finished()
                return False
            else:
                logging.info("Warning: Invalid input. Please enter 'yes' or 'no'.")
    else:
        # Create the output folder if it does not exist
        os.makedirs(output_folder, exist_ok=True)
        logging.info(f"Converted NIfTI images will be stored in: {output_folder}")

    # Create a temporary folder to store dcm2niix output before renaming the files
    temp_folder = os.path.join(output_folder, "temp_dcm2niix")
    logging.info(f"Creating a temporary folder for DICOM to NIfTI conversion: {temp_folder}")
    os.makedirs(temp_folder, exist_ok=True)
    # Run DICOM to NIfTI conversion using the dcm2niix command
    run_dcm2niix(dicom_folder, temp_folder)

    logging.info(100*"-")
    logging.info("DICOM to NIfTI is done. Please review the images and select images for further processing.")
    logging.info(100*"-")

    nii_info_df = get_nii_info_dataframe(temp_folder)
    # Display the DataFrame
    pd.set_option('display.max_colwidth', None)
    logging.info(f'{nii_info_df}\n')
    # Sleep for 1 second to ensure that the pandas output is displayed before the user input
    time.sleep(1)

    # Select images intended for further processing
    images_to_use_dict = {}
    for contrast in contrasts:
        images_to_use_dict[contrast] = select_image(contrast, nii_info_df, temp_folder)

    # Copy the files to the BIDS folder
    images_bids_dict = dict()
    logging.info('')
    for contrast, fname in images_to_use_dict.items():
        image_bids = copy_files_to_bids_folder(contrast, fname, output_folder, participant_id, session_id)
        images_bids_dict[contrast] = image_bids

    if args.debug:
        logging.info(f"\nInfo: Temporary folder with NIfTI images is stored in: {temp_folder}")
    # Remove the temporary folder
    else:
        logging.info(f"\nInfo: Removing the temporary folder {temp_folder}")
        shutil.rmtree(temp_folder)

    logging.info(100*"-")
    logging.info("All files have been successfully converted and validated. You can find the images in the "
                 "BIDS folder:")
    logging.info(f"\t{output_folder}")
    logging.info(100*"-")

    # Add call to write_participants_tsv
    source_id = os.path.basename(os.path.normpath(dicom_folder))
    write_participants_tsv(bids_folder, participant_id, session_id, source_id, args.age, args.sex)

    print_script_finished()


if __name__ == "__main__":
    main()
