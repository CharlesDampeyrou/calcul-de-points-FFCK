# -*- coding: utf-8 -*-
"""Appels HTTP à l'API JSON du site https://slalom.ffck.org (application Vue.js)."""

import json
import sys
import time
import urllib.error
import urllib.request


def get_json(url, essais=3):
    for i in range(essais):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "collecte-slalom/2.0",
                },
            )
            with urllib.request.urlopen(req, timeout=60) as rep:
                return json.loads(rep.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            # HTTPError est un cas particulier : 404 -> abandon immédiat,
            # autre code HTTP -> on réessaie, puis on abandonne l'URL.
            # (placé AVANT le except Exception car HTTPError en est une sous-classe)
            if e.code == 404:  # contenu inexistant : inutile de réessayer
                return None
            if i == essais - 1:
                print(f"  ERREUR, abandon de {url} : {e}", file=sys.stderr)
                return None
        except Exception as e:
            # toute erreur réseau transitoire (URLError, TimeoutError, JSONDecodeError,
            # mais aussi http.client.IncompleteRead / RemoteDisconnected, ssl.SSLError,
            # ConnectionResetError...) : on réessaie puis on abandonne l'URL sans
            # tuer la collecte entière.
            if i == essais - 1:
                print(
                    f"  ERREUR, abandon de {url} : {type(e).__name__}: {e}",
                    file=sys.stderr,
                )
                return None
        attente = 5 * (i + 1)
        print(f"  Échec, nouvelle tentative dans {attente}s...", file=sys.stderr)
        time.sleep(attente)
    return None
