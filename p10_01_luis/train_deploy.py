# -*- coding: utf-8 -*-
import os
import json
import tempfile
import argparse

from azureml.core import Workspace, Dataset

from utils import *

import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent paskage to sys.path so it can be imported (in child folder)
def find_pckg(pckg_name, starting_point=""):  
    if starting_point == "":
        starting_point =  str(Path(os.path.realpath(__file__)).parent)       
    
    found_in = starting_point

    while not pckg_name in os.listdir(found_in):
        found_in_before = found_in
        found_in = Path(found_in).parent

        if found_in_before == found_in:
            return None

    if found_in not in sys.path:
        sys.path.append(str(found_in))        
    return str(found_in)

# name of the package to add
path = find_pckg("p10_00_helper_func")
# once added we can import it here
from p10_00_helper_func import azure_helper


if __name__ == "__main__":
    # On récupère les arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--is_staging", type=int, default=1)
    args = parser.parse_args()
    
    
    print("Chargement des variables d'environement.")   
    env = LuisEnv()
    print('LUIS ENV APP ID', env.LUIS_APP_ID)
    
    
    print("Chargement du workspace.")
    # On charge l’espace de travail Azure ML
    ws = azure_helper.get_ws()
    print('WPORKSPAVCE', ws)
    
    # print("Chargement des paramètres du modèle.")
    # latest_version = get_latest_version(env)
    # params = get_params(env, latest_version)
        
    # # model_version = str(params["model"]["versionId"])
    # # ds_name = params["dataset"]["name"]
    # # ds_version = params["dataset"]["version"]
        
    # print("Chargement des jeux de données.")
    
    # dataset = Dataset.get_by_name(ws, 'utterances')
    # dataset.download(target_path='.', overwrite=True)
        
    # # On charge le jeu d'entrainement
    # file_path = os.path.join('.', "utterances_train.json")
    # with open(file_path) as f:
    #     utterances_train = json.load(f)
    
    # file_path1 = os.path.join('.', "utterances_test.json")
    # with open(file_path1) as f:
    #     utterances_test= json.load(f)

    # os.remove(file_path)
    # os.remove(file_path1)
    
    # # # On crée le nom de version du modèle
    # app_version = round(float(latest_version+0.1),2)    
    # print(f"Création de la version {app_version}.")
   
    # create_new_version(env, app_version, params, utterances_train)
    
    # print(f"Entrainement du modèle...")    
    # train_luis(env, app_version)
    
    # print(f"Déploiement du modèle...")    
    # if args.is_staging == 1:
    #     slots = "staging" 
    # else:
    #     slots = "production"

    # deploy_luis(env, app_version, is_staging=slots)
    

    # print(f"Evaluation du modèle...")
    # res = evaluate(env, True, utterances_test)
    # # On affiche les résultats
    # print(res.to_markdown())
    
    # # # On supprime le modèle si besoin
    # # if args.is_staging == 1:
    # #     print("Suppression du modèle.")
    # #     delete_luis(env, app_version)
