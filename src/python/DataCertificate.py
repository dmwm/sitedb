from WMCore.REST.Server import RESTEntity, restcall
from WMCore.REST.Auth import authz_match
from WMCore.REST.Tools import tools
from WMCore.REST.Validation import *
from SiteDB.Regexps import *
from crypt import crypt

class Certificate(RESTEntity):
  """REST entity object for user accounts/certificate mapping.

  ==================== ========================= ==================================== ====================
  Contents             Meaning                   Value                                Constraints
  ==================== ========================= ==================================== ====================
  *username*           user account name         string matching :obj:`.RX_USER`      required
  *passwd*             password                  string matching :obj:`.RX_CPASSWD`   required
  ==================== ========================= ==================================== ====================
  """
  def validate(self, apiobj, method, api, param, safe):
    """Validate request input data."""
    authz = cherrypy.request.user
    validate_str('username', param, safe, RX_USER)
    validate_str('passwd', param, safe, RX_CPASSWD)
    if authz['method'] != 'X509Cert' or not authz['dn']:
      raise cherrypy.HTTPError(403, "You are not allowed to access this resource.")

  @restcall
  def post(self, username, passwd):
    """Associate account and certificate. The caller must be authenticated
    using X509 certificate, and must provide the hypernews account and its
    clear-text password. If the password matches the one in the database,
    the DN for the account is changed to the one making this HTTP request.
    For input validation requirements, see the field descriptions above.
    It is an error to attempt to update a non-existent account.

    :arg list username: single account name to update.
    :arg list passwd: the clear text password for the account.
    :returns: a list with a dict in which *modified* gives number of objects
              inserted into the database, which is always *1.*"""
    nrow = nmatch = 0
    c, _ = self.api.execute("""
      select c.username, p.passwd from contact c
      left join user_passwd p on p.username = c.username
      where c.username = :username""",
      username = username)
    for row in c:
      nrow += 1
      if row[1] and crypt(passwd, row[1]) == row[1]:
        nmatch += 1

    if nrow < 1 or nmatch < 1:
      raise MissingObject(info="Wrong account and/or password")
    elif nrow > 1 or nmatch > 1:
      raise TooManyObjects(info="Ambiguous account and password")

    return self.api.modify("""
      update contact set dn = :dn
      where username = :username
      """, username = [username],
      dn = [cherrypy.request.user['dn']])
