from WMCore.REST.Server import RESTEntity, restcall
from WMCore.REST.Auth import authz_match
from WMCore.REST.Tools import tools
from WMCore.REST.Validation import *
from SiteDB.Regexps import *
from operator import itemgetter

class FederationsSites(RESTEntity):
  """Entity object for federations sites associations.

==================== ========================= ==================================== ====================
Contents             Meaning                   Value                                Constraints
==================== ========================= ==================================== ====================
*fed_id*             federation id             matching :obj:`.RX_LABEL`            required, unique
*site_id*            site id                   matching :obj:`.RX_LABEL`            required, unique
==================== ========================= ==================================== ====================
"""
  def validate(self, apiobj, method, api, param, safe):
    """Validate request input data."""
    if method in ('GET', 'HEAD'):
      validate_rx('match', param, safe, optional = True)

    elif method in ('PUT'):
      validate_strlist('fed_id', param, safe, RX_LABEL)
      validate_strlist('site_id', param, safe, RX_LABEL)
      authz_match(role=["Global Admin"], group=["global"])
    elif method in ('DELETE'):
      validate_strlist('site_id', param, safe, RX_LABEL)
      authz_match(role=["Global Admin"], group=["global"])

  @restcall
  @tools.expires(secs=300)
  def get(self, match):
    """Retrieve federations sites associations. The results aren't ordered in any particular way.

       :arg str match: optional regular expression to filter by *fed_id*

       :returns: sequence of rows of federations sites associations; field order in the
                 returned *desc.columns*."""
    return self.api.query(match, itemgetter(0), """
      select 'cms' type, s.id site_id, s.name site_name, c.name alias, fmap.federations_names_id fed_id,
             (select count(*) site_count from sites_federations_names_map where federations_names_id = fmap.federations_names_id) site_count
      from site s
      join site_cms_name_map cmap on cmap.site_id = s.id
      join cms_name c on c.id = cmap.cms_name_id
      left outer join sites_federations_names_map fmap on s.id = fmap.site_id""");

  @restcall
  def put(self, fed_id, site_id):
    """Insert new federations sites associations. The caller needs to have global admin privileges.
       For input validation requirements, see the field descriptions above.
       It is an error to attempt to insert a federation site association which already exists.

       :arg list fed_id: federation id to insert.
       :arg list site_id: site id to insert.

       :returns: a list with a dict in which *modified* gives number of objects
                 inserted into the database, which is always *len(name).*"""
    return self.api.modify("""
      insert into sites_federations_names_map (id, site_id, federations_names_id)
      values (sites_federations_names_map_sq.nextval, :site_id, :federations_names_id)
      """, site_id = site_id, federations_names_id = fed_id)

  @restcall
  def delete(self, site_id):
    """Delete federation site association. The caller needs to have global admin privileges.
       For input validation requirements, see the field descriptions above.
       It is an error to attempt to delete a non-existent federation site association.

       :arg list site_id: site id to delete.

       :returns: a list with a dict in which *modified* gives number of objects
                 deleted from the database, which is always *len(title).*"""
    return self.api.modify("delete from sites_federations_names_map where site_id = :site_id", site_id = site_id)
