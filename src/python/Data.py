from SiteDB.RESTServer import DatabaseRESTApi
from SiteDB.DataWhoAmI import *
from SiteDB.DataRoles import *
from SiteDB.DataGroups import *
from SiteDB.DataPeople import *
from SiteDB.DataSites import *
from SiteDB.DataPledges import *
from SiteDB.DataSoftware import *
from SiteDB.DataUserGroups import *
from SiteDB.DataUserSites import *

class Data(DatabaseRESTApi):
  """Server object for REST data access API."""
  def __init__(self, app, config):
    """
    :arg app: reference to application object; passed to all entities.
    :arg config: reference to configuration; passed to all entities."""
    DatabaseRESTApi.__init__(self, app, config)
    self._add({ "whoami":                 WhoAmI(app, self, config),
                "roles":                  Roles(app, self, config),
                "groups":                 Groups(app, self, config),
                "people":                 People(app, self, config),
                "sites":                  Sites(app, self, config),
                "site-names":             SiteNames(app, self, config),
                "site-resources":         SiteResources(app, self, config),
                "site-associations":      SiteAssociations(app, self, config),
                "resource-pledges":       Pledges(app, self, config),
                "pinned-software":        Software(app, self, config),
                "site-responsibilities":  UserSites(app, self, config),
                "group-responsibilities": UserGroups(app, self, config) })
