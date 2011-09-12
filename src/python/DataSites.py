from SiteDB.RESTServer import RESTEntity, restcall, rows
from SiteDB.RESTAuth import authz_match
from SiteDB.RESTTools import tools
from SiteDB.RESTValidation import *
from SiteDB.Regexps import *
from operator import itemgetter
from cherrypy import request

class Sites(RESTEntity):
  def validate(self, apiobj, method, api, param, safe):
    if method in ('GET', 'HEAD'):
      validate_rx('match', param, safe, optional = True)

    elif method in ('PUT', 'POST'):
      validate_strlist('site', param, safe, RX_SITE)
      validate_strlist('tier', param, safe, RX_TIER)
      validate_strlist('country', param, safe, RX_COUNTRY)
      validate_strlist('usage', param, safe, RX_USAGE)
      validate_strlist('url', param, safe, RX_URL)
      validate_strlist('logourl', param, safe, RX_URL)
      validate_numlist('gocdbid', param, safe, bare = True)
      validate_strlist('devel_release', param, safe, RX_YES_NO)
      validate_strlist('manual_install', param, safe, RX_YES_NO)
      validate_lengths(safe, 'site', 'tier', 'country',
                       'usage', 'url', 'logourl', 'gocdbid',
                       'devel_release', 'manual_install')

      for site in safe.kwargs['site']:
        authz_match(role=["Global Admin", "Site Admin"],
                    group=["global"], site=[site])

    elif method == 'DELETE':
      validate_strlist('site', param, safe, RX_SITE)
      authz_match(role=["Global Admin"], group=["global"])

  @restcall
  @tools.expires(secs=300)
  def get(self, match):
    return self.api.query(match, itemgetter(0), """
      select s.name, t.pos tier_level, t.name tier, s.country, s.usage,
             s.url, s.logourl, sam.gocdbid, s.getdevlrelease, s.manualinstall
      from site s
      join tier t on t.id = s.tier
      left join site_cms_name_map cmap on cmap.site_id = s.id
      left join sam_cms_name_map smap on smap.cms_name_id = cmap.cms_name_id
      left join sam_name sam on sam.id = smap.sam_id
      """)

  @restcall
  def post(self, site, tier, country, usage, url, logourl,
           gocdbid, devel_release, manual_install):
    # FIXME: gocdbid - use view to update site?
    return self.api.modify("""
      update site set
        tier = (select id from tier where name = :tier),
        country = :country,
        usage = :usage,
        url = :url,
        logourl = :logourl,
        -- gocdbid = :gocdbid,
        getdevlrelease = :devel_release,
        manualinstall = :manual_install
      where name = :name
      """, name = site, tier = tier, country = country,
      usage = usage, url = url, logourl = logourl, # gocdbid = gocdbid,
      devel_release = devel_release, manual_install = manual_install)

  @restcall
  def put(self, site, tier, country, usage, url, logourl,
          gocdbid, devel_release, manual_install):
    return self.api.modify("""
      insert into site
      (id, name, tier, country, usage, url, logourl, -- gocdbid,
       getdevlrelease, manualinstall)
      values (site_sq.nextval, :name, (select id from tier where name = :tier),
              :country, :usage, :url, :logourl, -- :gocdbid,
              :devel_release, :manual_install)
      """, name = site, tier = tier, country = country,
      usage = usage, url = url, logourl = logourl, # gocdbid = gocdbid,
      devel_release = devel_release, manual_install = manual_install)

  @restcall
  def delete(self, site):
    return self.api.modify("""
      delete from site where name = :site
      """, site = site)

