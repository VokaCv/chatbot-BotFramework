# -*- coding: utf-8 -*-
# +
import sys
import os
import json
from collections import defaultdict
from datetime import datetime
import tempfile
import subprocess
import random

import numpy as np
import pandas as pd

import matplotlib.pyplot as plt
import seaborn as sns

from tqdm.notebook import tqdm

import joblib

import ipywidgets as widgets
from IPython.display import display
import markdown

from azureml.core import Workspace, Dataset

from dotenv import load_dotenv, set_key

from github import Github

sys.path.append("../")
from P10_02_luis.utils import *

# +
# On définit les variables globales
JSON_PATH = "data/json/"
PARQUET_PATH = "data/parquet/"

os.makedirs(JSON_PATH, exist_ok=True)
os.makedirs(PARQUET_PATH, exist_ok=True)

RANDOM_SEED = 42


# -

def copy_and_clean_notebooks():
    """Copie les notebooks et supprime les sorties."""
    
    # On récupère la liste des notebooks à convertir (avec les sorties)
    file_names = os.listdir()
    notebooks = [
        f.replace(".ipynb", "") for f in file_names
        if f.endswith(".ipynb") and not f.endswith("no_out.ipynb")
    ]
    
    for n in notebooks:
        # On crée un version nettoyée du notebook (sans les sorties)
        args = f"jupyter nbconvert --clear-output --to notebook --output {n}_no_out {n}.ipynb".split()
        subprocess.run(args)


def turn_to_luis_utterance(turn: dict, intent_name: str, label_to_entity: dict) -> dict:
    """Convertit un turn du jeu de données en une utterance labellisée pour LUIS."""
    
    text = turn["text"]
    
    # Intent par défaut
    intent = "None"

    entity_labels = []
    for i in turn["labels"]["acts_without_refs"]:
        for l in i["args"]:
            k = l["key"]
            v = l["val"]
            
            if k == "intent":
                # Si il y a le label "intent", il s'agit d'une demande
                # de réservation.
                intent = intent_name
            elif k and v:
                # Les autres labels sont des entités
                if k in label_to_entity.keys():
                    start_char_index = text.lower().find(v.lower())
                    if start_char_index == -1:
                        continue
                    
                    end_char_index = start_char_index + len(v) - 1
                    
                    # On met en forme l'entité au format LUIS
                    entity_labels.append({
                        "entity": label_to_entity[k],
                        "startPos": start_char_index,
                        "endPos": end_char_index,
                        "children": []
                    })
    
    # On met en forme le texte labellisé au format LUIS
    res = {
        "text": text,
        "intent": intent,
        "entities": entity_labels,
    }
    return res


def user_turns_to_luis_ds(
    frames: list,
    intent_name: str,
    label_to_entity: dict
) -> pd.DataFrame:
    """Convertit les turns utilisateur du jeu de données pour LUIS."""
    
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


class AppInsightsAPIEnv:
    def __init__(self, env_file_path: str=""):
        # On charge le fichier des variables d'environnement
        if env_file_path:
            load_dotenv(env_file_path, override=True)

        # On charge les variables d'environnement
        self.APP_INSIGHTS_API_ID = os.getenv("APP_INSIGHTS_API_ID")
        self.APP_INSIGHTS_API_KEY = os.getenv("APP_INSIGHTS_API_KEY")


def get_tn_dialogs(env: AppInsightsAPIEnv, start_dt: str, end_dt: str) -> pd.DataFrame:
    """Récupère les dialogues des TN"""
    
    # On crée la requête en Kusto Query Language
    query = f"""customEvents
| where name == 'TN'
| where timestamp > datetime('{start_dt}') and timestamp < datetime('{end_dt}')
| extend mainDialogUuid = tostring(customDimensions['mainDialogUuid'])
| project mainDialogUuid
| join kind=rightsemi (
    customEvents
    | extend mainDialogUuid = tostring(customDimensions['mainDialogUuid'])
    | extend text = tostring(customDimensions['text'])
    | where text != ""
    | extend fromName = tostring(customDimensions['fromName'])
    | project mainDialogUuid, timestamp, fromName, session_Id, text
) on mainDialogUuid
| sort by mainDialogUuid asc, timestamp asc
"""
    
    # On envoie la requête
    response = requests.post(
        url=f"https://api.applicationinsights.io/v1/apps/{env.APP_INSIGHTS_API_ID}/query",
        headers={
            "X-Api-Key": env.APP_INSIGHTS_API_KEY,
        },
        json={"query": query}
    )
    
    # On vérifie la réponse
    check_response_ok_or_raise_for_status(response)
    
    # On récupère les données
    res = response.json()
    
    # On crée un dataframe à partir des données
    res = pd.DataFrame(res["tables"][0]["rows"])
    res.columns = ["main_dialog_uuid", "timestamp", "author", "session_id", "text"]
    res["timestamp"] = pd.to_datetime(res["timestamp"])
    
    # On renvoie le résultat
    return res


