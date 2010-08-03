'''
Created on 5 Jan 2010

@author: metson
'''
from WMCore.WebTools.NestedModel import NestedModel
from SiteDB.REST.People.Get import Get

class Base(NestedModel):
    '''
    Pull in all the methods for the various verbs.    
    '''

    def __init__(self, config):
        '''
        Initialise the RESTModel and add some methods to it.
        '''
        NestedModel.__init__(self, config)
        # Import the GET methods
        get = Get(config)
        self.methods['GET'] = get.methods['GET']
        