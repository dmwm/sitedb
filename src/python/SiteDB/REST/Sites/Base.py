'''
Created on 5 Jan 2010

@author: metson
'''
from WMCore.WebTools.RESTModel import RESTModel
from SiteDB.REST.Sites.Get import Get

class Base(RESTModel):
    '''
    Pull in all the methods for the various verbs.    
    '''

    def __init__(self, config):
        '''
        Initialise the RESTModel and add some methods to it.
        '''
        RESTModel.__init__(self, config)
        # Import the GET methods
        get = Get(config)
        self.methods['GET'] = get.methods['GET']
        