"""
errors.py

Errores de dominio del grafo de la agencia (REQ-PTT-03 / design D-D).

`NoCandidatesError` lleva un `.code` estable ("no_candidates") que el router de
ejecución propaga como campo ADITIVO del evento SSE ``graph_error`` — el
frontend puede distinguir la causa sin depender del texto del mensaje.
"""


class NoCandidatesError(Exception):
    """Cero ideas candidatas superaron el filtro 5/50 (PTT-03-1).

    Se lanza en `node_ideation` ANTES de cualquier write: nunca un
    IntegrityError por una fila inválida, nunca un éxito silencioso con cero
    filas y nunca una pausa humana por algo que no es una decisión humana.
    """

    code = "no_candidates"

    def __init__(self, message="No hay ideas candidatas que superen el filtro 5/50."):
        super().__init__(message)