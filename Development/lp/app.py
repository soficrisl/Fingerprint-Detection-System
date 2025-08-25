import time
import cv2 
import numpy as np
import psycopg2
from pyzkfp import ZKFP2
from dataloader.helpers.functions import find_sizeReader
from embedding_extraction import EmbeddingExtraction
from pgvector.psycopg2 import register_vector
import os
from payment_validator import MetroPaymentValidator 

class App:
    def __init__(self, state, status_callback = None):
        self.state = state 
        self.status_callback = status_callback
        self.path = r"C:\Users\sofic\OneDrive\Documentos\Work\Development\received_fingerprints"
        self.conn  = psycopg2.connect(host = "localhost", database ="test_db", user="postgres", password = "123456")
        register_vector(self.conn)
        self.cur = self.conn.cursor()
        self.api_base_url = "https://api-prd.enlaparadave.com/api/v1"
        self.payment_validator = MetroPaymentValidator(self.api_base_url)
        self.extractor = EmbeddingExtraction(self.path, 1,1, "reader")
        self.zkfp2 = ZKFP2()
        self.zkfp2.Init()

    def set_state(self,state): 
        self.state = state

    def set_state_callback(self,callback): 
        self.status_callback = callback

    def send_status(self, message, line1=None, line2 = None): 
        if self.status_callback: 
            self.status_callback(message, line1, line2)
        else: 
            print(message)

    def center_and_relocate(self, image):
        cv2.imshow("Initial Image", image)
        orig_h, orig_w = image.shape[:2]
        pad = 20  
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        padded = cv2.copyMakeBorder(
            image,
            top=pad, bottom=pad,
            left=pad, right=pad,
            borderType=cv2.BORDER_CONSTANT,
            value=[250,250,250]  
        )
        cv2.imshow("Padded", padded)
        gray = cv2.cvtColor(padded, cv2.COLOR_BGR2GRAY)
        #FIRST PART: ROTATION ------------------------------------------------------------------------
        #first threshold
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY +cv2.THRESH_OTSU)
        cv2.imshow("Binary 1", binary)

        cv2.waitKey(0)
        cv2.destroyAllWindows()

        # draw countours
        contours, hierarchy = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)

        if len(contours) > 1:
            contours = contours[:-1]
        cv2.drawContours(binary, contours, -1,(0,255,0), 6)
        cv2.imshow("Countours Connected", binary)

        # second  threshold, binary
        _, binary = cv2.threshold(binary, 0, 255, cv2.THRESH_BINARY)
        cv2.imshow("Binary 2", binary)

        # first final countour
        contours, hierarchy = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        if len(contours) > 1:
            contours = contours[:-1]
        if len(contours) > 0:
            cnt = max(contours, key=cv2.contourArea)
            padded_copy = padded.copy()
            max_idx, max_cnt = max(
                enumerate(contours),
                key=lambda ic: cv2.contourArea(ic[1])
            )
            cv2.drawContours(padded_copy,contours, max_idx, (0, 255, 0), 2)
            cv2.imshow("Main Contour", padded_copy)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
            print(len(contours))
            (h, w) = padded.shape[:2]
            cnt = max(contours, key=cv2.contourArea)
            if len(cnt) >= 5:
                ellipse = cv2.fitEllipse(cnt)
                (cx, cy), (MA, ma), phi = cv2.fitEllipse(cnt)
                print(f"Original angle: {phi}")
                if phi > 90:
                    # For angles > 90°, the correction needed is -(180 - phi)
                    rotation_angle = -(180 - phi)
                else:
                    # For angles < 90°, the correction needed is -phi
                    rotation_angle = phi
                if abs(rotation_angle) > 11: 
                    return None
                vis = padded.copy()
                print(f"Adjusted rotation angle: {rotation_angle}")
                cv2.drawContours(vis, [cnt], -1, (0,128,255), 2)
                cv2.ellipse(vis, ellipse, (0,255,0), 2)
                cv2.imshow("Ellipse Fit", vis)
                rotate_center =  (w // 2, h // 2)
                M = cv2.getRotationMatrix2D((int(cx),int(cy)), rotation_angle, 1.0)
                rotated = cv2.warpAffine(padded, M, (w, h),flags=cv2.INTER_CUBIC,
                    borderMode=cv2.BORDER_REPLICATE
                )
                rotated_binary= cv2.warpAffine(
                    binary, M, (w, h),
                    flags=cv2.INTER_CUBIC,
                    borderMode=cv2.BORDER_REPLICATE
                )
                cv2.imshow("Rotated padded", rotated)
                cv2.imshow("Rotated Binary: ", rotated_binary)
            else:
                print("Contour has too few points to fit an ellipse.")
                rotated = padded.copy()
                rotated_binary = binary.copy()
        else:
            print("No contours found.")
            rotated = padded.copy()
            rotated_binary = binary.copy()
            cv2.waitKey(0)
            cv2.destroyAllWindows()

        #TAKE OUT WHITE EXCESS ------------------------------------------------------------------------------
        kernel = np.ones((3, 3), np.uint8)
        rotated_binary_clean = cv2.morphologyEx(rotated_binary, cv2.MORPH_OPEN, kernel) # CHANGED IT SO IT DOESNT CONSIDER THE ROTATED PICTURE -> TEST
        rotated_binary_clean = cv2.morphologyEx(rotated_binary_clean, cv2.MORPH_CLOSE, kernel)
        
        cv2.imshow("Cleaned Binary", rotated_binary_clean)
        
        # Invert for contour finding
        rotated_binary_inv = cv2.bitwise_not(rotated_binary_clean)
        contours_rot, _ = cv2.findContours(rotated_binary_inv, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if len(contours_rot) > 0:
            cnt_rot = max(contours_rot, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(cnt_rot)
            
            # Very tight crop
            margin = 1  # Minimal margin
            x = max(0, x - margin)
            y = max(0, y - margin)
            w = min(rotated.shape[1] - x, w + 2 * margin)
            h = min(rotated.shape[0] - y, h + 2 * margin)
            
            result = padded[y:y+h, x:x+w]
            
            print(f"Bounding box: x={x}, y={y}, w={w}, h={h}")
            print(f"Result size: {result.shape}")
        else:
            result = padded[pad:pad+orig_h, pad:pad+orig_w]
        
        cv2.imshow("Method 1: Standard Crop", result)
        cv2.imshow("Original", image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        
        return result


    def preprocess_picture(self, image):
        outer_radius = 70
        inner_radius = 60  # Adjust this to control the thickness of the crescent
        value = 250
        image = image.copy()
        # TOP-LEFT corner - crescent with curve facing corner
        for y in range(outer_radius):
            for x in range(outer_radius):
                # Distance from (0,0) corner
                outer_dist = np.sqrt(x**2 + y**2)
                # Distance from inner circle center (shifted inward)
                inner_dist = np.sqrt((x - inner_radius)**2 + (y - inner_radius)**2)
                
                # Inside outer circle AND outside inner circle
                if outer_dist <= outer_radius and inner_dist >= inner_radius:
                    image[y, x] = value

        outer_radius = 80
        inner_radius = 70
        # TOP-RIGHT corner
        for y in range(outer_radius):
            for x in range(image.shape[1] - outer_radius, image.shape[1]):
                # Distance from top-right corner
                corner_x = image.shape[1] - 1
                outer_dist = np.sqrt((corner_x - x)**2 + y**2)
                # Inner circle shifted inward from corner
                inner_dist = np.sqrt((corner_x - x - inner_radius)**2 + (y - inner_radius)**2)
                
                if outer_dist <= outer_radius and inner_dist >= inner_radius:
                    image[y, x] = value
        outer_radius = 85
        inner_radius = 75
        # BOTTOM-LEFT corner
        for y in range(image.shape[0] - outer_radius, image.shape[0]):
            for x in range(80):
                # Distance from bottom-left corner
                corner_y = image.shape[0] - 1
                outer_dist = np.sqrt(x**2 + (corner_y - y)**2)
                # Inner circle shifted inward from corner
                inner_dist = np.sqrt((x - inner_radius)**2 + (corner_y - y - inner_radius)**2)
                
                if outer_dist <= outer_radius and inner_dist >= inner_radius:
                    image[y, x] = value

        outer_radius = 140
        inner_radius = 130
        # BOTTOM-RIGHT corner
        for y in range(image.shape[0] - outer_radius, image.shape[0]):
            for x in range(image.shape[1] - outer_radius, image.shape[1]):
                # Distance from bottom-right corner
                corner_x = image.shape[1] - 1
                corner_y = image.shape[0] - 1
                outer_dist = np.sqrt((corner_x - x)**2 + (corner_y - y)**2)
                # Inner circle shifted inward from corner
                inner_dist = np.sqrt((corner_x - x - inner_radius)**2 + (corner_y - y - inner_radius)**2)
                
                if outer_dist <= outer_radius and inner_dist >= inner_radius:
                    image[y, x] = value
        clahe = cv2.createCLAHE(clipLimit=3,tileGridSize=(4,4))
        enhanced = clahe.apply(image)
        result = self.center_and_relocate(enhanced)
        return result
        
    def get_fingerprint(self):
        print("Se ha inicializado la libreria \n")
        device_count = self.zkfp2.GetDeviceCount()
        if device_count > 0:
            self.zkfp2.OpenDevice(0)
            print("Dispositivo lector detectado \n Ingrese su huella. \n")
            max_attempts = 3
            for attempt in range(max_attempts):
                self.send_status(
                    f"Coloque su dedo - Intento {attempt + 1}/{max_attempts}",
                    "Ponga su huella",
                    f"Intento {attempt + 1}/{max_attempts}"
                )
                print(f"\nIntento {attempt + 1}/{max_attempts}")
                capture = None
                while not capture:
                    capture = self.zkfp2.AcquireFingerprintImage()
                self.send_status("Huella capturada", "Huella tomada", "Procesando...")
                a, b = find_sizeReader(len(capture))
                unprocessed = np.frombuffer(capture, dtype=np.uint8).reshape(a, b)
                quality_score = self.quick_quality_check(unprocessed)
                print(f"Calidad: {quality_score}/100")
                
                if quality_score >= 60:  # Minimum quality threshold
                    print("Huella escaneada con buena calidad\n")
                    processed = self.preprocess_picture(unprocessed)
                    if processed is None: 
                        if attempt < max_attempts - 1:
                            self.send_status(
                                "Calidad insuficiente, intente de nuevo",
                                "Calidad baja",
                                "Intente de nuevo"
                            )
                            continue
                    else:                     
                        self.send_status(
                        "Huella capturada exitosamente",
                        "Huella tomada", 
                        "Exitosamente!"
                    )
                        filename = f"received_fingerprints/image_subject.png"
                        if os.path.exists(filename):
                            try:
                                os.remove(filename)
                                print(f"Existing file {filename} deleted.")
                            except Exception as e:
                                print(f"Error deleting existing file: {e}")
                        try:
                            cv2.imwrite(filename, processed)
                            print(f"Saved fingerprint image to {filename}")
                        except Exception as e:
                            print(f"Error saving image: {e}")
                        return processed
                else:
                    print("Calidad insuficiente. Por favor intente de nuevo.")
                    if attempt < max_attempts - 1:
                        self.send_status(
                            "Calidad insuficiente, intente de nuevo",
                            "Calidad baja",
                            "Intente de nuevo"
                        )
                        print("Levante y vuelva a colocar su dedo...")
                        time.sleep(2)
            self.send_status(
                "No se pudo capturar huella de calidad",
                "Error captura",
                "Intente mas tarde"
            )
            print("No se pudo obtener una huella de calidad suficiente")
            return None

    def quick_quality_check(self, image):
        """
        Simplified quality check
        """
        score = 100
        
        # Check contrast
        contrast = np.std(image)
        if contrast < 20:
            score -= 40
        elif contrast < 40:
            score -= 20
        
        # Check if too dark or bright
        mean_val = np.mean(image)
        if mean_val < 50 or mean_val > 200:
            score -= 30
        
        # Check coverage
        _, binary = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        coverage = np.sum(binary == 0) / binary.size
        if coverage < 0.3:
            score -= 30
        
        return max(0, min(100, score))

    # def get_fingerprint(self):
    #     zkfp2 = ZKFP2()
    #     zkfp2.Init()
    #     print("Se ha inicializado la libreria \n")
    #     device_count = zkfp2.GetDeviceCount()
    #     if device_count > 0:
    #         zkfp2.OpenDevice(0)
    #         print("Dispositivo lector detectado \n Ingrese su huella. \n")
    #         while True:
    #             capture = zkfp2.AcquireFingerprintImage()
    #             if capture:
    #                 break
    #         print("Huella escaneada \n")
    #         a, b = find_sizeReader(len(capture))
    #         unprocessed = np.frombuffer(capture, dtype=np.uint8).reshape(a, b)  
    #         processed = self.preprocess_picture(unprocessed)
            # filename = f"received_fingerprints/image_subject.png"
            # if os.path.exists(filename):
            #     try:
            #         os.remove(filename)
            #         print(f"Existing file {filename} deleted.")
            #     except Exception as e:
            #         print(f"Error deleting existing file: {e}")
            # try:
            #     cv2.imwrite(filename, processed)
            #     print(f"Saved fingerprint image to {filename}")
            # except Exception as e:
            #     print(f"Error saving image: {e}")
            # return processed

    def extract_embedding(self):
        vector = self.extractor.extraction_reader()
        return vector

    def insert_embedding(self, vector, pas_id): 
        conn = self.conn
        cur = self.cur
        subject_in_database = 0
        impression = 0
        embedding = vector[1]
        
        try:
            cur.execute("""
                INSERT INTO fingerprints (pas_id, impression, embedding, database_name, subject_in_database)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (pas_id) DO NOTHING
            """, (
                pas_id, 
                impression, 
                embedding.tolist(), 
                "reader", 
                subject_in_database
            ))
            
            if cur.rowcount > 0:
                conn.commit()
                print(f"Successfully registered fingerprint for pas_id: {pas_id}")
                return True
            else:
                print(f"Failed to insert - pas_id {pas_id} may already exist")
                return False
                
        except Exception as e:
            print(f"Error inserting pas_id {pas_id}: {e}")
            conn.rollback()
            return False
        
    def search_fingerprint_db(self, query_embedding, top_k):
        cur = self.cur
        try:
            cur.execute("""
                SELECT 
                    id,
                    pas_id,
                    impression,
                    subject_in_database,
                    database_name,
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
            match = False
            counter = 0
            for row in cur.fetchall():
                if counter == 0: 
                    pas_id = int(row[1])
                    similarity = row[5]
                results.append({
                    'id': row[0],                    
                    'pas_id': row[1],                
                    'impression': row[2],            # Impression number
                    'subject_in_database': row[3],   # Original subject ID in source database
                    'database_name': row[4],         # Which database it came from
                    'similarity': row[5],            
                    'distance': row[6]               
                })
                counter +=1
            if similarity > 0.819: 
                match = True 
            
            # Print results in a more readable format
            print(f"\nTop {len(results)} matches:\n")
            for i, result in enumerate(results, 1):
                print(f"{i}. Pas_ID: {result['pas_id']}, "
                    f"Similarity: {result['similarity']:.4f}, "
                    f"Database: {result['database_name']}")
            
            return pas_id, match
            
        except Exception as e:
            print(f"Error searching fingerprints: {e}")
            return []

    def check_pas_id_exists(self, pas_id):
        self.cur.execute("SELECT EXISTS(SELECT 1 FROM fingerprints WHERE pas_id = %s)", (pas_id,))
        return self.cur.fetchone()[0]


    def initiate_with_pc(self):
        flag = False 
        pas_id = None
        if self.state: 
            while not flag:
                    try:
                        pas_id = int(input("Ingrese el passenger id : "))
                        # Check if pas_id already exists
                        if self.check_pas_id_exists(pas_id):
                            print(f"El ID {pas_id} ya está registrado. Por favor elija otro ID.")
                            continue
                        flag = True
                    except ValueError:
                        print("Por favor ingrese un ID válido (número entero)")
                    except Exception as e:
                         print(f"error {e}")
                         return {
                            "success": False,
                            "error": f"error: {e}"
                        }
                    

        vector = self.extract_embedding()
        if self.state and pas_id is not None: 
            success = self.insert_embedding(vector, pas_id)
            if success:
                return {
                "success": True,
                "message": "\n¡Gracias por registrarse!"
             } 
            else:
                 return {
                "success": False,
                "error": "Intente nuevamente"
            }
                
        else:
            self.state = False
            print("\nBuscaremos si la huella existe en la base de datos: \n")
            pas_id, match = self.search_fingerprint_db(vector[1], 1)
            if (match): 
                print(f"Huella encontrada, pas_id: {pas_id}")
                return True
                token ="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJhbnRvbmlvZ3VlcnJhMTZAeW9wbWFpbC5jb20iLCJyb2xlcyI6IlBBU1NFTkdFUiIsImlzcyI6Imh0dHA6Ly9lbHAtYXBpLWRldi5zb3V0aGFtZXJpY2EtZWFzdDEtYS5jLmVuLWxhLXBhcmFkYS1wcm9kLmludGVybmFsOjkwMDEvYXBpL3YxL2F1dGgvbG9naW4vc2lnbmluIiwiZXhwIjo0OTA5NzQ4NjM2fQ.AoibrHAYqo6fVYmpxyuj4nQiuG8D7YZ7W5a7p2_Hlv4" 
                response = self.payment_validator.validate_payment(token,pas_id)
                if response['success']: 
                    return {
                    "success": True,
                    "message": "\n¡Pase adelante!",
                    "pasId": pas_id
                        } 
                else: 
                    print(response["error"])
                    return {
                    "success": False,
                    "error": response["error"]
                }
            else: 
                print("no huella")
                return {
                    "success": False,
                    "error": "No se ha encontrado huella"
                }
  

    def initiate(self): 
        flag = False 
        pas_id = None
        if self.state: 
            while not flag:
                    try:
                        pas_id = int(input("Ingrese el passenger id : "))
                        # Check if pas_id already exists
                        if self.check_pas_id_exists(pas_id):
                            print(f"El ID {pas_id} ya está registrado. Por favor elija otro ID.")
                            continue
                        flag = True
                    except ValueError:
                        print("Por favor ingrese un ID válido (número entero)")
                    except Exception as e:
                        print(f"error {e}")
                        return {
                            "success": False,
                            "error": f"error: {e}"
                        }
                    
        finger = self.get_fingerprint()
        if finger is None:  
                return {
                "success": False,
                "error": "Intente nuevamente"
            }
        vector = self.extract_embedding()
        if self.state and pas_id is not None: 
            success = self.insert_embedding(vector, pas_id)
            if success:
                return {
                "success": True,
                "message": "\n¡Gracias por registrarse!", 
                "pas_id": pas_id,
             } 
            else:
                return {
                "success": False,
                "error": "Intente nuevamente"
            }
                
        else:
            self.state = False
            print("\nBuscaremos si la huella existe en la base de datos: \n")
            pas_id, match = self.search_fingerprint_db(vector[1], 5)
            if (match): 
                print(f"Huella encontrada, pas_id: {pas_id}")
                token ="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJhbnRvbmlvZ3VlcnJhMTZAeW9wbWFpbC5jb20iLCJyb2xlcyI6IlBBU1NFTkdFUiIsImlzcyI6Imh0dHA6Ly9lbHAtYXBpLWRldi5zb3V0aGFtZXJpY2EtZWFzdDEtYS5jLmVuLWxhLXBhcmFkYS1wcm9kLmludGVybmFsOjkwMDEvYXBpL3YxL2F1dGgvbG9naW4vc2lnbmluIiwiZXhwIjo0OTA5NzQ4NjM2fQ.AoibrHAYqo6fVYmpxyuj4nQiuG8D7YZ7W5a7p2_Hlv4" 
                response = self.payment_validator.validate_payment(token,pas_id)
                if response['success']: 
                    return {
                    "success": True,
                    "message": "\n¡Pase adelante!",
                    "pas_id": pas_id
                        } 
                else: 
                    print(response["error"])
                    return {
                    "success": False,
                    "error": response["error"]
                }
            else: 
                print("no huella")
                return {
                    "success": False,
                    "error": "No se ha encontrado huella"
                }
  


