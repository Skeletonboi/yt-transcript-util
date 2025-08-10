import json

def save_vids_dic(vids_dic, savepath):
    """ Save transcript dictionary to JSON file """
    with open(savepath, 'w') as file:
        json.dump(vids_dic, file)
        print("Saved file.")
    return

def load_vids_dic(savepath) -> dict:
    """ Loads transcript dict file (if exists) to memory """
    try:
        with open(savepath, "r", encoding="utf-8") as file:
            file_contents = json.load(file)
    except Exception as e:
        file_contents = {}

    return file_contents