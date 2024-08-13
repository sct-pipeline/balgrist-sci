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

## 1. Dependencies

[Spinal Cord Toolbox v6.4](https://github.com/spinalcordtoolbox/spinalcordtoolbox/releases/tag/6.4)
[dcm2niix >= v1.0.20220505](https://github.com/rordenlab/dcm2niix?tab=readme-ov-file#install)

## 2. Installation

> [!NOTE]
> The installation process below is currently only supported on macOS.

### 2.1 SCT Installation

1. Open a new terminal:

Press <kbd>command</kbd> + <kbd>space</kbd> and type `Terminal` and press <kbd>return/enter</kbd>.

2. Run the following commands in the terminal (you can copy-paste the whole block):

> [!NOTE]
> The installation process will take a few minutes.

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

> [!NOTE]
> We are not using `git clone` because Apple Developer Tools are needed for `git`.

3. Check that SCT was installed correctly:

Close the terminal and open a new one (press <kbd>command</kbd> + <kbd>space</kbd> and type `Terminal` and press <kbd>return/enter</kbd>.).

```bash
# Check that SCT was installed correctly
sct_check_dependencies
# Display location of SCT installation
echo $SCT_DIR
```

The expected output is `[OK]` for all dependencies.

### 2.2 dcm2niix Installation

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