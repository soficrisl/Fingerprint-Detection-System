import psycopg2
from pgvector.psycopg2 import register_vector
import numpy as np
from embedding_extraction import EmbeddingExtraction
from emb_backup import EmbeddingBackup
from app import App
from payment_validator import MetroPaymentValidator
import cv2
import time
def sql_connection():
    conn = psycopg2.connect(host = "localhost", database ="test_db", user="postgres", password = "123456")
    register_vector(conn)
    cur = conn.cursor()
    return cur, conn

        
def insert_emb(cur, conn, vector_list, database_name):
    cur.execute("SELECT COALESCE(MAX(pas_id), 10) FROM fingerprints")
    current_max_pas_id = cur.fetchone()[0]
    next_pas_id = current_max_pas_id + 1
    inserted_count = 0
    for identifier, embedding in vector_list:
        subject_in_database = identifier.subject  # Original subject ID
        impression = identifier.impression
        try:
            cur.execute("""
                INSERT INTO fingerprints (pas_id, impression, embedding, database_name, subject_in_database)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (pas_id) DO NOTHING
            """, (
                next_pas_id, 
                impression, 
                embedding.tolist(), 
                database_name, 
                subject_in_database
            ))
            
            # Only increment if the insert was successful
            if cur.rowcount > 0:
                next_pas_id += 1
                inserted_count += 1
                
        except Exception as e:
            print(f"Error inserting subject {subject_in_database}, impression {impression}: {e}")
            conn.rollback()
            continue
    
    conn.commit()
    print(f"Inserted {inserted_count} fingerprints into database")
    return inserted_count

def create_emb(cur, conn, database_name, databasepath, subjects, impression): 
    vector_list = []
    extractor = EmbeddingExtraction(databasepath, subjects, impression, database_name)
    vector_list  = extractor.extraction()
    insert_emb(cur, conn, vector_list, database_name)
    # storage = EmbeddingBackup()
    # folder = storage.save_embeddings(vector_list, "example_dataset")
    return vector_list

def load_emb(storage: EmbeddingBackup): 
    folder = r"C:\Users\sofic\OneDrive\Documentos\Work\Development\embeddings_storage\example_dataset_20250717_221942"
    loaded_vectors, metadata = storage.load_embeddings(folder)
    print(f"Cargados {len(loaded_vectors)} embeddings")
    return loaded_vectors

def search_fingerprint_db(conn, query_embedding, top_k):
    """Search for matching fingerprints"""
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            id,
            subject_id,
            impression,
            1 - (embedding <=> %s::vector) as similarity,
            embedding <=> %s::vector as distance
        FROM fingerprints
        ORDER BY embedding <=> %s::vector ASC
        LIMIT %s
    """, (
        query_embedding.tolist(),
        query_embedding.tolist(),
        query_embedding.tolist(),
        top_k
    ))
    
    results = []
    for row in cur.fetchall():
        results.append({
            'id': row[0],
            'subject_id': row[1],
            'impression': row[2],
            'similarity': row[3],
            'distance': row[4]
            
        })

    print(results)
    return results

def main():
    cur, conn =  sql_connection()
    # DATASET_PATH = r"C:\Users\sofic\OneDrive\Documentos\Work\Development\Databases\sd302c100500"
    # # # # MINEX_PATH = r"C:\Users\sofic\OneDrive\Documentos\Work\Development\minex\minexiii\validation\validation_imagery_raw"
    # vectors = create_emb(cur, conn,"SD302c",DATASET_PATH, 1275, 2)
    app = App(True)
    result = app.initiate() 
    app.set_state(False)
    for i in range(5):
        result = app.initiate() 
    result = app.initiate()
    app.set_state(True)
    for i in range(4):
        result = app.initiate() 
    app.set_state(False)
    for i in range(10):
        result = app.initiate()


if __name__ == '__main__':
    main()

  
    
    
    # m = input("1- Register \n 2- Match")
    # flag = True
    # while flag:
    #     try: 
    #         n = int(m)
    #         if n == 1: 
    #             state = True
    #         else:
    #             state = False
    #         flag = False
    #     except:
    #         print("Choose a number")
    # print("a")
    # app = App(state)
    # result = app.initiate()
    # if result["success"]:
    #     response = {
    #         "success": True,
    #         "message": result["message"],
    #         "pas_id": result.get('pasId', 0),
    #         "led_color": "green"
    #     }
    #     print(response)
    #     return response
    # else:
    #     return {
    #         "success": False,
    #         "message": result.get("error", ),
    #         "led_color": "red"
    #     }

    # api_base_url = "https://api-dev.enlaparadave.com/api/v1"
    # payment_validator = MetroPaymentValidator(api_base_url)
    # token ="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJhbnRvbmlvZ3VlcnJhMTZAeW9wbWFpbC5jb20iLCJyb2xlcyI6IlBBU1NFTkdFUiIsImlzcyI6Imh0dHA6Ly9lbHAtYXBpLWRldi5zb3V0aGFtZXJpY2EtZWFzdDEtYS5jLmVuLWxhLXBhcmFkYS1wcm9kLmludGVybmFsOjkwMDEvYXBpL3YxL2F1dGgvbG9naW4vc2lnbmluIiwiZXhwIjo0OTA5NzQ4NjM2fQ.AoibrHAYqo6fVYmpxyuj4nQiuG8D7YZ7W5a7p2_Hlv4" 
    # response = payment_validator.validate_payment(token,8)
    # if response['success']: 
    #     print(response["message"])
    # else: 
    #     print(response["error"])