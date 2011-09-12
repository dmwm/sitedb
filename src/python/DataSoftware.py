from SiteDB.RESTServer import RESTEntity, restcall, rows
from SiteDB.RESTAuth import authz_match
from SiteDB.RESTTools import tools
from SiteDB.RESTValidation import *
from SiteDB.Regexps import *

class Software(RESTEntity):
  def validate(self, apiobj, method, api, param, safe):
    if method in ('PUT', 'DELETE'):
      validate_strlist('site',    param, safe, RX_SITE)
      validate_strlist('ce',      param, safe, RX_FQDN)
      validate_strlist('release', param, safe, RX_RELEASE)
      validate_strlist('arch',    param, safe, RX_ARCH)
      validate_lengths(safe, 'site', 'ce', 'release', 'arch')
      for site in safe.kwargs['site']:
        authz_match(role=["Global Admin", "Site Admin"],
                    group=["global"], site=[site])

  @restcall
  @tools.expires(secs=300)
  def get(self):
    return self.api.query(None, None, """
      select s.name site, r.fqdn ce, pr.release, pr.arch
      from site s
      join resource_element r on r.site = s.id
      join pinned_releases pr on pr.ce_id = r.id
      where r.type = 'CE'
    """)

  @restcall
  def put(self, site, ce, release, arch):
    return self.api.modify("""
      insert into pinned_releases (ce_id, release, arch)
      select r.id, :release, :arch
      from site s
      join resource_element r on r.site = s.id
      where s.name = :site
        and r.type = 'CE'
        and r.fqdn = :fqdn
      """, site=site, fqdn=ce, release=release, arch=arch)

  @restcall
  def delete(self, site, ce, release, arch):
    return self.api.modify("""
      delete from pinned_releases
      where ce_id in (select r.id
                      from site s
                      join resource_element r on r.site = s.id
                      where s.name = :site
                        and r.type = 'CE'
                        and r.fqdn = :fqdn)
        and release = :release
        and arch = :arch
      """, site=site, fqdn=ce, release=release, arch=arch)
