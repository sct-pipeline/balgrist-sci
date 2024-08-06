# balgrist-sci

Repository containing pipeline for processing spinal cord injury (SCI) patients (both DCM and tSCI) using the [Spinal Cord Toolbox (SCT)](https://github.com/spinalcordtoolbox/spinalcordtoolbox).

Steps:
1. DICOM to nii (BIDS) conversion
2. Processing (spinal cord and lesion segmentation, vertebral labeling)
3. Quality control (QC) + manual compression level labeling
4. Lesion metric computation
