from WMCore.REST.Server import RESTEntity, restcall
from WMCore.REST.Auth import authz_match
from WMCore.REST.Tools import tools
from WMCore.REST.Validation import *
from SiteDB.Regexps import *
from operator import itemgetter

class Federations(RESTEntity):
  """Entity object for federations names.

==================== ========================= ==================================== ====================
Contents             Meaning                   Value                                Constraints
==================== ========================= ==================================== ====================
*name*               name title string         matching :obj:`.RX_LABEL`            required, unique
==================== ========================= ==================================== ====================
"""
  def validate(self, apiobj, method, api, param, safe):
    """Validate request input data."""
    if method in ('GET', 'HEAD'):
      validate_rx('match', param, safe, optional = True)

    elif method in ('DELETE'):
      validate_strlist('name', param, safe, RX_FEDERATION)
      authz_match(role=["Global Admin"], group=["global"])

  @restcall
  @tools.expires(secs=300)
  def get(self, match):
    """Retrieve federations. The results aren't ordered in any particular way.

    :arg str match: optional regular expression to filter by *title*

    :returns: sequence of rows of federations names; field order in the
              returned *id, name, site_count*."""
    return self.api.query(match, itemgetter(0), """
      select fn.id id, fn.name name, sum(case when sfnm.site_id is null then 0 else 1 end) site_count, fn.country country from all_federations_names fn
             left outer join sites_federations_names_map sfnm
                  on sfnm.federations_names_id = fn.id
              group by fn.id, fn.name, fn.country order by country, name, site_count""");

  @restcall
  def delete(self, name):
    """Delete federation. The caller needs to have global admin privileges.
       For input validation requirements, see the field descriptions above.
       It is an error to attempt to delete a non-existent federation.

       :arg list title: names to delete.

       :returns: nothing*"""
    self.api.modify("delete from all_federations_names where name = :name", name = name)

    elf.api.modify("""delete from sites_federations_names_map where all_federations_names_id =
                       (select id from all_federations_names where name = :name)""", name = name)
