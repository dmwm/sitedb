from SiteDB.RESTServer import RESTEntity, restcall
from SiteDB.RESTAuth import authz_match
from SiteDB.RESTTools import tools
from SiteDB.RESTValidation import *
from SiteDB.Regexps import *

class UserGroups(RESTEntity):
  def validate(self, apiobj, method, api, param, safe):
    if method in ('PUT', 'DELETE'):
      validate_strlist('email', param, safe, RX_EMAIL)
      validate_strlist('user_group', param, safe, RX_LABEL)
      validate_strlist('role', param, safe, RX_LABEL)
      validate_lengths(safe, 'email', 'user_group', 'role')
      authz_match(role=["Global Admin"], group=["global"])

  @restcall
  @tools.expires(secs=300)
  def get(self):
    return self.api.query(None, None, """
      select ct.email, g.name user_group, r.title role
      from group_responsibility gr
      join contact ct on ct.id = gr.contact
      join role r on r.id = gr.role
      join user_group g on g.id = gr.user_group
      """)

  @restcall
  def put(self, email, user_group, role):
    return self.api.modify("""
      insert into group_responsibility (contact, role, user_group)
      values ((select id from contact where email = :email),
              (select id from role where title = :role),
              (select id from user_group where name = :user_group))
      """, email = email, user_group = user_group, role = role)

  @restcall
  def delete(self, email, user_group, role):
    return self.api.modify("""
      delete from group_responsibility
      where contact = (select id from contact where email = :email)
        and role = (select id from role where title = :role)
        and user_group = (select id from user_group where name = :user_group)
      """, email = email, user_group = user_group, role = role)
