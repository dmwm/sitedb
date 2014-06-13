from WMCore.REST.Server import RESTEntity, restcall
from WMCore.REST.Auth import authz_match
from WMCore.REST.Tools import tools
from WMCore.REST.Validation import *
from SiteDB.Regexps import *

class UserPNNs(RESTEntity):
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
      validate_strlist('username', param, safe, RX_USER)
      validate_strlist('pnn_name', param, safe, RX_NAME)
      validate_strlist('role', param, safe, RX_LABEL)
      validate_lengths(safe, 'username', 'pnn_name', 'role')
      authz_match(role=["Global Admin", "Operator"], group=["global","SiteDB"])

  @restcall
  @tools.expires(secs=300)
  def get(self):
    """Retrieve pnn privilege associations. The results aren't ordered in
    any particular way.

    :returns: sequence of rows of associations; field order in the returned
              *desc.columns*."""

    return self.api.query(None, None, """
      select 'phedex' type, ct.username, p.name pnn_name, r.title role
      from data_responsibility sr
      join contact ct on ct.id = sr.contact
      join role r on r.id = sr.role
      join phedex_node p on p.id = sr.pnn
      """)

  @restcall
  def put(self, username, pnn_name, role):
    """Insert new privilege associations. Global admin can update associations
    for any site. When more than one argument is given, there must be an equal
    number of arguments for all the parameters. For input validation requirements,
    see the field descriptions above. It is an error to attempt to insert an existing
    association triplet.

    :arg list username: new values;
    :arg list pnn_name: new values;
    :arg list role: new values;
    :returns: a list with a dict in which *modified* gives the number of objects
              inserted into the database, which is always *len(username).*"""

    return self.api.modify("""
      insert into data_responsibility (contact, role, pnn)
      values ((select id from contact where username = :username),
              (select id from role where title = :role),
              (select p.id from site s join phedex_node p on p.site = s.id where p.name = :pnn_name))
      """, username = username, pnn_name = pnn_name, role = role)

  @restcall
  def delete(self, username, pnn_name, role):
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

    return self.api.modify("""
      delete from data_responsibility
      where contact = (select id from contact where username = :username)
        and role = (select id from role where title = :role)
        and pnn = (select p.id from site s join phedex_node p on p.site = s.id where p.name = :pnn_name)
      """, username = username, pnn_name = pnn_name, role = role)
