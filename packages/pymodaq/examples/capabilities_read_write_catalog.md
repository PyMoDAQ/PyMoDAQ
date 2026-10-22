# Reading and writing a quantity: every way, side by side

`capabilities.py`'s docstrings explain each knob where it's declared; this is the other direction -
one page answering "I have a plugin method/attribute/setting, which keyword gets me there," with
every option next to the others instead of scattered across `measurement()`'s and `control()`'s own
docstrings. Nothing here is new behavior; it's the existing mechanism, collected. Four example files
demonstrate all of it through a running GUI: `hardware_module_minimal_example.py`,
`hardware_module_example.py` (the spectrometer) and `hardware_module_stage_example.py` tell a
story, each adding a few rows at a time by design; `hardware_module_catalog_example.py` has no
story - every row in it is isolated on purpose, to show exactly one combination the other three
don't use anywhere. This doc is the index into which row, in which file, shows which keyword
(including `shape=`'s role in picking a plotting widget, and `get=`/`read()`'s own return value's
role in how several channels can end up on one plot, both at the bottom).

## Reading: `get=` (on both `measurement()` and `control()`)

| Form | Resolves to | What the plugin needs | Shown in |
|---|---|---|---|
| nothing (default) | `read(names, fresh)` | one shared `read()` handling every name it's given | `temperature` (minimal), `spectrum`/`motion` (stage) |
| `get=True` | `lambda plugin: plugin.<name>` | **control**: nothing extra - storage is automatic (see below). **measurement**: the plugin must assign `self.<name>` itself somewhere, nothing does it for you | `exposure`, `trigger` (spectrometer, control); `uptime` (catalog, measurement - `_advance()` assigns it itself) |
| `get='_method_name'` | `lambda plugin: plugin._method_name()` | that no-arg method | `temperature`, `status` (spectrometer): `_read_temperature`, `_read_status` |
| `get=callable` | used as-is | whatever the callable needs | `gain` (catalog) - a real lambda, for exactly the case one no-arg method call can't express: a calculation combined with the method call, inline |

A channel with *any* non-default `get` is read individually, not batched: periodic batching
(one `read(names=[...])` call per shared poll period) only ever groups channels with no `get` of
their own. Declaring `get=` is therefore also "opt this channel out of the plugin's batching," not
only a question of where the value comes from - relevant once a device has several channels that
*do* share one real batched read (like `spectrum` would, on real hardware, with other detector
channels), since giving one of them a `get` splits it out of that shared call.

## Writing: two mutually-exclusive dispatches, plus two hooks (`control()` only)

A write to a control is never *only* "however the value reaches the device" - that part picks
**one** of these:

| Dispatch | What happens | Plugin needs | Shown in |
|---|---|---|---|
| nothing, plugin defines no `write()` | nothing - the value is just stored (see below) | nothing: the "just an attribute" case | `trigger` (spectrometer) |
| nothing, plugin defines `write(name, value)` | `plugin.write(channel, value)` is called | one `write()` handling every control name it's given | `target` (minimal) |
| `set=callable` | `set(plugin, value)` instead of `write()` | the callable | `_axis_controls`'s `set_target`/`set_enabled` (stage) |
| `set='_method_name'` | sugar for `lambda plugin, value: plugin._method_name(value)` | that one-arg method | `calibration_offset` (catalog) |

Whichever applies (or none), storage is unconditional: after a successful write, the device thread
always does `plugin.<name> = value` too - this is what makes `get=True` safe to read back from, and
what makes a control with no dispatch at all still useful ("just an attribute"). `pre_set=`/
`post_set=` hook into *that* storage step, for the control that needs a little more than plain
storage but not a whole `set=` of its own - mutually exclusive with `set=`, not stackable with it:

| Hook | Runs | Can do | Shown in |
|---|---|---|---|
| `pre_set=callable`/string | before storage | reject the write (raise → `write_failed`, same as `set()`/`write()` raising; storage is skipped) | `safety_limit` (catalog) - `pre_set` with no matching `post_set` |
| `post_set=callable`/string | after storage | a side effect that can read `plugin.<name>` already holding the new value | `exposure`'s `post_set='_clamp_averaging'` (spectrometer); `heater_power` (catalog) - `pre_set` and `post_set` together |

## `readback=`: the measurement that answers "what is it actually doing"

| Form | Names it | If a measurement of that name already exists |
|---|---|---|
| `readback=True` | `<name>_readback` | that one is used untouched - nothing auto-created |
| `readback='custom_name'` | that name | same |

The auto-created one defaults its own `get` to the control's `get`, if the control has one: right
when the control has no real settling lag, so its own answer already *is* the readback's answer
(`exposure` in the spectrometer example - `get=True` on both ends up reading the same attribute
twice, for free). A control with no `get` - the laggy case, e.g. a target vs. the axis's actual
position - gets an empty auto-created readback instead, answered through the plugin's own `read()`,
exactly like the stage example's `x`/`y`/`z` and their positions.

## Wrapping an existing instrument object: inherit or compose

Neither `get=` nor `set=` has to be a plugin method at all - either accepts any
`Callable[[Any], Any]`/`Callable[[Any, Any], None]`, called as `getter(plugin)`/
`setter(plugin, value)`. That is what makes reusing a separately-written driver class (pymeasure or
otherwise) possible, in one of two shapes, picked by whether the driver's own API already uses
distinctly-named methods or reuses the quantity's own name:

