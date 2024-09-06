#!/bin/bash
#
# Process spinal cord MRI data
#
# Steps:
#   1. Convert DICOM files to NIfTI format
#   2. Run spinal cord analysis
#
# Authors: Jan Valosek, Sandrine Bedard
# AI assistance: Claude 3.5 Sonnet, ChatGPT-4o, and GitHub Copilot
#


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
  `basename ${0}` -d <dicom folder> -b <bids folder> -p <participant id> -s <session id> -c <contrasts> [-age <age> -sex <sex>]

MANDATORY ARGUMENTS
  -d <dicom folder>           Path to the folder containing DICOM images. Example: ~/sci-balgrist-study/sourcedata/dir_20230711
  -b <bids folder>            Path to the BIDS folder where the converted NIfTI images will be stored. Example: ~/sci-balgrist-study/bids
  -p <participant id>         Participant ID. Example: sub-001
  -s <session id>             Session ID. Example: ses-01
  -c <contrasts>              MRI contrasts to use (space-separated if multiple). Example: 'T2w dwi'

OPTIONAL ARGUMENTS
  -a <age>                  Age of the subject at the time of the MRI scan. Example: 25. Default: n/a
  -x <sex>                  Sex of the subject. Example: M. Default: n/a
EOF
}


main()
{
    # Get the directory of the current script
    get_repo_dir
    # Activate the SCT conda environment with dcm2niix installed
    activate_env

    check_dependencies
    convert_dcm2nii
    main_analysis

    conda deactivate
    echo "Done."
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
    commands=("dcm2niix" "sct_check_dependencies")

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

# Convert DICOM files to NIfTI format using the file_loader.py script, which calls the dcm2niix function
convert_dcm2nii()
{
    # Call the file_loader.py script to convert DICOM files to NIfTI format
    images_to_use=$(python "${REPO_DIR}"/file_loader.py -dicom-folder "$dicom_folder" -bids-folder "$bids_folder" -participant "$participant_id" -session "$session_id" -contrasts "${contrasts[@]}" -age "$age" -sex "$sex" | grep "^VAR:")

    # Strip the 'VAR:' prefix and store them into an array
    images_to_use_array=($(echo "$images_to_use" | sed 's/^VAR://'))
}

main_analysis()
{
    # Iterate over the array and split each contrast:path pair
    for item in "${images_to_use_array[@]}"; do
        # Use ':' as the delimiter to split the contrast and path
        contrast=$(echo "$item" | cut -d ':' -f 1)
        path=$(echo "$item" | cut -d ':' -f 2-)

        # Use the variables or print them
        echo "Contrast: $contrast"
        echo "Path: $path"

        # If contrast T2w is found, assign the path to file1
        if [[ $contrast == "T2w" ]]; then
            sct_deepseg_sc -i "$path" -c t2
            # TODO: continue with the analysis
            # TODO: output the analysis results to the 'data_processed' folder (see README / 2.1 File organization)
        fi

    done
}

# Print usage if no arguments are provided
if [ ! ${#@} -gt 0 ]; then
    usage `basename ${0}`
    exit 1
fi

#Initialization of variables
dicom_folder=""
bids_folder=""
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
variables=(dicom_folder bids_folder participant_id session_id contrasts)
for var in "${variables[@]}"; do
    if [[ -z ${!var} ]]; then
        echo "Error: Missing argument: -${var:0:1} <$var>."
        echo "To print the usage, run: `basename ${0}` -h"
        exit 1
    fi
done

# Call the main function
main
