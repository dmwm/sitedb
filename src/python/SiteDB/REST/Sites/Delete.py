'''
Created on 5 Jan 2010

@author: metson
'''

from WMCore.WebTools.RESTModel import RESTModel
from SiteDB.REST import Validate

class Delete(RESTModel):
    '''
    Delete: Delete data related to the sites known to SiteDB
     
    '''

    def __init__(self, config):
        '''
        Initialise the RESTModel and add some methods to it.
        '''
        RESTModel.__init__(self, config)
        
        del self.methods['POST']
        del self.methods['GET']