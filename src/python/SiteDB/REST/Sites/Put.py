'''
Created on 5 Jan 2010

@author: metson
'''

from WMCore.WebTools.RESTModel import RESTModel
from SiteDB.REST import Validate

class Put(RESTModel):
    '''
    Put: Put data related to the sites known to SiteDB
     
    '''

    def __init__(self, config):
        '''
        Initialise the RESTModel and add some methods to it.
        '''
        RESTModel.__init__(self, config)
        
        del self.methods['POST']
        del self.methods['GET']
        
        self.methods['PUT'] = {'list': {'args':['cms_name', 'site_name', 
                                                'country', 'usage', 'url', 
                                                'logourl'],
                                        'call': self.add_site,
                                        'version': 1},
                              'links': {'args':['name', 'url'],
                                        'call': self.add_link,
                                        'version': 1}}

    def add_link(self, *args, **kwargs):
        """
        Add a link to the site
        Args: name, url
        """
        input = self.sanitise_input(args, kwargs, 'add_link')
        try:
            sql = """insert into sitelinks (SITEID, URL) values (
                (select id from siteinfo where cms_name = :name), :url) 
            """
            binds = {'name': input['name'], 'url': input['url']}
            self.dbi.processData(sql, binds)
            return True
        except:
            self.exception("Could not add link for input:" % input)
            data = {"exception": e, 
                    "message": "Could not add link",
                    "execeptiontype": str(type(e)).split("'")[1],
                    'binds': binds}
            return data
    
    def add_site(self, *args, **kwargs):
        """
        Add a link to the site
        Args: name, url
        """
        input = self.sanitise_input(args, kwargs, 'add_site')
        try:
            sql = """insert into siteinfo
            (CMS_NAME, SITE_NAME, COUNTRY, USAGE, URL, LOGOURL) values (
                :cms_name, :site_name, :country, :usage, :url, :logourl) 
            """
            binds = {'cms_name': input['cms_name'],
                     'site_name': input['site_name'], 
                     'url': input['url'],
                     'country': input['country'], 
                     'usage': input['usage'], 
                     'url': input['url'], 
                     'logoirl': input['logourl']}
            self.dbi.processData(sql, binds)
            binds = {'cms_name': input['cms_name']}
            result = self.dbi.processData('''select * from siteinfo 
                                        where cms_name = :cms_name''', binds)
            return self.formatDict(result)
        except:
            self.exception("Could not add link for input:" % input)
            data = {"exception": e, 
                    "message": "Could not add link",
                    "execeptiontype": str(type(e)).split("'")[1],
                    'binds': binds}
            return data