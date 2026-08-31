import pytest
import gc
import sys

def pytest_unconfigure(config):
    """
    S'exécute juste après l'affichage du rapport de couverture,
    exactement au moment où le crash se produit.
    """
    # 1. Nettoyer agressivement le registre de pyqtgraph pour briser les références
    try:
        from pyqtgraph.parametertree import Parameter
        # On vide le dictionnaire global qui retient vos paramètres personnalisés
        Parameter.PARAM_TYPES = {}
    except (ImportError, AttributeError):
        pass

    # 2. Forcer la collecte des objets cycliques liés à vos types personnalisés
    gc.collect()

    # 3. Détruire proprement la QApplication avant la fermeture de Python
    try:
        from qtpy.QtCore import QCoreApplication
        app = QCoreApplication.instance()
        if app is not None:
            app.processEvents()
            # Supprime la référence globale C++ pour forcer un teardown propre
            app.quit()
            del app
    except ImportError:
        pass

    # 4. Forcer un cycle final de garbage collection
    gc.collect()