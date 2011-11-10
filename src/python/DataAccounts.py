from SiteDB.RESTServer import RESTEntity, restcall
from SiteDB.RESTAuth import authz_match
from SiteDB.RESTTools import tools
from SiteDB.RESTValidation import *
from SiteDB.Regexps import *
from operator import itemgetter

class Accounts(RESTEntity):
  """REST entity object for user accounts.

  ==================== ========================= ================================== ====================
  Contents             Meaning                   Value                              Constraints
  ==================== ========================= ================================== ====================
  *username*           user account name         string matching :obj:`.RX_USER`    required, unique
  *passwd*             encrypted password        string matching :obj:`.RX_PASSWD`  required
  ==================== ========================= ================================== ====================
  """
  def validate(self, apiobj, method, api, param, safe):
    """Validate request input data."""
    if method in ('GET', 'HEAD'):
      validate_rx('match', param, safe, optional = True)

    elif method in ('PUT', 'POST'):
      validate_strlist('username', param, safe, RX_USER)
      validate_strlist('passwd', param, safe, RX_PASSWD)
      validate_lengths(safe, 'username', 'passwd')
      authz_match(role=["Global Admin"], group=["global"])

    elif method == 'DELETE':
      validate_strlist('username', param, safe, RX_USER)
      authz_match(role=["Global Admin"], group=["global"])

  @restcall
  @tools.expires(secs=300)
  def get(self, match):
    """Retrieve accounts.

    :arg string match: optional regular expression to filter by *username*
    :returns: sequence of rows of accounts; field order in the
              returned *desc.columns*."""
    return self.api.query(match, itemgetter(0),
		          "select username, passwd from user_passwd")

  @restcall
  def put(self, username, passwd):
    """Insert new accounts. The caller needs to have global admin privileges.
    For input validation requirements, see the field descriptions above.
    It is an error to attempt to insert an account which already exists.

    :arg list username: account names to insert.
    :arg list passwd: account passwords to insert; use "*" for locked one.
    :returns: a list with a dict in which *modified* gives number of objects
              inserted into the database, which is always *len(username).*"""
    return self.api.modify("""
      insert into user_passwd (username, passwd)
      values (:username, :passwd)
      """, username = username, passwd = passwd)

  @restcall
  def post(self, username, passwd):
    """Update passwords. The caller needs to have global admin privileges.
    For input validation requirements, see the field descriptions above.
    It is an error to attempt to update an account which does not exist.

    :arg list username: account names to modify.
    :arg list passwd: account passwords to update; use "*" for locked one.
    :returns: a list with a dict in which *modified* gives number of objects
              inserted into the database, which is always *len(username).*"""
    return self.api.modify("""
      update user_passwd
      set passwd = :passwd
      where username = :username
      """, username = username, passwd = passwd)

  @restcall
  def delete(self, position):
    """Delete accounts. The caller needs to have global admin privileges.
    For input validation requirements, see the field descriptions above.
    It is an error to attempt to delete a non-existent account.

    :arg list username: account names to delete.
    :returns: a list with a dict in which *modified* gives number of objects
              deleted from the database, which is always *len(username).*"""
    return self.api.modify("delete from user_passwd where username = :username",
		           username = username)
