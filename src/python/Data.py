from WMCore.REST.Server import DatabaseRESTApi
from SiteDB.DataWhoAmI import *
from SiteDB.DataRoles import *
from SiteDB.DataGroups import *
from SiteDB.DataPeople import *
from SiteDB.DataSites import *
from SiteDB.DataPledges import *
from SiteDB.DataSoftware import *
from SiteDB.DataUserGroups import *
from SiteDB.DataUserSites import *
from SiteDB.DataLdapSync import *
from SiteDB.DataFederations import *
from SiteDB.DataFederationsSites import *
from SiteDB.DataFederationsPledges import *
from SiteDB.DataRebusFetch import *
from SiteDB.DataESPCredit import *
from SiteDB.DataUserPNNs import *

class Data(DatabaseRESTApi):
  """Server object for REST data access API."""
  def __init__(self, app, config, mount):
    """
    :arg app: reference to application object; passed to all entities.
    :arg config: reference to configuration; passed to all entities.
    :arg str mount: API URL mount point; passed to all entities."""
    DatabaseRESTApi.__init__(self, app, config, mount)
    self._add({ "whoami":                 WhoAmI(app, self, config, mount),
                "ldapsync":               LdapSync(app, self, config, mount),
                "rebusfetch":             RebusFetch(app, self, config, mount),
                "roles":                  Roles(app, self, config, mount),
                "groups":                 Groups(app, self, config, mount),
                "people":                 People(app, self, config, mount),
                "sites":                  Sites(app, self, config, mount),
                "site-names":             SiteNames(app, self, config, mount),
                "site-resources":         SiteResources(app, self, config, mount),
                "site-associations":      SiteAssociations(app, self, config, mount),
                "resource-pledges":       Pledges(app, self, config, mount),
                "pinned-software":        Software(app, self, config, mount),
                "site-responsibilities":  UserSites(app, self, config, mount),
                "group-responsibilities": UserGroups(app, self, config, mount),
                "data-responsibilities":  UserPNNs(app, self, config, mount),
                "federations":            Federations(app, self, config, mount),
                "federations-sites":      FederationsSites(app, self, config, mount),
                "federations-pledges":    FederationsPledges(app, self, config, mount),
                "esp-credit":             ESPCredit(app, self, config, mount)})
