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
import inspect
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

    # A real Qt slot may declare fewer parameters than the signal it's connected
    # to provides (e.g. a plain `def _grab(self):` connected to a checkable
    # QAction's `triggered(bool)`) -- Qt introspects the slot and only passes as
    # many arguments as it declares. That introspection needs a concrete
    # parameter list; it can't be done for `wrapper`'s own generic `*call_args`,
    # so Qt falls back to passing everything the signal provides, regardless of
    # what `unbound_func` actually accepts. Work out the true accepted arity
    # from `callback` itself (a bound method or `functools.partial` already
    # correctly excludes `self`/pre-bound args from its own signature) and
    # truncate `call_args` to match, replicating Qt's own truncation.
    max_extra_args = None  # None == unlimited (unknown, or callback itself takes *args)
    try:
        sig = inspect.signature(callback)
        if not any(p.kind is inspect.Parameter.VAR_POSITIONAL for p in sig.parameters.values()):
            max_extra_args = sum(
                1 for p in sig.parameters.values()
                if p.kind in (inspect.Parameter.POSITIONAL_ONLY,
                              inspect.Parameter.POSITIONAL_OR_KEYWORD))
    except (TypeError, ValueError):
        pass

    if max_extra_args is None:
        # Unknown/unbounded arity (the target itself declares *args) -- nothing
        # to pin down, fall back to forwarding everything.
        def wrapper(*call_args, **call_kwargs):
            obj = receiver_ref()
            if obj is None:
                return None
            return unbound_func(obj, *bound_args, *call_args, **bound_kwargs, **call_kwargs)
    else:
        # Qt determines how many signal arguments to deliver to a connected
        # Python callable by introspecting it -- and does so *reliably* only
        # for a callable with a concrete, fixed parameter list. A generic
        # `def wrapper(*call_args)` has no such list: its true arity is
        # ambiguous to that introspection, and in practice different Qt/
        # pytest-qt code paths resolve that ambiguity inconsistently (observed
        # directly: identical connections deliver the full signal argument in
        # one case and none of it in another, depending only on whether a
        # pytest-qt `qtbot` fixture is active in the process -- not on
        # anything specific to the target method). Rather than depend on
        # guessing that resolution, generate a wrapper with exactly
        # `max_extra_args` named positional parameters, so its arity is
        # concrete and unambiguous to any introspector.
        param_names = [f'_a{i}' for i in range(max_extra_args)]
        extra_call_args = ''.join(f', {name}' for name in param_names)
        source = (
            f"def wrapper({', '.join(param_names)}):\n"
            f"    obj = receiver_ref()\n"
            f"    if obj is None:\n"
            f"        return None\n"
            f"    return unbound_func(obj, *bound_args{extra_call_args}, **bound_kwargs)\n"
        )
        namespace: dict = {}
        exec(source, {
            'receiver_ref': receiver_ref,
            'unbound_func': unbound_func,
            'bound_args': bound_args,
            'bound_kwargs': bound_kwargs,
        }, namespace)
        wrapper = namespace['wrapper']

    # Copy __name__/__doc__ for readability (tracebacks, repr) without using
    # functools.wraps(unbound_func): that would set __wrapped__ to the
    # *unbound* function, which some introspection consumers resolve back to
    # (a signature still including `self`) instead of `wrapper`'s own.
    wrapper.__name__ = getattr(unbound_func, '__name__', wrapper.__name__)
    wrapper.__doc__ = unbound_func.__doc__

    return wrapper
