from WMCore.REST.Server import RESTEntity, restcall
from WMCore.REST.Auth import authz_match
from WMCore.REST.Tools import tools
from WMCore.REST.Validation import *
from SiteDB.Regexps import *
from operator import itemgetter

class Groups(RESTEntity):
  """REST entity object for group names.

  ==================== ========================= ==================================== ====================
  Contents             Meaning                   Value                                Constraints
  ==================== ========================= ==================================== ====================
  *name*               group name                string matching :obj:`.RX_LABEL`     required, unique
  ==================== ========================= ==================================== ====================
  """
  def validate(self, apiobj, method, api, param, safe):
    """Validate request input data."""
    if method in ('GET', 'HEAD'):
      validate_rx('match', param, safe, optional = True)

    elif method in ('PUT', 'DELETE'):
      validate_strlist('name', param, safe, RX_LABEL)
      authz_match(role="Global Admin", group="global")

  @restcall
  @tools.expires(secs=300)
  def get(self, match):
    """Retrieve user groups. The results aren't ordered in any particular way.

    :arg str match: optional regular expression to filter by *name*
    :returns: sequence of rows of user group names; field order in the
              returned *desc.columns*."""
    return self.api.query(match, itemgetter(0), "select name from user_group")

  @restcall
  def put(self, name):
    """Insert new groups. The caller needs to have global admin privileges.
    For input validation requirements, see the field descriptions above.
    It is an error to attempt to insert a group which already exists.

    :arg list name: names to insert.
    :returns: a list with a dict in which *modified* gives number of objects
              inserted into the database, which is always *len(name).*"""
    return self.api.modify("""
      insert into user_group (name, id)
      values (:name, user_group_sq.nextval)
      """, name = name)

  @restcall
  def delete(self, name):
    """Delete groups. The caller needs to have global admin privileges.
    For input validation requirements, see the field descriptions above.
    It is an error to attempt to delete a non-existent group.

    :arg list name: names to delete.
    :returns: a list with a dict in which *modified* gives number of objects
              deleted from the database, which is always *len(name).*"""
    return self.api.modify("delete from user_group where name = :name", name = name)
