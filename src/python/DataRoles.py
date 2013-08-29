from WMCore.REST.Server import RESTEntity, restcall
from WMCore.REST.Auth import authz_match
from WMCore.REST.Tools import tools
from WMCore.REST.Validation import *
from SiteDB.Regexps import *
from operator import itemgetter

class Roles(RESTEntity):
  """REST entity object for role names.

  ==================== ========================= ====================================== ====================
  Contents             Meaning                   Value                                  Constraints
  ==================== ========================= ====================================== ====================
  *title*              role title                string matching :obj:`.RX_LABEL`       required, unique
  *description*        role description          string matching :obj:`.RX_DESCRIPTION` optional
  ==================== ========================= ====================================== ====================
  """
  def validate(self, apiobj, method, api, param, safe):
    """Validate request input data."""
    if method in ('GET', 'HEAD'):
      validate_rx('match', param, safe, optional = True)

    elif method in ('PUT', 'DELETE'):
      validate_strlist('title', param, safe, RX_LABEL)
      authz_match(role=["Global Admin"], group=["global"])

    elif method in ('POST'):
      validate_strlist('title', param, safe, RX_LABEL)
      validate_strlist('description', param, safe, RX_DESCRIPTION)
      authz_match(role=["Global Admin"], group=["global"])

  @restcall
  @tools.expires(secs=300)
  def get(self, match):
    """Retrieve roles. The results aren't ordered in any particular way.

    :arg str match: optional regular expression to filter by *title*
    :returns: sequence of rows of role names and descriptions; field order in the
              returned *desc.columns*."""
    return self.api.query(match, itemgetter(0), "select title, description from role")

  @restcall
  def put(self, title):
    """Insert new roles. The caller needs to have global admin privileges.
    For input validation requirements, see the field descriptions above.
    It is an error to attempt to insert a role which already exists.

    :arg list title: names to insert.
    :returns: a list with a dict in which *modified* gives number of objects
              inserted into the database, which is always *len(title).*"""
    return self.api.modify("""
      insert into role (title, id)
      values (:title, role_sq.nextval)
      """, title = title)

  @restcall
  def delete(self, title):
    """Delete roles. The caller needs to have global admin privileges.
    For input validation requirements, see the field descriptions above.
    It is an error to attempt to delete a non-existent role.

    :arg list title: names to delete.
    :returns: a list with a dict in which *modified* gives number of objects
              deleted from the database, which is always *len(title)*."""
    return self.api.modify("delete from role where title = :title", title = title)

  @restcall
  def post(self, title, description):
    """Insert Role description. The caller needs to have global admin privileges.
    For input validation requirements, see the field descriptions above.
    It is an error to attmept to update a non-existent role.

    :arg list title: name of the role.
    :arg list description: role description.
    :returns: a list with a dict in which *modified* gives number of objects
              updated in database. which is not alwaus *len(title)*."""
    return self.api.modify(""" update role set description = :description_i
                               where title = :title_i""",
                               description_i = description, title_i = title)
