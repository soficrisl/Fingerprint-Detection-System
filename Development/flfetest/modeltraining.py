from flx.data.dataset import IdentifierSet, Identifier
from flx.extractor.fixed_length_extractor import get_DeepPrint_TexMinu, DeepPrintExtractor
import os

import torch 

from flx.data.dataset import *
from flx.data.image_loader import SFingeLoader
from flx.data.minutia_map_loader import SFingeMinutiaMapLoader
from flx.data.label_index import LabelIndex
from flx.data.transformed_image_loader import TransformedImageLoader
from flx.image_processing.binarization import LazilyAllocatedBinarizer
from flx.data.image_helpers import pad_and_resize_to_deepprint_input_size

def main(): 
    # We will use the example dataset with 10 subjects and 10 impression per subject
    training_ids: IdentifierSet = IdentifierSet([Identifier(i, j) for i in range(10) for j in range(10)])

    # We choose a dimension of 512 for the fixed-length representation (TexMinu has two outputs num_dims)
    extractor: DeepPrintExtractor = get_DeepPrint_TexMinu(num_training_subjects=training_ids.num_subjects, num_dims=256)

    DATASET_DIR: str = os.path.abspath(r"C:\Users\sofic\OneDrive\Documentos\Work\fixed-length-fingerprint-extractors\notebooks\example-dataset")
    MODEL_OUTDIR: str = os.path.abspath(r"C:\Users\sofic\OneDrive\Documentos\Work\fixed-length-fingerprint-extractors\models\example-model")
    i = 0
    # We will use the SFingeLoader to load the images from the dataset
    image_loader = TransformedImageLoader(
            images=SFingeLoader(DATASET_DIR),
            poses=None,
            transforms=[
                LazilyAllocatedBinarizer(5.0),
                pad_and_resize_to_deepprint_input_size,
            ],
        )
    print(f"{i} time")
    i +=1

    image_dataset = Dataset(image_loader, training_ids)
    # For pytorch, we need to map the subjects to integer labels from [0 ... num_subjects-1]
    label_dataset = Dataset(LabelIndex(training_ids), training_ids)

    minutia_maps_dataset = Dataset(SFingeMinutiaMapLoader(DATASET_DIR), training_ids)

    print("Starting training...")
    extractor.fit(
        fingerprints=image_dataset,
        minutia_maps=minutia_maps_dataset,
        labels=label_dataset,
        validation_fingerprints=None,
        validation_benchmark=None,
        num_epochs=20,
        out_dir=MODEL_OUTDIR
    )
    print("Training complete!")

if __name__ == '__main__':
    # This guard is ESSENTIAL on Windows to prevent multiprocessing errors
    # It ensures the training code only runs in the main process
    main()