'''
Created on 5 Jan 2010

@author: metson
'''

from WMCore.WebTools.RESTModel import RESTModel
from SiteDB.REST import Validate

class Post(RESTModel):
    '''
    Post: Post data related to the sites known to SiteDB
     
    '''

    def __init__(self, config):
        '''
        Initialise the RESTModel and add some methods to it.
        '''
        RESTModel.__init__(self, config)
        validator = Validator({'dbi':self.dbi})
        
        self.methods['POST'] = {'software':{'args': ['ce', 'release', 'arch'],
                                            'call': self.software,
                                            'version': 2,
                                            'validation': [validator.validate_release,
                                                           validate_architecture,
                                                           validate_is_ce]}
        }
        del self.methods['GET']
        
    def pin_software(self, *args, **kwargs):
        """
        Mark a release/arch pair as pinned.
        
        Input: {'ce': a FQDN, 
                'release': the CMSSW release, 
                'arch': the architecture}
        """
        sql = """insert into pinned_releases (CE_ID, RELEASE, ARCH) 
        values ((select id from resource_element where fqdn=:ce), 
                :release, 
                :arch)"""
        