
# Notes about PyMoDAQ

## Structure of the Different Parts of a Move Module

```python
class DAQ_Move:
    def init_hardware(self...):
        hardware: DAQ_Move_Hardware
        hardware.moveToThread()

class DAQ_Move_Hardware:
    hardware: DAQ_Move_Base

class DAQ_Move_LECODirector(DAQ_Move_Base):
    """Plugin class."""
```

