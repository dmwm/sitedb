from WMCore.REST.Server import RESTEntity, restcall
from WMCore.REST.Auth import authz_match
from WMCore.REST.Tools import tools
from WMCore.REST.Validation import *
from SiteDB.Regexps import *
from cherrypy import HTTPError

class UserGroups(RESTEntity):
  """REST entity for group privilege assocations.

  ==================== ========================= ==================================== ====================
  Contents             Meaning                   Value                                Constraints
  ==================== ========================= ==================================== ====================
  *username*           account name              string matching :obj:`.RX_USER`      required
  *user_group*         group name                string matching :obj:`.RX_LABEL`     required
  *role*               role title                string matching :obj:`.RX_LABEL`     required
  ==================== ========================= ==================================== ====================
  """
  def validate(self, apiobj, method, api, param, safe):
    """Validate request input data."""
    if method in ('PUT', 'DELETE'):
      validate_strlist('username', param, safe, RX_USER)
      validate_strlist('user_group', param, safe, RX_LABEL)
      validate_strlist('role', param, safe, RX_LABEL)
      validate_lengths(safe, 'username', 'user_group', 'role')
      for group in safe.kwargs['user_group']:
        try:
          authz_match(role=["Global Admin"], group=["global"])
        except HTTPError:
          authz_match(role=["Global Admin", "Admin"], group=[group])

  @restcall
  @tools.expires(secs=300)
  def get(self):
    """Retrieve group privilege associations. The results aren't ordered in
    any particular way.

    :returns: sequence of rows of associations; field order in the returned
              *desc.columns*."""

    return self.api.query(None, None, """
      select ct.username, g.name user_group, r.title role
      from group_responsibility gr
      join contact ct on ct.id = gr.contact
      join role r on r.id = gr.role
      join user_group g on g.id = gr.user_group
      """)

  @restcall
  def put(self, username, user_group, role):
    """Insert new privilege associations. The caller needs to be global admin
    in the global group, or global admin or admin in the group being changed.
    When more than one argument is given, there must be an equal number of
    arguments for all the parameters. For input validation requirements, see
    the field descriptions above. It is an error to attempt to insert an
    existing association triplet.

    :arg list username: new values;
    :arg list user_group: new values;
    :arg list role: new values;
    :returns: a list with a dict in which *modified* gives the number of objects
              inserted into the database, which is always *len(username).*"""

    return self.api.modify("""
      insert into group_responsibility (contact, role, user_group)
      values ((select id from contact where username = :username),
              (select id from role where title = :role),
              (select id from user_group where name = :user_group))
      """, username = username, user_group = user_group, role = role)

  @restcall
  def delete(self, username, user_group, role):
    """Delete privilege associations. The caller needs to be global admin
    in the global group, or global admin or admin in the group being changed.
    When more than one argument is given, there must be an equal number of
    arguments for all the parameters. For input validation requirements, see
    the field descriptions above. It is an error to attempt to delete a
    non-existent association triplet.

    :arg list username: values to delete;
    :arg list user_group: values to delete;
    :arg list role: values to delete;
    :returns: a list with a dict in which *modified* gives the number of objects
              deleted from the database, which is always *len(username).*"""

    return self.api.modify("""
      delete from group_responsibility
      where contact = (select id from contact where username = :username)
        and role = (select id from role where title = :role)
        and user_group = (select id from user_group where name = :user_group)
      """, username = username, user_group = user_group, role = role)
