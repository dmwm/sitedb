from WMCore.REST.Server import RESTEntity, restcall
from WMCore.REST.Auth import authz_match
from WMCore.REST.Tools import tools
from WMCore.REST.Validation import *
from SiteDB.Regexps import *

class Processing(RESTEntity):
  """REST entity for pnn`s privilege assocations.

  ==================== ========================= ==================================== ====================
  Contents             Meaning                   Value                                Constraints
  ==================== ========================= ==================================== ====================
  *username*           account name              string matching :obj:`.RX_USER`      required
  *pnn_name*           pnn name                  string matching :obj:`.RX_NAME`      required
  *role*               role title                string matching :obj:`.RX_LABEL`     required
  ==================== ========================= ==================================== ====================
  """
  def validate(self, apiobj, method, api, param, safe):
    """Validate request input data."""
    if method in ('PUT', 'DELETE'):
      validate_strlist('phedex_name', param, safe, RX_NAME)
      validate_strlist('psn_name', param, safe, RX_NAME)
      validate_lengths(safe, 'phedex_name', 'psn_name')
      authz_match(role=["Global Admin", "Operator"], group=["global","SiteDB"])

  @restcall
  @tools.expires(secs=300)
  def get(self):
    """Retrieve pnn privilege associations. The results aren't ordered in
    any particular way.

    :returns: sequence of rows of associations; field order in the returned
              *desc.columns*."""

    return self.api.query(None, None, """
      select p.name phedex_name, psn.name psn_name
        from psn_node_phedex_name_map pmap
        join phedex_node p on p.id = pmap.phedex_id
        join psn_node psn on psn.id = pmap.psn_id
        join site s on s.id = p.site
      """)

  @restcall
  def put(self, phedex_name, psn_name):
    """Insert new privilege associations. Global admin can update associations
              inserted into the database, which is always *len(username).*"""

    return self.api.modify("""
      insert into psn_node_phedex_name_map(phedex_id, psn_id)
      VALUES ((select id from phedex_node where name = :phedex_name),
              (select id from psn_node where name = :psn_name))
      """, phedex_name = phedex_name, psn_name = psn_name)

  @restcall
  def delete(self, phedex_name, psn_name):
    """Delete privilege associations. Site executive can update their own site,
              deleted from the database, which is always *len(username).*"""

    return self.api.modify("""
      delete from psn_node_phedex_name_map
        where phedex_id = (select id from phedex_node where name = :phedex_name)
        and psn_id = (select id from psn_node where name = :psn_name) 
      """, phedex_name = phedex_name, psn_name = psn_name)
