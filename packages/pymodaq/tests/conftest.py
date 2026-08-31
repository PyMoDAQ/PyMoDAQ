import pytest
import gc


def pytest_sessionfinish(session, exitstatus):
    """
    ÉTAPPE 1 : Appelé AVANT le rapport de couverture.
    On dissout les objets de données et les widgets pour que le tracker
    de couverture ne les fige pas en mémoire.
    """
    # 1. Vider le registre pyqtgraph des paramètres personnalisés
    try:
        from pyqtgraph.parametertree import Parameter
        Parameter.PARAM_TYPES = {}
    except (ImportError, AttributeError):
        pass

    # 2. Fermer et planifier la destruction C++ de tous les widgets restants
    try:
        from qtpy.QtWidgets import QApplication
        app = QApplication.instance()
        if app is not None:
            for widget in app.topLevelWidgets():
                if widget.isVisible():
                    widget.close()
                widget.deleteLater()
            app.processEvents()
    except ImportError:
        pass

    # 3. Forcer le Garbage Collector à nettoyer les références
    gc.collect()


def pytest_unconfigure(config):
    """
    ÉTAPE 2 : Appelé APRÈS le rapport de couverture, juste avant de quitter.
    Dernier filet de sécurité pour tuer proprement la QApplication.
    """
    try:
        from qtpy.QtCore import QCoreApplication
        app = QCoreApplication.instance()
        if app is not None:
            app.processEvents()
            # On quitte l'application et on supprime la référence globale
            app.quit()
            del app
    except ImportError:
        pass

    # Nettoyage final de la mémoire Python
    gc.collect()
