import os,json,requests, time
from dotenv import load_dotenv
from pathlib import Path

from azure.cognitiveservices.language.luis.authoring import LUISAuthoringClient
from azure.cognitiveservices.language.luis.authoring.models import ApplicationCreateObject, AzureAccountInfoObject, LuisApp
from azure.cognitiveservices.language.luis.runtime import LUISRuntimeClient
from msrest.authentication import CognitiveServicesCredentials

import pandas as pd

class LuisEnv:
    def __init__(self):
        path = str(Path(os.path.realpath(__file__)).parent)
        load_dotenv(Path(path, '.env'), override=True)
        # On charge les variables d'environnement
        self.LUIS_AUTH_KEY = os.environ.get("LUIS_AUTH_KEY")
        self.LUIS_AUTH_ENDPOINT = os.environ.get("LUIS_AUTH_ENDPOINT")

        self.LUIS_PRED_KEY = os.environ.get("LUIS_PRED_KEY")
        self.LUIS_PRED_ENDPOINT = os.environ.get("LUIS_PRED_ENDPOINT")

        self.LUIS_APP_ID = os.environ.get("LUIS_APP_ID")


def turn_to_luis_utterance(turn, intent_name, label_to_entity):
    """Transform turn to labelled utterance for LUIS."""
    text = turn["text"]
    # Intent par défaut
    intent = "None"

    entity_labels = []
    for i in turn["labels"]["acts_without_refs"]:
        for j in i["args"]:
            k = j["key"]
            v = j["val"]
            
            if k == "intent":
                intent = intent_name
            elif k and v:
                # Les autres labels sont des 'entities'
                if k in label_to_entity.keys():
                    start_char_index = text.lower().find(v.lower())
                    if start_char_index == -1:
                        continue
                    
                    end_char_index = start_char_index + len(v) - 1
                    
                    # On met en forme l'entité au format LUIS
                    entity_labels.append({
                        "entity": label_to_entity[k], #entityName if unique entry add, entity if batch
                        "startPos": start_char_index, #startCharIndex if unique entry add, entity if batch
                        "endPos": end_char_index, #endCharIndex if unique entry add, entity if batch
                        "children": []
                    })
    
    # On met au format LUIS
    res = {
        "text": text,
        "intent": intent,
        "entities": entity_labels,
    }
    
    # # On met au format LUIS
    # res = {
    #     "text": text,
    #     "intentName": intent,
    #     "entityLabels": entity_labels,
    # }

    return res

def user_turns_to_luis_ds(frames,intent_name,label_to_entity, keep_only_first=True):
    'frames -> list'
    'intent -> str'
    'label -> list'

    """Transform turns to LUIS dataset"""
    
    res = []
    # Pour chaque dialogue
    for frame in frames:
        # On crée un id pour identifier les tours de chaque dialogue
        user_turn_id = 0
        
        # Pour chaque tour du dialogue
        for turn in frame["turns"]:
            # On vérifie si il s'agit bien de l'utilisateur
            if turn["author"] == "user":
                # On ajoute l'id du tour
                row = {"user_turn_id": user_turn_id}
                user_turn_id += 1
                
                # On ajoute l'utterance au format LUIS
                row.update(turn_to_luis_utterance(turn, intent_name, label_to_entity))
                
                # On ajoute le résultat à la liste
                res.append(row)

                if keep_only_first:
                    break
    
    # On convertit les données en DataFrame
    df = pd.DataFrame(res)
    
    # On ajoute le nombre d'entitées labellisées dans le texte
    df["entity_total_nb"] = df["entities"].apply(len)
    
    # Pour chaque entitée, on ajoute le nombre de fois qu'elle apparait
    for entity_name in label_to_entity.values():
        df[f"{entity_name}_nb"] = df["entities"].apply(
            lambda x: len(list(
                filter(lambda x1: x1["entity"] == entity_name, x)
            ))
        )
    
    # On ajoute le nombre de mot dans le texte
    df["text_word_nb"] = df["text"].apply(lambda x: len(x.split()))
    
    return df

def check_response_ok_or_raise_for_status(response):
    # On génère une exception en cas d'erreur
    if not response.ok:
        print(response.content)
        response.raise_for_status()

def get_latest_version(env):
            # On envoie la requête permettant d'exporter le modèle au format json
    response = requests.get(
        url=f"{env.LUIS_AUTH_ENDPOINT}luis/authoring/v3.0-preview/apps/{env.LUIS_APP_ID}/versions?skip=0&take=100",
            headers={
                "Ocp-Apim-Subscription-Key": env.LUIS_AUTH_KEY,
            }
    )
    # On vérifie la réponse
    check_response_ok_or_raise_for_status(response)
    
    # On renvoie la dernière version (premier dans la liste de response)
    latest = response.json()[0]['version']
    return float(latest)

def get_params(env, app_version):
    """Renvoie les paramètres de LUIS"""
   
    # On envoie la requête permettant d'exporter le modèle au format json
    response = requests.get(
        url=f"{env.LUIS_AUTH_ENDPOINT}luis/authoring/v3.0-preview/apps/{env.LUIS_APP_ID}/versions/{app_version}/export",
        params={
            "format": "json"
        },
        headers={
            "Ocp-Apim-Subscription-Key": env.LUIS_AUTH_KEY,
        }
    )
    
    # On vérifie la réponse
    check_response_ok_or_raise_for_status(response)
    
    # On renvoie les paramètres
    return response.json()

