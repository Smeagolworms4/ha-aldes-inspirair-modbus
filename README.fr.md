# Aldes InspirAIR Top (Modbus) — intégration Home Assistant

[!["Buy Me A Coffee"](https://raw.githubusercontent.com/Smeagolworms4/donate-assets/master/coffee.png)](https://www.buymeacoffee.com/smeagolworms4)
[!["Buy Me A Coffee"](https://raw.githubusercontent.com/Smeagolworms4/donate-assets/master/paypal.png)](https://www.paypal.com/donate/?business=SURRPGEXF4YVU&no_recurring=0&item_name=Hello%2C+I%27m+SmeagolWorms4.+For+my+open+source+projects.%0AThanks+you+very+mutch+%21%21%21&currency_code=EUR)

*Lire ceci en [anglais](README.md).*

Intégration pour la VMC double flux **Aldes InspirAIR® Top**, via son **port
Modbus intégré**. Entièrement locale : ni boîtier AldesConnect, ni compte cloud,
ni API distante à interroger — et bien plus de données que l'application Aldes
n'en a jamais montré : les quatre températures d'air, les débits réels, la
position du bypass, le décompte des filtres, les codes défaut, les moteurs.

![hacs](https://img.shields.io/badge/HACS-custom%20repository-41BDF5)
![iot class](https://img.shields.io/badge/IoT%20class-local%20polling-6ee7a8)
![license](https://img.shields.io/badge/license-MIT-blue)

## Matériel

L'InspirAIR Top a un **port Modbus RS485 en standard** : le bornier **X3**
(*Connexion Modbus client*) de la carte électronique, sous la goulotte verte du
dessus de l'unité. Il est **distinct de X4**, le port de la télécommande : la
télécommande murale continue de fonctionner, aucun bus n'est partagé.

Home Assistant a besoin d'une **passerelle Modbus RTU ↔ Modbus TCP** entre les
deux — Ethernet, PoE ou WiFi, peu importe la marque, du moment qu'elle fait une
vraie conversion de protocole (*passerelle Modbus*, pas un simple tunnel série).

| Passerelle | → | Aldes X3 |
|---|---|---|
| 485A | → | **A** |
| 485B | → | **B** |
| GND (côté RS485) | → | **⏚** |

Une paire d'un câble réseau est idéale pour A/B (torsadée, ~100 Ω) ; un fil
d'une autre paire pour la masse. Si rien ne répond, inversez A et B — cela ne
peut rien abîmer.

> ⚠️ **Coupez l'alimentation de la VMC avant d'ouvrir la goulotte.** X3 est en
> très basse tension, mais X1, juste à côté, est en **230 V**.

Réglages de la passerelle — imposés par Aldes, ils ne se changent pas côté VMC :

| Réglage | Valeur |
|---|---|
| Série | **9600 bauds, 8 bits de données, sans parité, 1 bit de stop** |
| Mode | passerelle Modbus TCP ↔ RTU |
| Port TCP | 502 |
| Adresse esclave | **2** (valeur d'usine, 1 à 99 avec Aldes Configurator) |

Testé avec une **Waveshare RS485 TO POE ETH (B)** (isolée, alimentée en PoE),
*Protocol* réglé sur **Modbus TCP to RTU**. Sortie d'usine, elle est sur l'IP
fixe `192.168.1.200`, sans mot de passe : donnez un instant à votre ordinateur
une adresse en `192.168.1.x` pour atteindre sa page web et la passer sur votre
réseau.

## Installation

### Prérequis : HACS

HACS (Home Assistant Community Store) est ce qui installe et met à jour les
intégrations non livrées avec Home Assistant. Si vous ne l'avez pas encore :

1. Suivez le guide officiel : **<https://hacs.xyz/docs/use/download/download/>**
   (il détaille le script de téléchargement, puis le redémarrage de Home Assistant)
2. Ajoutez HACS comme intégration :
   *Paramètres → Appareils et services → Ajouter une intégration → HACS*
3. Il demande d'autoriser un compte GitHub — HACS lit les dépôts via l'API GitHub

Une fois HACS présent dans votre barre latérale, revenez ici.

*Vous n'utilisez pas HACS ? Passez à [l'installation manuelle](#manuelle)
ci-dessous, elle ne demande aucun outil supplémentaire.*

### HACS — en un clic

[![Ouvrir votre instance Home Assistant et afficher ce dépôt dans le Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Smeagolworms4&repository=ha-aldes-inspirair-modbus&category=integration)

Le bouton ouvre directement le dépôt dans HACS sur votre instance. Installez
**Aldes InspirAIR Top (Modbus)**, puis redémarrez Home Assistant.

<details>
<summary>Étapes manuelles dans HACS</summary>

1. HACS → Intégrations → menu ⋮ → *Dépôts personnalisés*
2. URL : `https://github.com/Smeagolworms4/ha-aldes-inspirair-modbus`, catégorie *Intégration*
3. Installer **Aldes InspirAIR Top (Modbus)**, puis redémarrer Home Assistant

</details>

### Manuelle

Copier `custom_components/aldes_inspirair` dans le dossier `custom_components`
de votre configuration, puis redémarrer Home Assistant.

### Configuration

[![Ouvrir votre instance Home Assistant et commencer la configuration d'une nouvelle intégration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=aldes_inspirair)

Ou *Paramètres → Appareils et services → Ajouter une intégration → Aldes
InspirAIR Top (Modbus)*. Saisissez l'adresse IP de la passerelle, le port
Modbus TCP (`502`) et l'adresse esclave (`2`). L'intégration interroge la VMC
avant de créer l'entrée : un problème de câblage ou de réglages série se voit
tout de suite.

## Options

*Paramètres → Appareils et services → Aldes InspirAIR Top (Modbus) → Configurer*

| Option | Défaut | Détail |
|---|---|---|
| Intervalle d'interrogation | 15 s | de 5 s à 10 min |

L'adresse de la passerelle peut être changée plus tard avec *Reconfigurer*,
sans perdre les entités ni leur historique.

## Entités

Tout est regroupé sous un seul appareil **VMC Aldes**.

| Entité | Type | Détail |
|---|---|---|
| Ventilation | ventilateur | la VMC elle-même : préréglages Vacances / Quotidien / Pointe cuisine / Boost / **Auto**, ou vitesse en 4 crans. Pas d'*arrêt* — une double flux n'est pas faite pour s'arrêter, *Vacances* est le niveau le plus bas |
| Niveau de ventilation | sélecteur | les mêmes choix, pratique dans les automatisations |
| Niveau en cours | capteur | ce que la VMC applique réellement. En *Auto*, le mode demandé vaut 255 : c'est le seul moyen de connaître le niveau réel |
| Mode bypass | sélecteur | Désactivé / Automatique / Optimisation hiver / Optimisation été / Ouvert forcé |
| Durée de vie des filtres | nombre | de 6 à 12 mois, comme dans le menu de la télécommande |
| Température air neuf / extrait / insufflé / rejeté | capteur | résolution 0,01 °C |
| Débit extraction / insufflation | capteur | débit réel, m³/h |
| Rendement échangeur | capteur | calculé seulement bypass fermé, avec plus de 3 °C d'écart intérieur/extérieur |
| Filtres : usage | capteur | % de la durée de vie consommée |
| Filtres : temps depuis le reset | capteur | heures écoulées depuis la remise à zéro |
| Position du bypass | capteur | fermé, ouvert, en fermeture, en ouverture, ou les défauts de câblage signalés par la VMC |
| Bypass ouvert | capteur binaire | |
| Erreur / Défaut | capteur / capteur binaire | le défaut en clair, d'après la liste de la notice Aldes |
| Horloge de la VMC, dérive de l'horloge | capteur | la date et l'heure internes de la machine, et son écart avec Home Assistant — c'est cette horloge que suit la programmation hebdomadaire |
| Code erreur, équilibrage, commandes et régimes des ventilateurs extraction / insufflation | capteur | diagnostic |
| Consignes de débit par niveau, configuration ventilateurs | capteur | valeurs de mise en service, en lecture seule, désactivées par défaut |

## Protocole

La notice d'installation Aldes donne les réglages série ; la table complète des
registres (document 11029423) n'est plus accessible — son QR code mène
aujourd'hui à la page d'accueil d'Aldes. La table ci-dessous vient de la table
officielle de la même carte (EasyVEC® / InspirAIR® Home) et de mesures sur une
vraie InspirAIR Top, firmware 291.

- Registres de maintien uniquement : **FC03** en lecture, **FC16** en écriture.
  **FC06 est refusé** (fonction illégale) — tout comme une écriture d'un seul
  registre envoyée de la façon « habituelle » par la plupart des outils Modbus.
  Le FC16 sur un seul registre fonctionne.
- Le registre **16** est un *niveau d'utilisateur*, pas un mot de passe : `avilleret/esphome-aldes` en
  recense quatre — 0, 2345, 12054 et **34102**, le plus élevé. La plupart des registres renvoient **`-1`**
  tant que **34102** n'a pas été écrit dans le registre **16** — l'équivalent Modbus du
  mot de passe installateur de la télécommande. L'intégration l'envoie avant
  chaque lecture, faute de savoir combien de temps il reste valable.

| Registre | Contenu | Accès |
|---|---|---|
| 12 | version logicielle | L |
| 257 | mode demandé : 0 vacances, 1 quotidien, 2 pointe cuisine, 3 boost, **255 auto** | L/É |
| 259 | bypass : 0 désactivé, 1 auto, 2 hiver, 3 été, 4 ouvert | L/É |
| 267 | durée de vie des filtres, mois | L/É |
| 278 | équilibrage insufflation/extraction, % | L |
| 320 / 321 | commandes moteurs, mV (0–10 V) | L, verrouillé |
| 346 / 347 | usage des filtres (%) / heures depuis le reset | L |
| 348 | position du bypass | L |
| 350 / 351 | air neuf / air extrait, 0,01 °C | L |
| 352 / 353 | air rejeté / air insufflé, 0,01 °C | L, verrouillé |
| 354 / 355 | régime ventilateur extraction / insufflation, tr/min | L, verrouillé |
| 356 / 357 | débits extraction / insufflation, m³/h | L, verrouillé |
| 384 | code défaut en cours | L |
| 1056 | **niveau appliqué** (0 à 3), y compris en auto | L |
| 1057 | 10 quand l'auto pilote la VMC, 0 sinon | L |
| 1028 | configuration ventilateurs (2 = A, 1 = B) | L |
| 1040-1049 | consignes de débit par niveau, par paires (extraction, insufflation) : vacances, quotidien, pointe cuisine, boost, maxi | L |
| 1304-1310 | horloge : année, mois, jour, jour de semaine (lundi = 0), heure, minute, seconde | L |

Les registres 320/321 et 354/355 sont nommés d'après
[avilleret/esphome-aldes](https://github.com/avilleret/esphome-aldes), qui les rattache aux ventilateurs
d'extraction et d'insufflation. Les registres 346 et 347 viennent de la
[notice Modbus InspirAIR Side](https://assets.aldes.fr/assets/docsFR/modbus-inspirair-side-notice-de-parametrage.pdf)
d'Aldes, la table publiée la plus proche de celle du Top — en notant qu'elle donne pour le registre 257
*2 = boost, 3 = invités*, là où le Top utilise *2 = bouton poussoir, 3 = boost*, vérifié ici. Les registres de
durée qu'elle documente (264-266) sont inertes sur le Top : l'écriture est acceptée puis ignorée, la relecture
reste à `-1`. Les registres 350 et 351 sont nommés dans la table Aldes ; lequel de 352/353 est
l'air rejeté et lequel l'air insufflé a été déduit des mesures. La télécommande
murale affiche les quatre valeurs avec leur nom dans *Installateur (0405) →
Maintenance → Valeurs réelles* — ouvrez un ticket si elles ne concordent pas.

## Icônes et logo

Les icônes des entités sont livrées avec l'intégration (`icons.json`) et ne
demandent rien de plus.

Le **logo** affiché par HACS et la page des intégrations est livré avec
l'intégration lui aussi, dans
[`custom_components/aldes_inspirair/brand/`](custom_components/aldes_inspirair/brand/).
Depuis Home Assistant 2026.3, une intégration tierce sert ses propres visuels
depuis ce dossier, et ils priment sur le CDN `brands`.

<img src="brands/icon.png" alt="Icône Aldes InspirAIR Top (Modbus)" width="96" height="96">

## Tests

```bash
pip install -r requirements-test.txt
pytest
```

43 tests, joués contre une **fausse InspirAIR Top** : un petit serveur Modbus
TCP qui se comporte comme la vraie — registres verrouillés tant que le code
installateur n'est pas envoyé, FC06 refusé, esclave 2, silence sur un mauvais
esclave. Ils couvrent le client Modbus seul, puis l'intégration chargée dans une
vraie instance Home Assistant : configuration, options, reconfiguration, chaque
entité, chaque commande, une écriture refusée, et une VMC qui cesse de répondre.

Le harnais de test demande Python 3.13. Sans lui en local :

```bash
docker run --rm -v "$PWD":/repo -w /repo python:3.13 \
  sh -c "pip install -q -r requirements-test.txt && pytest -p no:cacheprovider"
```

## Licence

MIT
