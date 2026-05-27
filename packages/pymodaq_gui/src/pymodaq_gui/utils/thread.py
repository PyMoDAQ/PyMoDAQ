from qtpy.QtCore import  QThread


class QStopThread(QThread):
    '''
    A QThread but with a `stop` method.
    '''
    def stop(self, timeout:float=5.):
        '''
        A method to always quit a QThread. It firsts try a clean
        termination using quit for `timeout` seconds. If not
        successful, it results using terminate to force QThread
        to quit.

        Parameters
        ----------
        timeout: the timeout to wait for proper termination (in s)

        '''
        self.quit()
        terminated = self.wait(int(timeout*1000))
        if not terminated:
            self.terminate()
            self.wait()