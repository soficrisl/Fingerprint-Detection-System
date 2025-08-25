import os
from flx.extractor.fixed_length_extractor import get_DeepPrint_Tex, get_DeepPrint_TexMinu, DeepPrintExtractor
from flx.data.dataset import *
from flx.data.image_loader import SFingeLoader
from flx.data.transformed_image_loader import TransformedImageLoader
from flx.image_processing.binarization import LazilyAllocatedBinarizer
from flx.data.image_helpers import pad_and_resize_to_deepprint_input_size
from flx.scripts.generate_benchmarks import create_verification_benchmark
from flx.benchmarks.matchers import CosineSimilarityMatcher
from flx.data.embedding_loader import EmbeddingLoader
from dataloader.minex_loader import MinexLoader
from dataloader.reader_loader import ReaderLoader
from dataloader.UareU_loader import UareULoader
from dataloader.sd302c_loader import SD302CLoader

#from flx.visualization.plot_DET_curve import plot_verification_resultss
#"C:\Users\sofic\OneDrive\Documentos\Work\fixed-length-fingerprint-extractors\notebooks\example-dataset"

class EmbeddingExtraction: 
    def __init__(self, database_path: str, num_subjects: int, num_impressions:int, database_name: str):
        self.database_path = database_path
        self.num_subjects = num_subjects
        self.num_impressions = num_impressions
        self.database_name = database_name
        self.extractor:  DeepPrintExtractor = get_DeepPrint_TexMinu(8000,256)
        MODEL_DIR : str = os.path.abspath(r"C:\Users\sofic\OneDrive\Documentos\Work\Development\fixed-length-fingerprint-extractors\models\drive")
        self.extractor.load_best_model(MODEL_DIR)

    def extract_embeddings(self): 
        DATASET_PATH: str = self.database_path
        if self.database_name == "Minex": 
            image_initial_loader = MinexLoader(DATASET_PATH)
        elif self.database_name == "example-database": 
            image_initial_loader = SFingeLoader(DATASET_PATH)
        elif self.database_name == "reader": 
            image_initial_loader = ReaderLoader(DATASET_PATH)
        elif self.database_name == "UareU": 
            image_initial_loader = UareULoader(DATASET_PATH)
        elif self.database_name == "SD302c":
            image_initial_loader = SD302CLoader(DATASET_PATH)
        image_loader = TransformedImageLoader(
                images=image_initial_loader,
                poses=None,
                transforms=[
                    LazilyAllocatedBinarizer(5.0),
                    pad_and_resize_to_deepprint_input_size,
                ],
            )

        image_dataset = Dataset(image_loader, image_loader.ids)
        texture_embeddings, minutia_embeddings = self.extractor.extract(image_dataset)
        embeddings =EmbeddingLoader.combine(texture_embeddings, minutia_embeddings)
        return embeddings, image_dataset

    def extract_emb_per_subject(self, embeddings: EmbeddingLoader): 
        emb_list = []
        ids = embeddings.ids
        idb = Identifier(0,0)
        for i in range(self.num_subjects * self.num_impressions): 
            if i == 635: 
                print("a")
            id = ids[i]
            if id.subject != idb.subject: 
                idb = id
                emb_id = embeddings.get(id)
                emb_list.append([id, emb_id])
        for m in emb_list: 
            print(f"{m[0]}: {m[1][0:3]}")
        return emb_list

    def ver_benchmark(self,image_dataset, embeddings): 
        benchmark = create_verification_benchmark(list(range(image_dataset.num_subjects)), list(range(self.num_impressions)))
        matcher = CosineSimilarityMatcher(embeddings)
        results = benchmark.run(matcher)
        print(f"Equal-Error-Rate: {results.get_equal_error_rate()}")

    def extraction(self) -> list: 
        embeddings, image_dataset = self.extract_embeddings()
        self.ver_benchmark(image_dataset, embeddings)
        list_emb =  self.extract_emb_per_subject(embeddings)
        return list_emb
    
    def extraction_reader(self) : 
        embeddings, image_dataset = self.extract_embeddings()
        id = embeddings.ids[0]
        emb_id = embeddings.get(id)
        return [id, emb_id]






    








