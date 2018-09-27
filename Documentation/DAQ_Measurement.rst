DAQ_Measurement
===============

Introduction
------------

| **The DAQ_Measurement module is a mathematic tool to treate Regions Of Interest (see viewer).**
| 

From a given x/y curve we have six main tools :

	* **Integrator** : Integrator with three profile:

		* *sum*  : a sum integration from the cursor
		* *mean* : a mean integration from the cursor
		* *std*  :

	* **Maximum** : Get the maximum value in axis

	* **Minimum** : Get the minimum value in axis
	
	* **Gaussian Fit** : The Gaussian function given by : 

.. amp*\frac{\exp{(-2*\ln{(2)}*(x-x0)^2)}}{(\mathrm{d}x^2)+offset}
.. \end
		with the possibility to define the parameter of the function between the curve values:
			* *amp*    : the amplitude
			* *dx*     : x derivative
			* *xo*     : first x point
			* *offset* :

	* **Lorentzian Fit** : The Lorentzian function given by : 
		.. math:: alpha/pi*gamma/2/((x-x0)^2+(gamma/2)^2)+offset with the possibility to define the parameter of the function between :

			* *alpha*
			* *gamma*
			* *x0*
			* *offset*
			* *amplitude*

	* **Exponential Decay Fit** : The exponential function given by : .. math:: N0*exp(-gamma*x)+offset with the possibility to define the parameter of the function between :

		* *NO*
		* *gamma*
		* *offset*

| 


A paragraph
-----------


Another paragraph
-----------------