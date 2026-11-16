# Credits

## Training data of the released model

The model in NoodleWatch is trained on these two datasets from Roboflow Universe, both under the [Creative Commons Attribution 4.0 International license (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/):

- **3D printing failure**, version 1, by the Roboflow Universe workspace `3d-printing-failure`:
  https://universe.roboflow.com/3d-printing-failure/3d-printing-failure/dataset/1
- **Defect Detection in 3D Printing**, version 4, by the Roboflow Universe workspace `project-jkfnh`:
  https://universe.roboflow.com/project-jkfnh/defect-detection-in-3d-printing-9vutd/dataset/4

Changes made: only the spaghetti labels ("spaghetti" in the first dataset, "Spaghetti" in the second) and the "Blob of Death" labels of the second dataset are kept, as the classes `spaghetti` and `boule`; the other labels are dropped and their images are used as images without a defect to detect. Images are grouped by original photo, so that copies of a photo (rotated, flipped…) never end up in both the training and the test sets.

## Also used during development

These datasets, also under CC BY 4.0, were used in experiments but are not part of the released model:

- **3D printing flaws**, version 10, by the Roboflow Universe workspace `spaghettidetect`:
  https://universe.roboflow.com/spaghettidetect/3d-printing-flaws/dataset/10
- **3D printing defects**, version 3, by the Roboflow Universe workspace `hcmut-yxyhm`:
  https://universe.roboflow.com/hcmut-yxyhm/3d-printing-defects/dataset/3