def create_new_version(env, app_version, app_params, app_utterances=[]):
    """Créer une nouvelle version"""
    
    # On ajoute les utterances aux paramètres de l'application
    app_params_tmp = app_params.copy()
    app_params_tmp["utterances"] += app_utterances
    
    # On envoie la requête permettant de créer la nouvelle version
    response = requests.post(
        url=f"{env.LUIS_AUTH_ENDPOINT}luis/authoring/v3.0-preview/apps/{env.LUIS_APP_ID}/versions/import",
        params={
            "versionId": app_version,
        },
        headers={
            "Ocp-Apim-Subscription-Key": env.LUIS_AUTH_KEY,
        },
        json=app_params_tmp
    )
    
    # On vérifie la réponse
    check_response_ok_or_raise_for_status(response)


def train_luis(env, app_version, check_status_period=5):
    """Entrainement du modèle LUIS"""
    
    # On crée le client avec les informations d'authentification
    client = LUISAuthoringClient(env.LUIS_AUTH_ENDPOINT, CognitiveServicesCredentials(env.LUIS_AUTH_KEY))

    # On entraine le modèle
    client.train.train_version(env.LUIS_APP_ID, app_version)
    
    # On attend la fin de l'entrainement
    waiting = True
    while waiting:
        # On demande le status de l'entrainement
        info = client.train.get_status(env.LUIS_APP_ID, app_version)

        # On vérifie si l'entrainement est en attente ou en cours d'exécution
        waiting = any(map(lambda x: 'Queued' == x.details.status or 'InProgress' == x.details.status, info))
        
        if waiting:
            time.sleep(check_status_period)
        else: 
            print ("trained")
            waiting = False

def deploy_luis(env, app_version, is_staging=True):
    """Déploiement du modèle LUIS"""   
    # On crée le client avec les informations d'authentification
    client = LUISAuthoringClient(env.LUIS_AUTH_ENDPOINT, CognitiveServicesCredentials(env.LUIS_AUTH_KEY))
    # On publie l'app

    # Mark the app as public so we can query it using any prediction endpoint.
    # Note: For production scenarios, you should instead assign the app to your own LUIS prediction endpoint. See:
    # https://docs.microsoft.com/en-gb/azure/cognitive-services/luis/luis-how-to-azure-subscription#assign-a-resource-to-an-app
    # client.apps.update_settings(env.LUIS_APP_ID, is_public=True)

    staging = is_staging
    client.apps.publish(env.LUIS_APP_ID, app_version, is_staging=staging)
    
def get_prediction_luis(env, is_staging, utterance):
    """Renvoie une prédiction LUIS"""
    
    # On définie le slot à tester
    if is_staging:
        slots = "Staging"
    else:
        slots = "Production"
    
    # On crée le client 
    clientRuntime = LUISRuntimeClient(env.LUIS_PRED_ENDPOINT, 
                CognitiveServicesCredentials(env.LUIS_PRED_KEY))

    # On effectue la prédiction
    pred = clientRuntime.prediction.get_slot_prediction(
        env.LUIS_APP_ID,
        slots,
        {"query" : [utterance]}
    )
    
    return pred.as_dict()

def delete_luis(env, app_version):
    """Suppression de l'application"""
    
    # On crée le client avec les informations d'authentification
    client = LUISAuthoringClient(env.LUIS_AUTH_ENDPOINT, 
        CognitiveServicesCredentials(env.LUIS_AUTH_KEY))

    # On supprime l'app
    client.versions.delete(env.LUIS_APP_ID, app_version)

def get_utterances(env, app_version):
    """Renvoie les utterances de la version demandée de LUIS"""
    params = get_params(env, app_version)
   
    return params["utterances"]    

def evaluate(env, is_staging, utterances, check_status_period=5):
    """Evaluation sur un jeu de test"""
    
    # On définie le slot à tester
    if is_staging:
        slots = "staging"
    else:
        slots = "production"
    
    # On envoie la requête permettant de lancer l'évaluation
    response = requests.post(
        url=f"{env.LUIS_PRED_ENDPOINT}luis/v3.0-preview/apps/{env.LUIS_APP_ID}/slots/{slots}/evaluations",
        headers={
            "Ocp-Apim-Subscription-Key": env.LUIS_PRED_KEY,
        },
        json=utterances
    )
    
    # On vérifie la réponse
    check_response_ok_or_raise_for_status(response)
    
    # On récupère l'id de l'opération
    operation_id = response.json()["operationId"]
    
    waiting = True
    while waiting:
        # On check le status
        response = requests.get(
            url=f"{env.LUIS_PRED_ENDPOINT}luis/v3.0-preview/apps/{env.LUIS_APP_ID}/slots/{slots}/evaluations/{operation_id}/status",
            headers={
                "Ocp-Apim-Subscription-Key": env.LUIS_PRED_KEY,
            }
        )
        
        # On vérifie s'il y a une erreur
        if response.json()["status"] == "failed":
            raise ValueError(response.content)
        
        waiting = response.json()["status"] in ["notstarted", "running"]
        
        if waiting:
            time.sleep(check_status_period)
        
    # On récupère les résultats de l'évaluation
    response = requests.get(
        url=f"{env.LUIS_PRED_ENDPOINT}luis/v3.0-preview/apps/{env.LUIS_APP_ID}/slots/{slots}/evaluations/{operation_id}/result",
        headers={
            "Ocp-Apim-Subscription-Key": env.LUIS_PRED_KEY,
        }
    )
    
    # On vérifie la réponse
    check_response_ok_or_raise_for_status(response)
    
    # On récupère les résultats
    resultat = response.json()
    
    # On met en forme les résultats dans un DataFrame
    resultat = pd.DataFrame(resultat["intentModelsStats"] + resultat["entityModelsStats"])
    resultat.iloc[:, -3:] = resultat.iloc[:, -3:].astype(float)
    resultat.columns = [
        "model_name",
        "model_type",
        f"precision",
        f"recall",
        f"f_score",
    ]
    
    return resultat