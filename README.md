# balgrist-sci

Repository containing pipeline for processing spinal cord injury (SCI) patients (both DCM and tSCI) using the [Spinal Cord Toolbox (SCT)](https://github.com/spinalcordtoolbox/spinalcordtoolbox).

Pipeline steps:
1. DICOM to nii (BIDS) conversion
2. Processing (spinal cord and lesion segmentation, vertebral labeling)
3. Quality control (QC) + manual compression level labeling
4. Lesion metric computation

## Table of contents
* [1. Dependencies](#1-dependencies)
* [2. Installation](#2-installation)
  * [2.1 SCT Installation](#21-sct-installation)
  * [2.2 dcm2niix Installation](#22-dcm2niix-installation)
* [3. Data structure](#3-data-structure)

## 1. Dependencies

* [Spinal Cord Toolbox v6.4](https://github.com/spinalcordtoolbox/spinalcordtoolbox/releases/tag/6.4)
* [dcm2niix >= v1.0.20220505](https://github.com/rordenlab/dcm2niix?tab=readme-ov-file#install)

## 2. Installation

> [!NOTE]
> The installation process below is currently only supported on macOS.

### 2.1 SCT Installation

<details><summary>Click the triangle to expand/collapse the section</summary>

1. Open a new terminal:

Press <kbd>command</kbd> + <kbd>space</kbd> and type `Terminal` and press <kbd>return/enter</kbd>.

2. Run the following commands in the terminal (you can copy-paste the whole block):

ℹ️ The installation process will take a few minutes.

```bash
# Go to your home directory
cd ~
# Download SCT v6.4
wget https://github.com/spinalcordtoolbox/spinalcordtoolbox/archive/refs/tags/6.4.zip
# Unzip the downloaded file --> the unzipped directory will be named spinalcordtoolbox-6.4
unzip 6.4.zip
rm 6.4.zip
# Go to the SCT directory
cd spinalcordtoolbox-6.4
# Install SCT v6.4
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

### 2.2 dcm2niix Installation

<details><summary>Click the triangle to expand/collapse the section</summary>

1. Open a new terminal (if you closed the previous one):

Press <kbd>command</kbd> + <kbd>space</kbd> and type `Terminal` and press <kbd>return/enter</kbd>.

2. Run the following commands in the terminal (you can copy-paste the whole block):

```bash
# Go to the SCT directory
cd $SCT_DIR
# Activate SCT conda environment
source ./python/etc/profile.d/conda.sh
conda activate venv_sct
# Install dcm2niix using pip
pip install dcm2niix
```

3. Check that `dcm2niix` was installed correctly:

```bash
dcm2niix --version
```

The expected output is the version of `dcm2niix`.

</details>

## 3. Data structure

<details><summary>Click the triangle to expand/collapse the section</summary>

Expected [BIDS](https://bids-specification.readthedocs.io/en/stable/)-like structures is shown below.

Note that only the `sourcedata` directory containing folders with DICOM files for each subject is required. 
The rest of the directories and files will be created during the processing.

```
├── participants.tsv        --> file with participants information; see example below
├── sourcedata              --> folder containing DICOM files for each subject
│   ├── dir_20230711        --> folder with DICOM files for first subject and first session
│   ├── dir_20230711        --> folder with DICOM files for second subject and first session
│   ├── ... 
│   ├── dir_20240815        --> folder with DICOM files for first subject and second session
│   └── ... 
├── sub-001                 --> folder containing NIfTI files for first subject
│   ├── ses-01              --> first session
│   │  ├── anat             --> folder with anatomical data
│   │  │  ├── sub-001_ses-01_T2w.nii.gz
│   │  │  ├── sub-001_ses-01_T2w_copression.nii.gz
│   │  │  ├── ...
│   │  └── dwi              --> folder with diffusion data
│   │     ├── sub-001_ses-01_dwi.nii.gz
│   │     ├── sub-001_ses-01_dwi.bval
│   │     ├── sub-001_ses-01_dwi.bvec
│   └── ses-02              --> second session
│      ├── ...
├── sub-002                 --> folder containing NIfTI files for second subject
│   ├── ...
├── ...
└── derivatives             --> folder to store visually checked and/or manually corrected data (for example, spinal cord segmentations)
    └── labels
        ├── sub-001         --> folder with corrected data for first subject
        │   ├── ses-01      --> first session
        │   │  ├── anat
        │   │  │  ├── sub-001_ses-01_T2w_label-SC_seg.nii.gz              --> spinal cord (SC) binary segmentation 
        │   │  │  ├── sub-001_ses-01_T2w_label-compression_label.nii.gz   --> binary compression labeling
        │   │  │  ├── ...
        │   │  └── dwi
        │   │     ├── sub-001_ses-01_dwi_label-SC_seg.nii.gz
        │   │     ├── ...
        │   └── ses-02      --> second session
        │      ├── ...
        ├── sub-002 
        └── ...
```

`participants.tsv` example:

| participant_id | ses_id | source_id | age | sex |
|----------------|--------|-----------|-----|-----|
| sub-001        | ses-01 | dir_20230711 | 42  | M   |
| sub-001        | ses-02 | dir_20240815 | 43  | M   |
| sub-002        | ses-01 | dir_20230713 | 57  | F   |

ℹ️ Notice that we use one row per session. This means that, for example, `sub-001` has two rows in the table because they have two sessions.

</details>