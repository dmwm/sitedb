'''
Created on 16 Aug 2009

@author: metson
'''
from WMCore.WebTools.NestedModel import NestedModel
from SiteDB.REST.Validate import Validator

class Get(NestedModel):
    '''
    People: Data related to the people known to SiteDB 
    '''
    def __init__(self, config):
        '''
        Initialise the RESTModel and add some methods to it.
        '''
        NestedModel.__init__(self, config)
        
        validator = Validator({'dbi':self.dbi})
        
        self.methods = {'GET':{
                               'list': {
                                        'default':{'default_data':1234, 
                                                   'call':self.info,
                                                   'version': 1,
                                                   'args': ['username'],
                                                   'expires': 3600,
                                                   'validation': []},
                                        'dn':{'default_data':1234, 
                                               'call':self.dnUserName,
                                               'version': 1,
                                               'args': ['dn'],
                                               'expires': 3600,
                                               'validation': []},
                                        'roles':{'default_data':1234, 
                                               'call':self.roles,
                                               'version': 1,
                                               'args': ['username'],
                                               'expires': 3600,
                                               'validation': []},
                                        'groups':{'default_data':1234, 
                                               'call':self.groups,
                                               'version': 1,
                                               'args': ['username'],
                                               'expires': 3600,
                                               'validation': []}}
                               }
        }
    
    def dnUserName(self, dn):
        """
        Return the username associated to the dn
        """
        sql = 'select username from contact where dn = :dn'
        binds = {'dn': dn}
        result = self.dbi.processData(sql, binds)
        data = self.formatOneDict(result)
        return {'username':data['username'], 'dn': dn}
    
    def info(self, username=None):
        """
        Return information for a given username, to include:
            site:roles
            group:roles
            dn
            email
        Can be shortened by kwarg, e.g. ?dn will only return the DN for username
        """
        return {'info': {'username':username}}
    
    def roles(self, username=None):
        """
        Return the roles username has
        """
        return {'roles': {'username':username}}
    
    def groups(self, username=None):
        """
        Return the groups username is in
        """
        return {'groups': {'username':username}}
     