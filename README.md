# balgrist-sci

Repository containing code to process MRI data from spinal cord injury (SCI) patients (both DCM and tSCI) using the [Spinal Cord Toolbox (SCT)](https://github.com/spinalcordtoolbox/spinalcordtoolbox).

Steps:
1. DICOM to NIfTI (BIDS) conversion
2. Processing (spinal cord and lesion segmentation, vertebral labeling)
3. Quality control (QC) + manual compression level labeling
4. Lesion metric computation -- not implemented yet

## Table of contents
- [1. Getting Started](#1-getting-started)
  - [1.1 Dependencies](#11-dependencies)
  - [1.2 Installation](#12-installation)
    - [SCT Installation](#sct-installation)
    - [dcm2niix Installation](#dcm2niix-installation)
    - [FSLeyes Installation](#fsleyes-installation)
    - [Downloading this repository](#downloading-this-repository)
- [2. Data structure](#2-data-structure)
  - [2.1 File organization](#21-file-organization)
- [3. Analysis pipeline](#3-analysis-pipeline)

## 1. Getting Started

### 1.1 Dependencies

* [Spinal Cord Toolbox v7.0](https://github.com/spinalcordtoolbox/spinalcordtoolbox/releases/tag/7.0): toolbox for processing spinal cord MRI data
* [dcm2niix >= v1.0.20220505](https://github.com/rordenlab/dcm2niix?tab=readme-ov-file#install): tool for converting DICOM images into the NIfTI format
* [FSLeyes](https://owncloud.cesnet.cz/index.php/s/z5h02r0cq0B7ESf): tool for visualizing NIfTI images

### 1.2 Installation

> [!NOTE]
> The installation process below is currently only supported on macOS.

#### SCT Installation

<details><summary>Click the triangle to expand/collapse the section</summary>

1. Open a new terminal:

Press <kbd>command</kbd> + <kbd>space</kbd> and type `Terminal` and press <kbd>return/enter</kbd>.

2. Run the following commands in the terminal (you can copy-paste the whole block):

ℹ️ The installation process will take a few minutes.

```bash
# Go to your home directory
cd ~
# Download SCT v7.0
curl -L -o 7.0.zip https://github.com/spinalcordtoolbox/spinalcordtoolbox/archive/refs/tags/7.0.zip
# Unzip the downloaded file --> the unzipped directory will be named spinalcordtoolbox-7.0
unzip 7.0.zip
rm 7.0.zip
# Go to the SCT directory
cd spinalcordtoolbox-7.0
# Install SCT v7.0
./install_sct -iyc
#  '-i'   Install in-place (i.e., in the current directory)
#  '-y'   Install without interruption with 'yes' as default answer
#  '-c'   Disables sct_check_dependencies so we can check it separately
```

3. Check that SCT was installed correctly:

Close the terminal and open a new one (press <kbd>command</kbd> + <kbd>space</kbd> and type `Terminal` and press <kbd>return/enter</kbd>.).

```bash
# Check that SCT was installed correctly
sct_check_dependencies
# Display location of SCT installation
echo $SCT_DIR
```

The expected output is `[OK]` for all dependencies.

</details>

#### dcm2niix Installation

<details><summary>Click the triangle to expand/collapse the section</summary>

1. Open a new terminal (if you closed the previous one):

Press <kbd>command</kbd> + <kbd>space</kbd> and type `Terminal` and press <kbd>return/enter</kbd>.

Then, activate the SCT conda environment:

```bash
# Go to the SCT directory
cd $SCT_DIR
# Activate SCT conda environment
source ./python/etc/profile.d/conda.sh
conda activate venv_sct
```

2. Run the following command in the terminal (you can copy-paste the whole block):

```bash
# Install dcm2niix using pip
pip install dcm2niix
```

3. Check that `dcm2niix` was installed correctly:

```bash
dcm2niix --version
```

The expected output is the version of `dcm2niix`.

</details>

#### FSLeyes Installation

<details><summary>Click the triangle to expand/collapse the section</summary>

1. Open a new terminal (if you closed the previous one):

Press <kbd>command</kbd> + <kbd>space</kbd> and type `Terminal` and press <kbd>return/enter</kbd>.

Then, activate the SCT conda environment:

```bash
# Go to the SCT directory
cd $SCT_DIR
# Activate SCT conda environment
source ./python/etc/profile.d/conda.sh
conda activate venv_sct
```

2. Run the following command in the terminal (you can copy-paste the whole block):

```bash
# Install fsleyes from conda-forge
conda install -c conda-forge fsleyes
```

3. Check that `fsleyes` was installed correctly:

```bash
fsleyes --version
```

The expected output is the version of `fsleyes`.

</details>

#### Downloading this repository

<details><summary>Click the triangle to expand/collapse the section</summary>

1. Open a new terminal (if you closed the previous one):

Press <kbd>command</kbd> + <kbd>space</kbd> and type `Terminal` and press <kbd>return/enter</kbd>.

2. Run the following commands in the terminal (you can copy-paste the whole block):

```bash
# Go to your home directory
cd ~
# Download the repository --> the repository will be downloaded as zip file named balgrist-sci.zip
curl -L -o balgrist-sci.zip https://github.com/sct-pipeline/balgrist-sci/archive/refs/tags/r20241208.zip
# Unzip the downloaded file --> the unzipped directory will be named balgrist-sci-r20241208
unzip balgrist-sci.zip
rm balgrist-sci.zip
# Rename the unzipped directory to balgrist-sci
mv balgrist-sci-r20241208 balgrist-sci
# Make the process_data.sh script executable
cd balgrist-sci
chmod u+x process_data.sh
```

3. Check that the repository was downloaded correctly:

```bash
# Activate SCT conda environment
source ./python/etc/profile.d/conda.sh
conda activate venv_sct
# Call the help of the file_loader.py script
python ~/balgrist-sci/file_loader.py --help
```

The expected output is the help message of the `file_loader.py` script.

</details>

## 2. Data structure

### 2.1 File organization

<details><summary>Click the triangle to expand/collapse the section</summary>

A file organization according to the [BIDS](https://bids-specification.readthedocs.io/en/stable/) is shown below.

Note that only the `sourcedata` directory containing folders with DICOM files for each subject is initially required. 
The rest of the directories and files will be created during the processing; see the next section.

```
├── participants.tsv        --> file with participants information; see example below
├── sourcedata              --> folder containing DICOM files for each subject
│   ├── dir_20230711        --> folder with DICOM files for first subject and first session
│   ├── dir_20230711        --> folder with DICOM files for second subject and first session
│   ├── ... 
│   ├── dir_20240815        --> folder with DICOM files for first subject and second session
│   └── ... 
├── bids                    --> folder with BIDS-compliant data
│    ├── sub-001            --> folder containing NIfTI files for first subject
│    │   ├── ses-01         --> first session
│    │   │  └── anat        --> folder with anatomical data
│    │   │     ├── sub-001_ses-01_acq-sag_T2w.nii.gz
│    │   │     ├── sub-001_ses-01_acq-ax_T2w.nii.gz
│    │   │     ├── ...
│    │   └── ses-02         --> second session
│    │      ├── ...
│    ├── sub-002            --> folder containing NIfTI files for second subject
│    │   ├── ...
│    ├── ...
│    └── derivatives        --> folder to store visually checked and/or manually corrected data (for example, spinal cord segmentations)
│        └── labels
│            ├── sub-001    --> first subject
│            │   ├── ses-01 --> first session
│            │   │  └── anat
│            │   │     ├── sub-001_ses-01_acq-sag_T2w_label-SC_seg.nii.gz      --> spinal cord (SC) binary segmentation
│            │   │     ├── sub-001_ses-01_acq-sag_T2w_label-disc.nii.gz        --> discrete discs labeling
│            │   │     ├── ...
│            │   └── ses-02 --> second session
│            │      ├── ...
│            ├── sub-002
│            └── ...
└── data_processed          --> folder with processed data  
     ├── sub-001            --> folder with processed data for first subject
     │   ├── ses-01         --> first session
     │   │  ├── anat        --> folder with processed anatomical data
     │   │  │  ├── ...
     ...
```

`participants.tsv` example:

| participant_id | ses_id | source_id | age | sex |
|----------------|--------|-----------|-----|-----|
| sub-001        | ses-01 | dir_20230711 | 42  | M   |
| sub-001        | ses-02 | dir_20240815 | 43  | M   |
| sub-002        | ses-01 | dir_20230713 | 57  | F   |

ℹ️ Notice that we use one row per session. This means that, for example, `sub-001` has two rows in the table because they have two sessions.

</details>

## 3. Analysis pipeline

The entire analysis pipeline is orchestrated by the `process_data.sh` script.

The script first converts DICOM files to NIfTI (BIDS) format using `dcm2niix`. 
Then, it processes the data using SCT functions. After running the SCT functions, the script opens FSLeyes to allow the 
user to visually check the results. 

Usage:

```bash
bash process_data.sh -d <dicom folder> -b <bids folder> -r <results folder> -p <participant id> -s <session id> -c <contrasts> [-age <age> -sex <sex>]
```

```
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
```

Example:

```bash
bash process_data.sh \
  -d ~/data/experiments/balgrist-sci/source_data/dir_20231010 \
  -b ~/data/experiments/balgrist-sci/bids \
  -r ~/data/experiments/balgrist-sci/data_processed \
  -p sub-001 \
  -s ses-01 \
  -c acq-sag_T2w acq-ax_T2w \
  -a 30 \
  -x M
```