class InsatisfactionsAnalyser:
    """Outil interactif permettant de visualiser et d'analyser les dialogues qui
    sont sources d'insatisfactions.
    
    Cet outil utilise les ipywidgets.
    """
    
    def __init__(self, data: pd.DataFrame, res: pd.DataFrame=None):
        self.data = data.groupby("main_dialog_uuid")
        
        self.error_types = ["unknown", "luis", "chatbot"]
        
        if res is None:
            self.res = data.groupby("main_dialog_uuid", as_index=False).agg({
                "timestamp": ["min", "max"],
                "session_id": "first",
                "text": "count",
            })
            self.res.columns = [
                "main_dialog_uuid",
                "timestamp_min",
                "timestamp_max",
                "session_id",
                "text_nb"
            ]
            self.res["error_type"] = ""
            self.res["comment"] = ""
            self.res["utterances"] = ""
        else:
            self.res = res
        
        self.uuids = self.res["main_dialog_uuid"].to_list()
        
        self.idx = 0
        self.idx_min = 0
        self.idx_max = len(self.uuids) - 1
        
        self.dialog_vbox = widgets.VBox(layout=widgets.Layout(
            width="60%",
            height="300px",
            display="block",
            overflow_y='auto',
            border="1px solid black"
        ))
        
        self.comment_label = widgets.Label("Comment")
        self.comment_text = widgets.Textarea(
            placeholder="Add a comment, bug description or new feature request.",
            layout=widgets.Layout(
                width="95%",
                height="95px"
            )
        )
        
        self.utterances_label = widgets.Label("LUIS utterances")
        self.utterances_text = widgets.Textarea(
            placeholder="Add LUIS utterances to add to the training set.",
            layout=widgets.Layout(
                width="95%",
                height="95px"
            )
        )
        
        self.prev_button = widgets.Button(
            description="",
            icon="arrow-left"
        )
        
        self.error_type_sel = widgets.Dropdown(
            options=self.error_types,
            value=None,
            description="Error type:"
        )

        self.next_button = widgets.Button(
            description="",
            icon="arrow-right"
        )
        
        self.options_hbox = widgets.HBox([
            self.prev_button,
            self.error_type_sel,
            self.next_button
        ], layout=widgets.Layout(
            width="95%"
        ))
        
        self.analysis_vbox = widgets.VBox([
            self.comment_label,
            self.comment_text,
            self.utterances_label,
            self.utterances_text,
            self.options_hbox
        ], layout=widgets.Layout(
            width="40%",
            height="300px",
            display="flex",
            justify_content="space-between"
        ))
        
        self.analyser = widgets.HBox([self.dialog_vbox, self.analysis_vbox])
        
        self.prev_button.on_click(self.on_prev_button_clicked)
        self.next_button.on_click(self.on_next_button_clicked)
        self.error_type_sel.observe(self.on_error_type_sel_change, names="value")
        self.comment_text.observe(self.on_comment_text_change, names="value")
        self.utterances_text.observe(self.on_utterances_text_change, names="value")
        
        self.update_all()
        
    def on_prev_button_clicked(self, b):
        if self.idx > self.idx_min:
            self.idx -= 1

        self.update_all()
        
    def on_next_button_clicked(self, b):
        if self.idx < self.idx_max:
            self.idx += 1

        self.update_all()
        
    def on_error_type_sel_change(self, value: dict):
        self.res.loc[self.idx, "error_type"] = value["new"]
        self.update_error_type_sel()
        
    def on_comment_text_change(self, value: dict):
        self.res.loc[self.idx, "comment"] = value["new"]
        self.update_comment_text()
        
    def on_utterances_text_change(self, value: dict):
        self.res.loc[self.idx, "utterances"] = value["new"]
        self.update_utterances_text()
        
    def update_all(self):
        self.update_dialog_vbox()
        self.update_buttons()
        self.update_error_type_sel()
        self.update_comment_text()
        self.update_utterances_text()
        
    def update_buttons(self):
        if self.idx <= self.idx_min:
            self.prev_button.disabled = True
        else:
            self.prev_button.disabled = False

        if self.idx >= self.idx_max:
            self.next_button.disabled = True
        else:
            self.next_button.disabled = False
        
    def update_dialog_vbox(self):
        data = self.data.get_group(self.uuids[self.idx])
        texts = []
        for i, row in data.iterrows():
            if row["author"] == "p10-chatbot-bot":
                layout = widgets.Layout(justify_content="flex-end")
            else:
                layout = widgets.Layout(justify_content="flex-start")

            text = row["text"].replace("\n", "\n\r")
            texts.append(widgets.HBox([widgets.HTML(
                markdown.markdown(text),
                layout=widgets.Layout(
                    max_width="70%",
                    border="1px solid black",
                    padding="5px",
                    margin="10px 5px 10px 5px"
                ))], layout=layout))

        self.dialog_vbox.children = texts
        
    def update_error_type_sel(self):
        value = self.res.loc[self.idx, "error_type"]
        self.error_type_sel.value = value if value != "" else None
        
    def update_comment_text(self):
        value = self.res.loc[self.idx, "comment"]
        self.comment_text.value = value
        
    def update_utterances_text(self):
        value = self.res.loc[self.idx, "utterances"]
        self.utterances_text.value = value
        
    def display(self):
        display(self.analyser)
        
    def save(self, dir_path: str, name: str):
        # On enregistre les données. "coerce_timestamps" permet de conserver
        # le type datetime dans les métadonnées du fichier parquet.
        file_path = os.path.join(dir_path, f"{name}_data.parquet")
        self.data.obj.to_parquet(
            file_path,
            index=False,
            coerce_timestamps="ms",
            allow_truncated_timestamps=True
        )
        
        file_path = os.path.join(dir_path, f"{name}_res.parquet")
        self.res.to_parquet(
            file_path,
            index=False,
            coerce_timestamps="ms",
            allow_truncated_timestamps=True
        )
        
    @classmethod
    def load(cls, dir_path: str, name: str):
        # On crée les chemins vers les fichiers
        data_file_path = os.path.join(dir_path, f"{name}_data.parquet")
        res_file_path = os.path.join(dir_path, f"{name}_res.parquet")
        
        # On vérifie si les fichiers existent
        if not os.path.exists(data_file_path):
            print("Missing file:", data_file_path)
            return None
        
        if not os.path.exists(res_file_path):
            print("Missing file:", res_file_path)
            return None
        
        # On charge les données.
        data = pd.read_parquet(data_file_path)
        res = pd.read_parquet(res_file_path)
        
        # On initialise l'analyser avc les nouvelles données
        return cls(data, res)
        
    def get_report(self, issue_ids: list):
        report = "## Introduction\n\n"
        report += "Analyse des issues : " + ", ".join(issue_ids)

        report += "\n\n## Distribution des erreurs\n\n"

        tmp = self.res["error_type"].value_counts().to_frame("error_nb")
        tmp["%"] = self.res["error_type"].value_counts(normalize=True)
        tmp.index.name = "error_type"

        report += tmp.to_html(float_format=lambda x: f"{x:0.2f}")

        report += "\n\n## Commentaires\n\n"

        for comment in self.res["comment"]:
            if comment:
                report += comment + "\n"

        report += "\n## Textes à labelliser pour LUIS\n\n"

        for utterances in self.res["utterances"]:
            if utterances:
                report += utterances + "\n"

        return report


def get_texts_from_dataset(utterances_train: list, utterances_test: list, intent: str):
    """Extraction des utterances du jus de données"""
    
    # Utterances du jeu d'entrainement
    texts = list(filter(
        lambda x: x["intent"] == intent,
        utterances_train
    ))

    # Utterances du jeu de test
    texts += list(filter(
        lambda x: x["intent"] == intent,
        utterances_test["LabeledTestSetUtterances"]
    ))

    # Extraction des textes
    texts = [i["text"] for i in texts]
    
    return texts


def texts_to_luis_utterances(texts: list, intent_name: str) -> list:
    """Convertit des textes en des utterances pour LUIS."""
    
    utterances = []
    for text in texts:
        utterances.append({
            "text": text,
            "intent": intent_name,
            "entities": []
        })
        
    return utterances


class GithubAPIEnv:
    def __init__(self, env_file_path: str=""):
        # On charge le fichier des variables d'environnement
        if env_file_path:
            load_dotenv(env_file_path, override=True)

        # On charge les variables d'environnement
        self.GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
        self.GITHUB_REPO = os.getenv("GITHUB_REPO")
