import os 
PIC_PATH: str = r"C:\Users\sofic\OneDrive\Documentos\Work\Development\Databases\UareU"
counter_subjects = 0
person = 0
counter_fingers = 0
for file in os.listdir(PIC_PATH): 
    name_without_ext = file.replace('.tif', '')
    iden_list = name_without_ext.split("_")
    subject = int(iden_list[0])
    finger =  int(iden_list[1])
    impression = int(iden_list[2])
    if (person != subject + finger): 
        counter_subjects+=1
        print(f"{file} - {subject} - {finger} - {impression}")
        person = subject + finger

print(f"Final subject number: {counter_subjects}")

# PIC_PATH: str = r"C:\Users\sofic\OneDrive\Documentos\Work\Development\minex\minexiii\validation\validation_imagery_raw"
# counter = 0
# person = 0
# counter_fingers = 0
# for file in os.listdir(PIC_PATH): 
#     current_path = os.path.join(PIC_PATH, file)
#     if file[0] == "a" or  file[0] == "b": 
#         if (person !=int(file[1:4])):
#             print(f"\nperson: {person}, finger: {counter_fingers}\n")
#             counter_fingers = 0
#             person = int(file[1:4])
#         if counter < 10: 
#             file_new = f"{file[0]}00{counter}{file[-5:]}"
#         elif counter < 100: 
#             file_new = f"{file[0]}0{counter}{file[-5:]}"
#         else:   
#              file_new = f"{file[0]}{counter}{file[-5:]}"
#         print(f"old file: {file} new file: {file_new}")
#         counter_fingers +=1
#         if counter == 396: 
#             counter = 0
#         else: 
#             counter +=1
#         new_path = os.path.join(PIC_PATH, file_new)
#         os.rename(current_path, new_path)
# print(counter)