| Driver's own API | Approach | How | Shown in |
|---|---|---|---|
| Distinctly-named methods (`get_x()`/`set_x()`) | **Inherit** the driver; reference its methods directly - no wrapper at all | `get=MyDriver.get_x, set=MyDriver.set_x` | `aux_relay` (catalog) - `_RelayDriver.get_relay`/`.set_relay` |
| Same-named property (pymeasure's own `control()`/`measurement()`) | Inherit; reach into the property's `fget`/`fset`, declared under a *different* PyMoDAQ-facing name | `get=MyDriver.x.fget, set=MyDriver.x.fset` | not in any example yet - worked through in `hardware/README.md` |
| Any API, held as `self.controller` instead of inherited (several composed instruments, or not tying the plugin's own lifecycle to the driver's) | **Compose**; redirect with `instr_get`/`instr_set` (`capabilities.py`) | `get=instr_get(MyDriver.get_x), set=instr_set(MyDriver.set_x)` | `beam_shutter` (catalog) - `_ShutterDriver.get_shutter`/`.set_shutter` |

The same-name case can only ever be inherited, never redeclared under the identical name:
`control()`/`measurement()` return a data descriptor (`Quantity.__get__`/`__set__`), so declaring
that name again on the subclass *replaces* whatever it meant on the driver, rather than layering
PyMoDAQ's metadata on top of it. Picking a different PyMoDAQ-facing name (`trigger_source`, not
pymeasure's own `trigger`) is what avoids the collision, not a different mechanism. Full reasoning
and worked examples: `hardware/README.md`, "Wrapping an existing instrument object."

`instr_get(method, attr='controller')`/`instr_set(method, attr='controller')` default `attr` to
`'controller'` - the same attribute name the old-style `ini_stage`/`ini_detector` already use, so a
bare `controller: MyDriver` class-level annotation still gives IDE autocompletion on
`self.controller.<method>`, with no runtime effect of its own. *attr* is only resolved against the
real instance when the hardware thread actually calls the callable `instr_get`/`instr_set` return -
always after `open()` has already run - so `self.controller = MyDriver(...)` belongs in `open()`,
not `__init__`, the same timing the old style already uses.

## `shape=`: which plotting widget

| Shape | Widget | Shown in |
|---|---|---|
| `(1,)` (the default) | `Viewer0D` - a scrolling scalar trace | `temperature` (minimal), every scalar measurement |
| `(N,)`, N > 1 | `Viewer1D` - a curve | `spectrum` (spectrometer) |
| `(H, W)` | `Viewer2D` - an image | `frame` (catalog) |
| anything with more than 2 dimensions | rejected at declaration time (`ValueError`), not at display time | - |

Nothing extra to declare for a camera-style 2D reading: `shape=(H, W)` alone is what picks
`Viewer2D`, the same single rule (`_viewer_type`, by `len(shape)`) that already picks
`Viewer0D`/`Viewer1D` for the others - `get=`/`set=`/`readback=`/etc. all work on a 2D measurement
exactly as they do on any other. The more-than-2-dimensions case isn't a silent gap: nothing past
`Viewer2D` is wired up in `HardwareModule` yet (no `ViewerND`), so `Quantity` rejects it outright,
with a message pointing at exactly that, rather than letting it fail later with a confusing
`ViewerError` deep inside a paint call. `shape=` only ever matters for *this* - picking the dock
before the first reading has arrived; what that reading actually plots is the next section.

## Several channels, one plot: let `get=`/`read()` answer with a real `DataWithAxes`

`get`/`read` normally answer with a plain array or scalar, and `HardwareModule` wraps that into a
single-array, single-label `DataWithAxes` on the way to the viewer - everything above this point
assumes that. Either may instead return an **already-built** `DataWithAxes`/`DataRaw` directly -
e.g. two channels a spectrometer reports together in one reading:

```python
def _read_channels(self):
    return DataRaw('channels', data=[self._ch_a, self._ch_b], labels=['ch_a', 'ch_b'],
                   axes=[Axis('wavelength', units='nm', data=self._wavelength, index=0)])
```

`HardwareModule` passes it straight through, unexamined, to the viewer (`channels` in the catalog
example) - curves, labels, *and* the real wavelength axis instead of a bare point index, none of it
possible from a plain `get=` value at all. There is **no separate keyword for this** - an earlier
version of this had one (`curves=`, naming the labels up front on the declaration); it was removed
because it was purely redundant with what the return value already says, the same way `read()`'s
own `DataToExport` has always let a plugin build and return whatever `DataWithAxes` it wants, with
nothing declared on the `Quantity` about it at all. The plotted shape - how many arrays, their
labels, real axes if any - is exactly whatever the plugin's own return value carries, not a separate
piece of declaration-time metadata that would just have to be kept in sync with it. This is for
channels that are genuinely read together and belong on the same axes - not a way to combine two
otherwise-unrelated, separately declared quantities into one view after the fact; that would need
reconciling readings that arrive at different times, which returning one `DataWithAxes` from one
`get=`/`read()` call sidesteps entirely, since the channels inside it are always read (and so always
redrawn) together.

## Picking one

| On write | On read | Use |
|---|---|---|
| nothing to do | nothing computed | declare it and stop (`trigger`-style) - storage alone answers both |
| something to do, no more than a hook needs | nothing computed | `pre_set=`/`post_set=` only |
| nothing to do | a value computed fresh each read | `get=` only (callable or string) |
| something to do, no more than a hook needs | a value computed fresh each read | both, independently - `get=`/`set=` don't interact with each other |
| a whole-row replacement (shares one hardware transaction with other channels, writes under a different name, skips storage altogether) | - | `set=` instead of the hooks |

The real hardware access living on a *separate* object instead of the plugin itself - inherited or
composed - is an orthogonal choice on top of any row above: it only changes what `get=`/`set=`
point at, never which row applies.

See `control_modules/HARDWARE_MODULE.md` ("Writing a value, and settling") for where this sits
inside the full request_write → store → settle sequence, and `hardware/README.md` ("Wrapping an
existing instrument object") for the inherit-vs-compose reasoning in full.
