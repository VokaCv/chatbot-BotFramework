# Chatbot with Azure Bot Framework

# Introduction

Ce projet est une MVP chatbot pour la réservation de voyage.

Son objectif c'est de permettre de détecter les entités de language suivantes: 
- Ville de départ et de destination
- Dates d'aller et retour
- Budget maximum

Le chatbot est développé en tant que dialogue en cascade,  c'est à dire que le dalogue est sequentiel et que le bot va poser des questions à l’utilisateur afin de comprendre sa demande. Tant que l'information nécessaire n'est pas disponible au bot, il réitère sa question. Quand il pense avoir compris toutes les briques nécessaires, il refolrmule la demande et demande une confirmation à l'utilisateur.


# Architecture du projet

L'ensemble du projet est développer sur Azure donc pour consommer ce git il faut avoir un compte Azure et Github.

pour plus de détails sur l'utilisation de Microsoft Azure voir:
1. [LUIS AI reconnaissance de texte](https://docs.microsoft.com/fr-fr/azure/cognitive-services/luis/)
2. [Bot Framework](https://docs.microsoft.com/fr-fr/azure/bot-service/index-bf-sdk?view=azure-bot-service-4.0)
3. [App Insight pour le suivi de performances](https://docs.microsoft.com/fr-fr/azure/azure-monitor/app/app-insights-overview)

## Déploiement 

Le modèle LUIS ainsi que le bot framework sont déployés à partir des Git actoins.