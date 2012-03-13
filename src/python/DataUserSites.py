from SiteDB.RESTServer import RESTEntity, restcall
from SiteDB.SiteAuth import oldsite_authz_match
from SiteDB.RESTTools import tools
from SiteDB.RESTValidation import *
from SiteDB.Regexps import *

class UserSites(RESTEntity):
  """REST entity for site privilege assocations.

  ==================== ========================= ==================================== ====================
  Contents             Meaning                   Value                                Constraints
  ==================== ========================= ==================================== ====================
  *username*           account name              string matching :obj:`.RX_USER`      required
  *site_name*          site name                 string matching :obj:`.RX_SITE`      required
  *role*               role title                string matching :obj:`.RX_LABEL`     required
  ==================== ========================= ==================================== ====================
  """
  def validate(self, apiobj, method, api, param, safe):
    """Validate request input data."""
    if method in ('PUT', 'DELETE'):
      validate_strlist('username', param, safe, RX_USER)
      validate_strlist('site_name', param, safe, RX_SITE)
      validate_strlist('role', param, safe, RX_LABEL)
      validate_lengths(safe, 'username', 'site_name', 'role')
      # Delay authz until we have database connection for name remapping.

  def _authz(self, sites):
    """Run late authorisation, remapping site names to canonical ones."""
    remap = {}
    for site in sites:
      oldsite_authz_match(self.api, remap,
                          role=["Global Admin", "Site Executive"],
                          group=["global"], site=[site])

  @restcall
  @tools.expires(secs=300)
  def get(self):
    """Retrieve site privilege associations. The results aren't ordered in
    any particular way.

    :returns: sequence of rows of associations; field order in the returned
              *desc.columns*."""

    return self.api.query(None, None, """
      select ct.username, s.name site_name, r.title role
      from site_responsibility sr
      join contact ct on ct.id = sr.contact
      join role r on r.id = sr.role
      join site s on s.id = sr.site
      """)

  @restcall
  def put(self, username, site_name, role):
    """Insert new privilege associations. Site executive can update their own
    site, global admin can update associations for any site. When more than
    one argument is given, there must be an equal number of arguments for
    all the parameters. For input validation requirements, see the field
    descriptions above. It is an error to attempt to insert an existing
    association triplet.

    :arg list username: new values;
    :arg list site_name: new values;
    :arg list role: new values;
    :returns: a list with a dict in which *modified* gives the number of objects
              inserted into the database, which is always *len(username).*"""

    self._authz(site_name)
    return self.api.modify("""
      insert into site_responsibility (contact, role, site)
      values ((select id from contact where username = :username),
              (select id from role where title = :role),
              (select id from site where name = :site_name))
      """, username = username, site_name = site_name, role = role)

  @restcall
  def delete(self, username, site_name, role):
    """Delete privilege associations. Site executive can update their own site,
    global admin can update associations for any site. When more than one
    argument is given, there must be an equal number of arguments for all
    the parameters. For input validation requirements, see the field
    descriptions above. It is an error to attempt to delete a non-existent
    association triplet.

    :arg list username: values to delete;
    :arg list site_name: values to delete;
    :arg list role: values to delete;
    :returns: a list with a dict in which *modified* gives the number of objects
              deleted from the database, which is always *len(username).*"""

    self._authz(site_name)
    return self.api.modify("""
      delete from site_responsibility
      where contact = (select id from contact where username = :username)
        and role = (select id from role where title = :role)
        and site = (select id from site where name = :site_name)
      """, username = username, site_name = site_name, role = role)
