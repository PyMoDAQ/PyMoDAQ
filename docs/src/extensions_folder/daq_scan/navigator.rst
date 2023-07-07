

.. _navigator_paragrah:

Navigator
---------

From version 1.4.0, a new module has been added: the Navigator (daq_utils.plotting.navigator). It is most useful when
dealing with 2D scans such as XY
cartography. As such, it is not displayed by default. It consists of a tree like structure displaying all
currently saved 2D scans (in the current dataset) and a viewer where selected scans can be displayed at their respective
locations. It can be displayed using the *Settings* menu, *Show Navigator* option. :numref:`navigator` shows the DAQ_scan extension
with activated Navigator and a few scans. This navigator can also be used as a :ref:`scan_selector_paragraph` viewer to
quickly explore and select areas to scan on a 2D phase space.

   .. _navigator:

.. figure:: /image/DAQ_Scan/navigator.PNG
   :alt: navigator

   An example of dataset displaying several 2D scans at their respective locations (up and right axis)

