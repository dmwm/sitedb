
from WMCore.WebTools.RESTModel import RESTModel

class Search(RESTModel):
    """
    Read only interface to SiteDB
    """
    def __init__(self, config):
        RESTModel.__init__(self, config)
        self.methods.update({'sitelist':{'args':['name', 'type'],
                                         'call': self.sitelist,
                                         'version':2}})
    
    def handle_get(self, args, kwargs):
        """
        Standard get verb method. Path arguments determine the API call to make,
        multiple calls (like rest/api1/ap2) will be eventually supported, and 
        key word arguments are passed as the arguments to a given API
        """
        data = self.methods[args[0]]['call'](**kwargs)
        self.debug(str(data))
        return data
    
    def sitelist(self, name='T%', type='cmsname'):
        binds = []
        for n in self.makelist(name):
            binds.append({'name':n})
        sql = "select cms_name from t_site where cms_name like :name"
        return {'sitelist':self.execute(sql, binds)} 
    
    def sitestatus(self, name):
        return {}
    
    def execute(self, sql = "", binds = {}, conn = None, transaction = False):
        """
        A simple select with no binds/arguments is the default
        """
        result = self.dbi.processData(sql, binds, 
                         conn = conn, transaction = transaction)
        
        return self.format(result)[0]