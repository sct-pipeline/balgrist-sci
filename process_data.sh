#!/bin/bash
#
# Process spinal cord MRI data
#
# Steps:
#   1. Convert DICOM files to NIfTI format
#   2. Run spinal cord analysis
#
# Requirements:
#   - SCT (Spinal Cord Toolbox)
#   - dcm2niix
#   - FSLeyes
#
# Usage:
#   1. Activate the SCT conda environment:
#       source ${SCT_DIR}/python/etc/profile.d/conda.sh
#       conda activate venv_sct
#
#   2. Example usage:
#       bash process_data.sh \
#        -d ~/data/experiments/balgrist-sci/source_data/dir_20231010 \
#        -b ~/data/experiments/balgrist-sci/bids \
#        -r ~/data/experiments/balgrist-sci/data_processed \
#        -p sub-001 \
#        -s ses-01 \
#        -c acq-ax_T2w acq-sag_T2w \
#        -a 30 \
#        -x M
#
# Authors: Jan Valosek, Sandrine Bedard
# AI assistance: Claude 3.5 Sonnet, ChatGPT-4o, and GitHub Copilot
#

SCRIPT_NAME=$(basename "${0}")

# Immediately exit if error
set -e -o pipefail

# Exit if user presses CTRL+C (Linux) or CMD+C (OSX)
trap "echo Caught Keyboard Interrupt within script. Exiting now.; exit" INT

usage()
{
cat << EOF

DESCRIPTION
  Run spinal cord analysis.
  Requires that SCT, dcm2niix, and FSLeyes to be installed.

USAGE
  ${SCRIPT_NAME} -d <dicom folder> -b <bids folder> -r <results folder> -p <participant id> -s <session id> -c <contrasts> [-age <age> -sex <sex>]

MANDATORY ARGUMENTS
  -d <dicom folder>           Path to the folder containing DICOM images. Example: ~/sci-balgrist-study/sourcedata/dir_20230711
  -b <bids folder>            Path to the BIDS folder where the converted NIfTI images will be stored. Example: ~/sci-balgrist-study/bids
  -r <results folder>         Path to the folder where the results will be stored. Example: ~/sci-balgrist-study/data_processed
  -p <participant id>         Participant ID. Example: sub-001
  -s <session id>             Session ID. Example: ses-01
  -c <contrasts>              MRI contrasts to use (space-separated if multiple). Examples: 'acq-sag_T2w' and/or 'acq-ax_T2w'

OPTIONAL ARGUMENTS
  -a <age>                  Age of the subject at the time of the MRI scan. The provided value will be stored to participants.tsv file. Example: 25. Default: n/a
  -x <sex>                  Sex of the subject. The provided value will be stored to participants.tsv file. Example: M. Default: n/a
EOF
}


main()
{
    # Get the directory of the current script
    get_repo_dir

    echo_with_linebreaks "Starting the main analysis using the script: ${REPO_DIR}/${SCRIPT_NAME}"

    # Activate the SCT conda environment with dcm2niix installed
    activate_env

    check_dependencies
    convert_dcm2nii
    main_analysis

    conda deactivate
    echo_with_linebreaks "${REPO_DIR}/${SCRIPT_NAME} finished successfully."
}

# Get the directory of the current script
get_repo_dir()
{
    REPO_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
}

# Activate the SCT conda environment with dcm2niix installed
activate_env()
{
    CURRENT_DIR=$(pwd)
    cd "$SCT_DIR" || exit
    source ./python/etc/profile.d/conda.sh
    conda activate venv_sct
    cd "$CURRENT_DIR" || exit
}

# Check if the necessary dependencies are installed
check_dependencies()
{
    # List of commands to check
    commands=("dcm2niix" "sct_check_dependencies" "fsleyes")

    echo "Checking dependencies..."

    # Loop through each command and check if it is installed and callable
    for cmd in "${commands[@]}"; do
        if ! command -v $cmd &> /dev/null; then
            echo "$cmd could not be found. Please install it before running this script. Exiting..."
            exit 1
        else
            echo "[OK] $cmd"
        fi
    done
}

# Echo a message with line breaks before and after
echo_with_linebreaks()
{
    local message=$1
    local line=$(printf -- '-%.0s' {1..100})
    echo "${line}"
    echo -e "${message}"
    echo "${line}"
}

echo_fsleyes_instructions()
{
    echo_with_linebreaks "Opening FSLeyes, it might take a few seconds...\nCheck the quality of the segmentation, correct the segmentation if necessary ('Tools' --> 'Edit mode'),\nand save it by overwriting the existing file ('Overlay' --> 'Save' --> 'Overwrite').\nThen close FSLeyes to continue."
}

