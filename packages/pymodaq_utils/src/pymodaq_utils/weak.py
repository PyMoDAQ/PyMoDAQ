"""
Helper for connecting Qt (or any) signals without leaking the receiver.

PySide/PyQt keep an internal reference to a connected Python callable that
outlives ``disconnect()`` (and can survive even destroying the underlying
QObject it was connected to). A slot that closes over ``self`` — a bound
method, or a lambda capturing ``self`` — therefore keeps the receiving
object alive for as long as the connection exists, regardless of any
teardown code, unless that connection is force-broken.

``weak_slot()`` sidesteps the problem at the source: it wraps a bound
method (or a :func:`functools.partial` of one) so the connection only ever
holds a :class:`weakref.ref` to the receiver. Even if the underlying Qt
binding never releases the wrapper closure, the closure itself cannot keep
the receiver reachable.
"""
import functools
import weakref
from typing import Callable


def weak_slot(callback: Callable) -> Callable:
    """Wrap a bound method (or a ``functools.partial`` of one) to hold a weakref.

    Parameters
    ----------
    callback : Callable
        A bound method (``obj.method``), or ``functools.partial(obj.method, *args)``.

    Returns
    -------
    Callable
        A plain function that looks up the receiver via a weakref on each call
        and is a no-op once the receiver has been garbage collected. If
        `callback` is not a bound method (or partial of one) — e.g. it is a
        plain function, an already-bound `staticmethod`, or a lambda — it
        cannot be safely rewritten this way and is returned unchanged.

    Examples
    --------
    >>> action.triggered.connect(weak_slot(self.on_triggered))
    >>> action.triggered.connect(weak_slot(functools.partial(self.load_extension, name)))
    """
    func = callback
    bound_args: tuple = ()
    bound_kwargs: dict = {}
    if isinstance(callback, functools.partial):
        func = callback.func
        bound_args = callback.args
        bound_kwargs = callback.keywords or {}

    receiver = getattr(func, '__self__', None)
    unbound_func = getattr(func, '__func__', None)
    if receiver is None or unbound_func is None:
        return callback  # not a bound method we can safely rewrite

    receiver_ref = weakref.ref(receiver)

    @functools.wraps(unbound_func)
    def wrapper(*call_args, **call_kwargs):
        obj = receiver_ref()
        if obj is None:
            return None
        return unbound_func(obj, *bound_args, *call_args, **bound_kwargs, **call_kwargs)

    return wrapper
