from pymodaq.plugins.hardware.STEM import orsayscan

class OrsayScanPosition(orsayscan.orsayScan):

    def __init__(self, gene, scandllobject = 0):
        super(OrsayScanPosition,self).__init__(gene,scandllobject)

        self.x=0
        self.y=0

    def OrsayScanSetProbeAt(self,gene,px,py):
        #bool SCAN_EXPORT OrsayScanSetProbeAt(self.orsayscan, int gene, int px, int py);
        self.x=px
        self.y=py
        return orsayscan._OrsayScanSetProbeAt(self.orsayscan,gene,px,py)