# Convert DICOM files to NIfTI format using the file_loader.py script, which calls the dcm2niix function
convert_dcm2nii()
{
    # Call the file_loader.py script to convert DICOM files to NIfTI format
    # TODO: redirect the output to LOG file to do not clutter the users terminal
    python "${REPO_DIR}"/file_loader.py -dicom-folder "$dicom_folder" -bids-folder "$bids_folder" -participant "$participant_id" -session "$session_id" -contrasts "${contrasts[@]}" -age "$age" -sex "$sex"
}

# Create the results folder (specified by the '-r' arg) and copy the NIfTI images from bids folder (specified by
# the '-b' arg) to it
# Also, create a folder under derivatives/labels for the current subject to store visually verified segmentations
create_results_folder_and_copy_images()
{
    # Create data_processed folder if it does not exist to store the analysis results
    if [ ! -d "$results_folder" ]; then
        mkdir -p "$results_folder"
    fi

    # Create a folder under derivatives/labels for the current subject to store visually verified segmentations
    if [ ! -d "${bids_folder}"/derivatives/labels/"$participant_id"/"$session_id"/anat/ ]; then
        mkdir -p "${bids_folder}"/derivatives/labels/"$participant_id"/"$session_id"/anat/
    fi

    # Go to folder where data will be copied and processed
    cd "$results_folder"
    # Copy source images
    mkdir -p "$participant_id"
    cp -r "$bids_folder/$participant_id/$session_id" "$participant_id/"
    # Note: We need to create "$participant_id" first, to preserve the directory structure (e.g., sub-001/ses-01) when
    # copying the files. Otherwise, only ses-01 folder would be copied to the results folder.
}

# Inspiration: https://github.com/spinalcordtoolbox/sct_tutorial_data/blob/master/multi_subject/process_data.sh#L66-L89
segment_if_does_not_exist() {
  ###
  #  This function checks if a manual spinal cord segmentation file already exists, then:
  #    - If it does, copy it locally.
  #    - If it doesn't, perform automatic spinal cord segmentation.
  #  This allows you to add manual segmentations on a subject-by-subject basis without disrupting the pipeline.
  ###
  local file="${1}"
  local contrast="${2}"
  # Update global variable with segmentation file name
  FILESEG="${file}"_label-SC_seg
  FILESEGMANUAL="${bids_folder}"/derivatives/labels/"${SUBJECT}"/anat/"${FILESEG}"
  echo
  echo "Looking for manual segmentation: ${FILESEGMANUAL}.nii.gz"
  if [[ -e "${FILESEGMANUAL}".nii.gz ]]; then
    echo "Found! Using manual segmentation."
    cp "${FILESEGMANUAL}".nii.gz "${FILESEG}".nii.gz
    cp "${FILESEGMANUAL}".json "${FILESEG}".json
    sct_qc -i "${file}".nii.gz -s "${FILESEG}".nii.gz -p sct_deepseg_sc -qc "${PATH_QC}" -qc-subject "${SUBJECT}"
  else
    echo "Not found. Proceeding with automatic segmentation."
    # Segment spinal cord
    sct_deepseg spinalcord -i "${file}".nii.gz -o "${FILESEG}".nii.gz -qc "${PATH_QC}" -qc-subject "${SUBJECT}"

    # Open FSLeyes to visualize the segmentation
    echo_fsleyes_instructions
    fsleyes "$file_t2".nii.gz "${FILESEG}.nii.gz" -cm red -a 70.0
    # Copy the visually verified segmentation (and potentially manually corrected SC seg) to the derivatives folder
    # (to be reused in the future analysis)
    cp "${FILESEG}".nii.gz "${FILESEGMANUAL}".nii.gz
    # TODO: add an entry who QCed and corrected the segmentation to the JSON sidecar
    cp "${FILESEG}".json "${FILESEGMANUAL}".json

    echo_with_linebreaks "Spinal cord segmentation saved as:\n\t"${FILESEGMANUAL}".nii.gz\n"

  fi
}

