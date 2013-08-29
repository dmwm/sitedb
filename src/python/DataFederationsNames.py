from WMCore.REST.Server import RESTEntity, restcall
from WMCore.REST.Auth import authz_match
from WMCore.REST.Tools import tools
from WMCore.REST.Validation import *
from SiteDB.Regexps import *
from operator import itemgetter

class FederationsNames(RESTEntity):
  """Entity object for federations names.

==================== ========================= ==================================== ====================
Contents Meaning Value Constraints
==================== ========================= ==================================== ====================
*fed_id*             federation id             matching :obj:`.RX_LABEL`            required, unique
*fed_name_id*        federation name id        matching :obj:`.RX_LABEL`            required, unique
==================== ========================= ==================================== ====================
"""
  def validate(self, apiobj, method, api, param, safe):
    """Validate request input data."""
    if method in ('GET', 'HEAD'):
      validate_rx('match', param, safe, optional = True)

    elif method in ('PUT'):
      validate_strlist('fed_id', param, safe, RX_LABEL)
      validate_strlist('fed_name_id', param, safe, RX_LABEL)
      authz_match(role=["Global Admin"], group=["global"])

    elif method in ('DELETE'):
      validate_strlist('fed_id', param, safe, RX_LABEL)
      authz_match(role=["Global Admin"], group=["global"])

  @restcall
  @tools.expires(secs=300)
  def get(self, match):
    """Retrieve federations names associations. The results aren't ordered in any particular way.

       :returns: sequence of rows of federations names associations; field order in the
                 returned *desc.columns*."""
    return self.api.query(match, itemgetter(0), "select * from all_federations_names");

  @restcall
  def put(self, fed_id, fed_name_id):
    """Insert new federations names associations. The caller needs to have global admin privileges.
       For input validation requirements, see the field descriptions above.
       It is an error to attempt to insert a federation name which already exists.

       :arg list fed_id: fed_id to insert.
       :arg list fed_name_id: federation name id to insert;

       :returns: a list with a dict in which *modified* gives number of objects
                 inserted into the database, which is always *len(fed_id).*"""
    return self.api.modify("""
      update all_federations_names SET federations_names_id = :fed_id
      where id = :fed_name_id and federations_names_id IS NULL
      """, fed_id = fed_id, fed_name_id = fed_name_id)

  @restcall
  def delete(self, fed_id):
    """Delete federations names association. The caller needs to have global admin privileges.
       For input validation requirements, see the field descriptions above.
       It is an error to attempt to insert a federation name which already exists.

       :arg list fed_id: federation id to delete.
       :returns: a list with a dict in which *modified* gives number of objects
                 inserted into the database, which is always *len(name).*"""
    return self.api.modify("""
      update all_federations_names SET federations_names_id = null
      where id = :fed_id""", fed_id = fed_id)
