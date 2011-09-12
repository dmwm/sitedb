from SiteDB.RESTServer import RESTEntity, restcall
from SiteDB.RESTAuth import authz_match
from SiteDB.RESTTools import tools
from SiteDB.RESTValidation import *
from SiteDB.Regexps import *

class UserSites(RESTEntity):
  def validate(self, apiobj, method, api, param, safe):
    if method in ('PUT', 'DELETE'):
      validate_strlist('email', param, safe, RX_EMAIL)
      validate_strlist('site', param, safe, RX_SITE)
      validate_strlist('role', param, safe, RX_LABEL)
      validate_lengths(safe, 'email', 'site', 'role')
      for site in safe.kwargs['site']:
        authz_match(role=["Global Admin", "Site Admin"],
                    group=["global"], site=[site])

  @restcall
  @tools.expires(secs=300)
  def get(self):
    return self.api.query(None, None, """
      select ct.email, s.name site, r.title role
      from site_responsibility sr
      join contact ct on ct.id = sr.contact
      join role r on r.id = sr.role
      join site s on s.id = sr.site
      """)

  @restcall
  def put(self, email, site, role):
    return self.api.modify("""
      insert into site_responsibility (contact, role, site)
      values ((select id from contact where email = :email),
              (select id from role where title = :role),
              (select id from site where name = :site))
      """, email = email, site = site, role = role)

  @restcall
  def delete(self, email, site, role):
    return self.api.modify("""
      delete from site_responsibility
      where contact = (select id from contact where email = :email)
        and role = (select id from role where title = :role)
        and site = (select id from site where name = :site)
      """, email = email, site = site, role = role)