label_if_does_not_exist(){
  ###
  #  This function checks if a manual disc label file already exists, then:
  #     - If it does, copy it locally.
  #     - If it doesn't, perform automatic labeling.
  #   Then, the function generates a labeled segmentation using the disc labels.
  #   This allows you to add manual labels on a subject-by-subject basis without disrupting the pipeline.
  ###
  local file="$1"
  local file_seg="$2"
  local contrast="$3"    # acq-sag_T2w or acq-ax_T2w
  # Copy manual disc labels from derivatives/labels if they exist
  FILELABEL="${file}_label-disc"
  FILELABELMANUAL="${bids_folder}/derivatives/labels/${SUBJECT}/anat/${FILELABEL}"
  echo "Looking for manual disc labels: ${FILELABELMANUAL}.nii.gz"
  if [[ -e ${FILELABELMANUAL}.nii.gz ]]; then
    echo "Found! Using manual disc labels."
    cp $FILELABELMANUAL.nii.gz ${FILELABEL}.nii.gz
    # cp "${FILELABELMANUAL}".json "${FILELABEL}".json  # TODO: uncomment once we have a JSON sidecar for disc labels
    # Generate labeled segmentation from manual disc labels
    sct_label_vertebrae -i ${file}.nii.gz -s ${file_seg}.nii.gz -discfile ${FILELABEL}.nii.gz -c t2 -qc ${PATH_QC} -qc-subject ${SUBJECT}
  else
    echo "Not found. Proceeding with automatic labeling."
    # Automatically label discs and generate labeled segmentation
    sct_label_vertebrae -i ${file}.nii.gz -s ${file_seg}.nii.gz -c t2 -qc ${PATH_QC} -qc-subject ${SUBJECT}
    mv ${file_seg}_labeled_discs.nii.gz ${FILELABEL}.nii.gz
    # Create disc labels QC
    sct_qc -i ${file}.nii.gz -s ${FILELABEL}.nii.gz -p sct_label_utils -qc ${PATH_QC} -qc-subject "${SUBJECT}"

    # Open QC
    echo_with_linebreaks "Opening quality control report for disc labels in in your browser.\nIn the report, navigate to the disc labels ('sct_label_utils' in the 'Function' column) and assess the quality of the labels.\nAre the disc labels correct? (y/n)"
    open ${PATH_QC}/index.html
    # Read user input
    read -r answer
    while true; do
      if [[ $answer == "y" ]]; then
        echo "Copying disc labels to the derivatives folder..."
        cp ${FILELABEL}.nii.gz ${FILELABELMANUAL}.nii.gz
        # TODO: add an entry who QCed (and corrected) the disc labels to the JSON sidecar
        cp ${FILELABEL}.json ${FILELABELMANUAL}.json
        break
      elif [[ $answer == "n" ]]; then
        echo "Please manually label the discs."
        message="Click at the posterior tip of the discs. Then click 'Save and Quit'."
        # TODO: do we want to use '-ilabel' to open automatic labels (which might be wrong) in the viewer? Or is it better
        #  to label from scratch?
        sct_label_utils -i ${file}.nii.gz -create-viewer 1:12 -o ${FILELABEL}.nii.gz -msg message
        cp ${FILELABEL}.nii.gz ${FILELABELMANUAL}.nii.gz
        # TODO: create a JSON sidecar with the information about the user who created the labels
        # TODO: manual disc labels are located at the posterior tip of the discs. Do we want to bring them to the spinal
        #  cord centerline to be consistent with the automatic labels (`${file_seg}_labeled_discs.nii.gz`)?
        break
      else
        echo "Invalid input. Please enter 'y' (yes) or 'n' (no):"
        read -r answer
      fi
    done
    echo_with_linebreaks "Disc labels saved as:\n\t"${FILELABELMANUAL}".nii.gz"
  fi

}

bring_sag_disc_lables_to_ax()
{
  ###
  # This function brings the T2w sagittal disc labels to the T2w axial space:
  #     - Bring T2w sagittal image to T2w axial image to obtain warping field.
  #     - This warping field will be used to bring the T2w sagittal disc labels to the T2w axial space.
  #     - Generate QC report to assess warped disc labels.
  #     - Label T2w axial spinal cord segmentation using the disc labels.
  # Context: https://github.com/sct-pipeline/dcm-metric-normalization/issues/9
  # Inspired by: https://github.com/sct-pipeline/dcm-metric-normalization/blob/r20250320/scripts/process_data_dcm-zurich.sh#L155-L176
  local file_t2_ax="$1"
  local file_t2_ax_seg="$2"
  local file_t2_sag="${file_t2_ax/-ax/-sag}"    # TODO: this is very fragile, we should use a more robust way to
  local file_t2_sag_seg="${file_t2_ax_seg/-ax/-sag}"    # TODO: this is very fragile, we should use a more robust way to

  # Note: the '-dseg' is used only for the QC report
  sct_register_multimodal -i ${file_t2_sag}.nii.gz -d ${file_t2_ax}.nii.gz -identity 1 -x nn -qc ${PATH_QC} -qc-subject ${SUBJECT} -dseg ${file_t2_ax_seg}.nii.gz
  # Bring T2w sagittal disc labels (located in the middle of the spinal cord) to T2w axial space
  # Context: https://github.com/sct-pipeline/dcm-metric-normalization/issues/10
  sct_apply_transfo -i ${file_t2_sag_seg}_labeled_discs.nii.gz -d ${file_t2_ax}.nii.gz -w warp_${file_t2_sag}2${file_t2_ax}.nii.gz -x label
  # Generate QC report to assess warped disc labels
  sct_qc -i ${file_t2_ax}.nii.gz -s ${file_t2_sag_seg}_labeled_discs_reg.nii.gz -p sct_label_utils -qc ${PATH_QC} -qc-subject ${SUBJECT}

  file_t2_ax_labels=${file_t2_sag_seg}_labeled_discs_reg

  # Label T2w axial spinal cord segmentation. Either using manual disc labels or using disc labels from sagittal image.
  # Note: here we use sct_label_utils instead of sct_label_vertebrae to avoid SC straightening
  # Context: https://github.com/spinalcordtoolbox/spinalcordtoolbox/pull/4072
  sct_label_utils -i ${file_t2_ax_seg}.nii.gz -disc ${file_t2_ax_labels}.nii.gz -o ${file_t2_ax_seg}_labeled.nii.gz
  # Generate QC report to assess labeled segmentation
  sct_qc -i ${file_t2_ax}.nii.gz -s ${file_t2_ax_seg}_labeled.nii.gz -p sct_label_vertebrae -qc ${PATH_QC} -qc-subject ${SUBJECT}

}

