import os
import json
import numpy as np
from datetime import datetime
from flx.data.dataset import *

class EmbeddingBackup:
    def __init__(self, base_path="./embeddings_storage"):
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)
    
    def save_embeddings(self, vector_list, dataset_name="fingerprints"):
        """Guarda embeddings y metadata"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        folder = os.path.join(self.base_path, f"{dataset_name}_{timestamp}")
        os.makedirs(folder, exist_ok=True)
        
        # Separar IDs y embeddings
        identifiers = []
        embeddings = []
        
        for identifier, embedding in vector_list:
            identifiers.append({
                'subject': identifier.subject,
                'impression': identifier.impression
            })
            embeddings.append(embedding)
        
        # Guardar embeddings como numpy array
        embeddings_array = np.array(embeddings)
        np.save(os.path.join(folder, "embeddings.npy"), embeddings_array)
        
        # Guardar metadata como JSON
        metadata = {
            'timestamp': timestamp,
            'num_embeddings': len(vector_list),
            'embedding_dim': embeddings_array.shape[1],
            'identifiers': identifiers
        }
        
        with open(os.path.join(folder, "metadata.json"), "w") as f:
            json.dump(metadata, f, indent=2)
        
        print(f"Guardado en: {folder}")
        return folder
    
    def load_embeddings(self, folder_path):
        """Carga embeddings y metadata"""
        # Cargar embeddings
        embeddings = np.load(os.path.join(folder_path, "embeddings.npy"))
        
        # Cargar metadata
        with open(os.path.join(folder_path, "metadata.json"), "r") as f:
            metadata = json.load(f)
        
        # Reconstruir lista de vectores
        vector_list = []
        for i, id_info in enumerate(metadata['identifiers']):
            identifier = Identifier(id_info['subject'], id_info['impression'])
            vector_list.append([identifier, embeddings[i]])
        
        return vector_list, metadata

