Interlude I: Custom Application
===============================

As an interlude we'll have a look into writing a custom application instead of a custom extension. The principal difference between the corresponding Python classes is that :code:`CustomApp` does not have access to the functionality of the dashboard. Using a custom application makes sense when controlling a dedicated instrument or a fixed arrangement which is used by people not being familiar with the wealth of PyMoDAQ's functionality. It can be seen as kind of a standalone extension.

There is, though, an important drawback for the approach with simulated devices used in this tutorial. Sharing controllers amongst different plugins is managed "out of the box" by the dashboard. Getting that to work in a custom application without a dashboard would ask for quite some cross-thread coding to access the plugins, each living in its proper thread, which is not really subject of this tutorial. Therefore, the custom application takes a little different approach. It is based on a spectro-photometer which can control the shutters itself.

This tweak demonstrates also why custom applications without a dashboard working behind the scene always risk to compromise PyMoDAQ's modular approach: the plugin's interface has to fit to the application's specific needs and calls. With our simulation controller, however, all we need is already there. We just have to access the controller directly over the spectrometer plugin. But this is exactly the point where modularity gets broken,

At the time of this writing, the version 5.2 of PyMoDAQ is out and some mechanisms for the interaction with plugins apparently have changed. The custom application to be built here was working in version 5.1 but ceased to work with version 5.2. For the time being and until the new API has settled (or the use of CustomApp is abandoned for non-internal coding), this chapter will not be continued.