process_t2w_sag()
{
    local contrast=$1
    # Go to anat folder where all structural data are located
    cd anat

    # Construct the file name based on the subject ID, e.g., sub-001_ses-01_acq-sag_T2w
    file_t2="${participant_id}_${session_id}_${contrast}"

    # Segment spinal cord (only if it does not exist)
    # TODO: redirect sct_deepseg_sc output to LOG file to do not clutter the users terminal
    segment_if_does_not_exist "$file_t2" t2
    file_t2_seg="${FILESEG}"
    label_if_does_not_exist "$file_t2" "$file_t2_seg" acq-sag

    # Go back to the subject root folder
    cd ..
}

process_t2w_ax()
{
    local contrast=$1
    # Go to anat folder where all structural data are located
    cd anat

    # Construct the file name based on the subject ID, e.g., sub-001_ses-01_acq-ax_T2w
    file_t2="${participant_id}_${session_id}_${contrast}"

    # Segment spinal cord (only if it does not exist)
    # TODO: redirect sct_deepseg_sc output to LOG file to do not clutter the users terminal
    segment_if_does_not_exist "$file_t2" t2
    file_t2_seg="${FILESEG}"

    bring_sag_disc_lables_to_ax "${file_t2}" "${file_t2_seg}"

    # Go back to the subject root folder
    cd ..
}

main_analysis()
{
    # Create the results folder and copy the images to it
    create_results_folder_and_copy_images

    # Define path to the folder where QC will be stored
    PATH_QC="${results_folder}"/qc
    SUBJECT="${participant_id}/${session_id}"
    # TODO: add a path for log files

    # Go to subject folder in the results folder
    cd "${SUBJECT}"

    # Loop across contrasts (specified by the '-c' arg)
    # TODO: the order the contrasts are processed is determined by the order they are specified in the command line
    for contrast in "${contrasts[@]}"; do
        case $contrast in
            acq-sag_T2w)
                echo_with_linebreaks "Processing T2w sagittal image..."
                process_t2w_sag $contrast
                ;;
            acq-ax_T2w)
                echo_with_linebreaks "Processing T2w axial image..."
                process_t2w_ax $contrast
                ;;
            *)
                echo "Analysis for $contrast is not implemented yet :-(. Skipping..."
#                echo "Unknown contrast: $contrast"
                ;;
        esac
    done
}

# Print usage if no arguments are provided
if [ ! ${#@} -gt 0 ]; then
    usage ${SCRIPT_NAME}
    exit 1
fi

#Initialization of variables
dicom_folder=""
bids_folder=""
results_folder=""
participant_id=""
session_id=""
contrasts=()
age="n/a"
sex="n/a"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h)
            usage
            exit 0
            ;;
        -d)
            dicom_folder="$2"
            shift 2
            ;;
        -b)
            bids_folder="$2"
            shift 2
            ;;
        -r)
            results_folder="$2"
            shift 2
            ;;
        -p)
            participant_id="$2"
            shift 2
            ;;
        -s)
            session_id="$2"
            shift 2
            ;;
        -c)
            shift
            while [[ $# -gt 0 && ! $1 =~ ^- ]]; do
                contrasts+=("$1")
                shift
            done
            ;;
        -x)
            sex="$2"
            shift 2
            ;;
        -a)
            age="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Check whether the required arguments are provided, if not, print the usage and exit
variables=(dicom_folder bids_folder results_folder participant_id session_id contrasts)
for var in "${variables[@]}"; do
    if [[ -z ${!var} ]]; then
        echo "Error: Missing argument: -${var:0:1} <$var>."
        echo "To print the usage, run: ${SCRIPT_NAME} -h"
        exit 1
    fi
done

# Call the main function
main