class SiteNames(RESTEntity):
  def validate(self, apiobj, method, api, param, safe):
    if method in ('GET', 'HEAD'):
      validate_rx('match', param, safe, optional = True)

    elif method in ('PUT', 'DELETE'):
      validate_strlist('type', param, safe, RX_NAME_TYPE)
      validate_strlist('site', param, safe, RX_SITE)
      validate_strlist('alias', param, safe, RX_NAME)
      validate_lengths(safe, 'type', 'site', 'alias')
      for site in safe.kwargs['site']:
        authz_match(role=["Global Admin", "Site Admin"],
                    group=["global"], site=[site])

  @restcall
  @tools.expires(secs=300)
  def get(self, match):
    return self.api.query(match, itemgetter(1), """
      (select 'lcg' type, s.name site_name, sam.name alias
       from site s
       join site_cms_name_map cmap on cmap.site_id = s.id
       join sam_cms_name_map smap on smap.cms_name_id = cmap.cms_name_id
       join sam_name sam on sam.id = smap.sam_id)
      union
      (select 'cms' type, s.name site_name, c.name alias
       from site s
       join site_cms_name_map cmap on cmap.site_id = s.id
       join cms_name c on c.id = cmap.cms_name_id)
      union
      (select 'phedex' type, s.name site_name, p.name alias
       from site s
       join phedex_node p on p.site = s.id)
      """)

  @restcall
  def put(self, type, site, alias):
    binds = self.api.bindmap(type = type, site = site, alias = alias)
    lcg = filter(lambda b: b['type'] == 'lcg', binds)
    cms = filter(lambda b: b['type'] == 'cms', binds)
    phedex = filter(lambda b: b['type'] == 'phedex', binds)
    for b in binds: del b['type']
    updated = 0

    if cms:
      c, _ = self.api.executemany("""
        insert all
        into cms_name (id, name) values (cms_name_sq.nextval, alias)
        into site_cms_name_map (site_id, cms_name_id) values (site_id, cms_name_sq.nextval)
        select s.id site_id, :alias alias
        from site s where s.name = :site
        """, cms)
      self.api.rowstatus(c, 2*len(cms))
      updated += c.rowcount / 2

    if lcg:
      c, _ = self.api.executemany("""
        insert all
        into sam_name (id, name) values (sam_name_sq.nextval, alias)
        into sam_cms_name_map (cms_name_id, sam_id) values (cms_id, sam_name_sq.nextval)
        select cmap.cms_name_id cms_id, :alias alias
        from site s join site_cms_name_map cmap on cmap.site_id = s.id
        where s.name = :site
        """, lcg)
      self.api.rowstatus(c, 2*len(lcg))
      updated += c.rowcount / 2

    if phedex:
      c, _ = self.api.executemany("""
        insert into phedex_node (id, site, name)
        select phedex_node_sq.nextval, s.id, :alias
        from site s where s.name = :site
        """, phedex)
      self.api.rowstatus(c, len(phedex))
      updated += c.rowcount

    result = rows([{ "modified": updated }])
    request.dbconn.commit()
    return result

  @restcall
  def delete(self, type, site, alias):
    binds = self.api.bindmap(type = type, site = site, alias = alias)
    lcg = filter(lambda b: b['type'] == 'lcg', binds)
    cms = filter(lambda b: b['type'] == 'cms', binds)
    phedex = filter(lambda b: b['type'] == 'phedex', binds)
    for b in binds: del b['type']
    updated = 0

    if cms:
      c, _ = self.api.executemany("""
        delete from cms_name
        where id in (select cmap.cms_name_id
                     from site s
                     join site_cms_name_map cmap on cmap.site_id = s.id
                     where s.name = :site)
          and name = :alias
        """, cms)
      self.api.rowstatus(c, len(cms))
      updated += c.rowcount

    if lcg:
      c, _ = self.api.executemany("""
        delete from sam_name
        where id in (select smap.sam_id
                     from site s
                     join site_cms_name_map cmap on cmap.site_id = s.id
                     join sam_cms_name_map smap on smap.cms_name_id = cmap.cms_name_id
                     where s.name = :site)
           and name = :alias
        """, lcg)
      self.api.rowstatus(c, len(lcg))
      updated += c.rowcount

    if phedex:
      c, _ = self.api.executemany("""
        delete from phedex_node
        where site = (select s.id from site s where s.name = :site)
          and name = :alias
        """, phedex)
      self.api.rowstatus(c, len(phedex))
      updated += c.rowcount

    result = rows([{ "modified": updated }])
    request.dbconn.commit()
    return result

# class SiteLinks(RESTEntity):
#   def validate(self, apiobj, method, api, param, safe):
#     pass
#
#   @restcall
#   @tools.expires(secs=300)
#   def get(self):
#     return self.api.query(None, None, """
#       select s.name, l.url
#       from site s
#       join sitelinks l on l.siteid = s.id
#     """)

class SiteResources(RESTEntity):
  def validate(self, apiobj, method, api, param, safe):
    if method in ('PUT', 'DELETE'):
      validate_strlist('site', param, safe, RX_SITE)
      validate_strlist('type', param, safe, RX_RES_TYPE)
      validate_strlist('fqdn', param, safe, RX_FQDN)

    if method == 'PUT':
      validate_strlist('is_primary', param, safe, RX_YES_NO)
      validate_lengths(safe, 'site', 'type', 'fqdn', 'is_primary')
    elif method == 'DELETE':
      validate_lengths(safe, 'site', 'type', 'fqdn')

    if method in ('PUT', 'DELETE'):
      for site in safe.kwargs['site']:
        authz_match(role=["Global Admin", "Site Admin"],
                    group=["global"], site=[site])

  @restcall
  @tools.expires(secs=300)
  def get(self):
    return self.api.query(None, None, """
      select s.name, r.type, r.fqdn, r.is_primary
      from site s
      join resource_element r on r.site = s.id
    """)

  @restcall
  def put(self, site, type, fqdn, is_primary):
    return self.api.modify("""
      insert into resource_element (id, site, fqdn, type, is_primary)
      select resource_element_sq.nextval, s.id, :fqdn, :type, :is_primary
      from site s where s.name = :site
      """, site=site, type=type, fqdn=fqdn, is_primary=is_primary)

  @restcall
  def delete(self, site, type, fqdn):
    return self.api.modify("""
      delete from resource_element
      where site = (select s.id from site s where s.name = :site)
        and fqdn = :fqdn
        and type = :type
      """, site=site, type=type, fqdn=fqdn)

class SiteAssociations(RESTEntity):
  def validate(self, apiobj, method, api, param, safe):
    if method in ('PUT', 'DELETE'):
      validate_strlist('parent', param, safe, RX_SITE)
      validate_strlist('child',  param, safe, RX_SITE)
      validate_lengths(safe, 'parent', 'child')
      for site in safe.kwargs['parent']:
        authz_match(role=["Global Admin", "Site Admin"],
                    group=["global"], site=[site])

  @restcall
  @tools.expires(secs=300)
  def get(self):
    return self.api.query(None, None, """
      select p.name parent_site, c.name child_site
      from site_association sa
      join site p on p.id = sa.parent_site
      join site c on c.id = sa.child_site
    """)

  @restcall
  def put(self, parent, child):
    return self.api.modify("""
      insert into site_association (parent_site, child_site)
      values ((select id from site where name = :parent),
              (select id from site where name = :child))
      """, parent=parent, child=child)

  @restcall
  def delete(self, parent, child):
    return self.api.modify("""
      delete from site_association
      where parent_site = (select id from site where name = :parent)
        and child_site = (select id from site where name = :child)
      """, parent=parent, child=child)
