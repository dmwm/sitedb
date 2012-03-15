from WMCore.REST.Server import RESTEntity, restcall, rows
from WMCore.REST.Tools import tools
from WMCore.REST.Validation import *
from SiteDB.Regexps import *
import cherrypy

class WhoAmI(RESTEntity):
  """REST entity describing the calling user."""
  def validate(self, apiobj, method, api, param, safe):
    """Validate request input data."""
    pass

  @restcall
  @tools.expires(secs=-1)
  def get(self):
    """Return information on the calling user.

    The user description contains the following fields. All the information
    is always present, regardless of authentication method. Data not known
    will be null, for example if access is made using CMS VO X509 certificate
    which is not registered in SiteDB, much of the information will be empty.

    ``name``
      The full name.

    ``login``
      CMS HyperNews account.

    ``dn``
      X509 certificate distinguished name.

    ``method``
      Authentication method, one of ``X509Cert``, ``X509Proxy``, ``HNLogin``,
      ``HostIP``, ``AUCookie`` or ``None``. In practice for SiteDB it will
      only be one of the first three since the latter three are not allowed
      authentication methods for SiteDB and this REST entity.

    ``roles``
      A dictionary of authorisation roles possessed by the user. For each
      role the person has, there will be a key-value pair where the key is
      the *canonical* role name, and the value is another dictionary with
      keys ``group`` and ``site``, each of whose value is a list. The lists
      will contain the *canonical* group and site names for which the role
      applies, respectively. Canonical names are all lower-case, with all
      word delimiters replaced with a single dash. For example the canonical
      role title for "Global Admin" is "global-admin", and for the site
      "T1\_CH\_CERN" it is "t1-ch-cern".

    :returns: sequence of one dictionary which describes the user."""

    user = cherrypy.request.user
    for authz in user['roles'].values():
      for k in ('site', 'group'):
        authz[k] = [x for x in authz[k]]
    return rows([cherrypy.request.user])
