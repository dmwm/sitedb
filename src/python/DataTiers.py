from WMCore.REST.Server import RESTEntity, restcall
from WMCore.REST.Auth import authz_match
from WMCore.REST.Tools import tools
from WMCore.REST.Validation import *
from SiteDB.Regexps import *
from operator import itemgetter

class Tiers(RESTEntity):
  """REST entity object for tier names.

  ==================== ========================= ================================== ====================
  Contents             Meaning                   Value                              Constraints
  ==================== ========================= ================================== ====================
  *position*           tier rank                 non-negative integer               required, unique
  *name*               tier name                 string matching :obj:`.RX_TIER`    required, unique
  ==================== ========================= ================================== ====================
  """
  def validate(self, apiobj, method, api, param, safe):
    """Validate request input data."""
    if method in ('GET', 'HEAD'):
      validate_rx('match', param, safe, optional = True)

    elif method == 'PUT':
      validate_numlist('position', param, safe, bare = True)
      validate_strlist('name', param, safe, RX_TIER)
      validate_lengths(safe, 'position', 'name')
      authz_match(role=["Global Admin"], group=["global"])

    elif method == 'DELETE':
      validate_numlist('position', param, safe, bare = True)
      authz_match(role=["Global Admin"], group=["global"])

  @restcall
  @tools.expires(secs=300)
  def get(self, match):
    """Retrieve tiers. The results aren't ordered in any particular way.

    :arg str match: optional regular expression to filter by *name*
    :returns: sequence of rows of tiers; field order in the
              returned *desc.columns*."""
    return self.api.query(match, itemgetter(1),
		          "select pos position, name from tier")

  @restcall
  def put(self, position, name):
    """Insert new tiers. The caller needs to have global admin privileges.
    For input validation requirements, see the field descriptions above.
    It is an error to attempt to insert a tier which already exists.

    :arg list position: positions to insert.
    :arg list name: names to insert.
    :returns: a list with a dict in which *modified* gives number of objects
              inserted into the database, which is always *len(position).*"""
    return self.api.modify("""
      insert into tier (id, pos, name)
      values (tier_sq.nextval, :position, :name)
      """, position = position, name = name)

  @restcall
  def delete(self, position):
    """Delete tiers. The caller needs to have global admin privileges.
    For input validation requirements, see the field descriptions above.
    It is an error to attempt to delete a non-existent tier.

    :arg list position: tiers to delete.
    :returns: a list with a dict in which *modified* gives number of objects
              deleted from the database, which is always *len(position).*"""
    return self.api.modify("delete from tier where pos = :position",
		           position = position)
