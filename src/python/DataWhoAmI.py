from SiteDB.RESTServer import RESTEntity, restcall, rows
from SiteDB.RESTTools import tools
from SiteDB.RESTValidation import *
from SiteDB.Regexps import *
import cherrypy

class WhoAmI(RESTEntity):
  def validate(self, apiobj, method, api, param, safe):
    pass

  @restcall
  @tools.expires(secs=86400)
  def get(self):
    user = cherrypy.request.user
    for authz in user['roles'].values():
      for k in ('site', 'group'):
        authz[k] = [x for x in authz[k]]
    return rows([cherrypy.request.user])
