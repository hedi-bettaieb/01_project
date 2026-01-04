import logging
# program/subtitle/internet_monitor.py
import time
import requests


class InternetMonitor:
    """Fournit des méthodes pour vérifier et surveiller l'état de la connexion Internet."""

    def __init__(self, check_url="https://www.google.com"):
        """
        Initialise le moniteur de connexion.
        
        Args:
            check_url (str): URL à interroger pour vérifier la connexion.
        """
        self.check_url = check_url

    def check_internet_connection(self, timeout=3):
        """
        Vérifie la connexion Internet en effectuant une requête HTTP.
        
        Args:
            timeout (int): Temps d'attente maximal pour la requête (secondes).
            
        Returns:
            bool: True si la connexion est disponible (statut 200), False sinon.
        """
        try:
            # Effectue une requête HEAD pour économiser de la bande passante, 
            # et vérifie que le statut est 200 (OK)
            response = requests.head(self.check_url, timeout=timeout)
            return response.status_code == 200
        except requests.RequestException:
            # requests.exceptions.ConnectionError, Timeout, TooManyRedirects, etc.
            return False

    def monitor_internet_connection(self, stop_event, check_interval=3, max_failures=3):
        """
        Surveille la connexion Internet en continu avec tolérance aux coupures temporaires.
        
        Note: Cette méthode est bloquante et est destinée à être exécutée dans un thread
        séparé, s'arrêtant lorsque stop_event est déclenché ou qu'une panne durable est détectée.
        
        Args:
            stop_event (threading.Event): Événement utilisé pour arrêter le monitoring.
            check_interval (int): Délai entre les vérifications (secondes).
            max_failures (int): Nombre d'échecs consécutifs avant de considérer la perte comme durable.
            
        Returns:
            bool: True si le monitoring s'est arrêté par stop_event, False si la connexion 
                  a été perdue durablement.
        """
        failures = 0
        while not stop_event.is_set():
            if self.check_internet_connection(timeout=2):
                failures = 0  # Reset si connexion rétablie
            else:
                failures += 1
                # Laissez l'affichage de l'erreur au code appelant si nécessaire
                if failures >= max_failures:
                    return False  # Perte durable détectée
            
            # Attend l'intervalle de vérification ou jusqu'à ce que stop_event soit déclenché
            if stop_event.wait(check_interval):
                break # Arrêt demandé

        return True # Arrêt normal par stop_event
