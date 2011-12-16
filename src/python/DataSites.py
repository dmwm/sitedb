from SiteDB.RESTServer import RESTEntity, restcall, rows
from SiteDB.RESTAuth import authz_match
from SiteDB.RESTTools import tools
from SiteDB.RESTValidation import *
from SiteDB.Regexps import *
from operator import itemgetter
from cherrypy import request

######################################################################
######################################################################
class Sites(RESTEntity):
  """REST entity object for sites.

  ==================== ========================= ==================================== ====================
  Contents             Meaning                   Value                                Constraints
  ==================== ========================= ==================================== ====================
  *site*               site name                 string matching :obj:`.RX_SITE`      required, unique
  *tier_level*         tier level                integer >= 0                         required
  *tier*               tier label                string matching :obj:`.RX_TIER`      required
  *country*            country                   string matching :obj:`.RX_COUNTRY`   required
  *usage*              grid flavour              string matching :obj:`.RX_USAGE`     required
  *url*                site web page             string matching :obj:`.RX_URL`       required
  *logourl*            logo image location       string matching :obj:`.RX_URL`       required
  *gocdbid*            id in goc database        bare integer                         required
  *devel_release*      (unknown)                 string matching :obj:`.RX_YES_NO`    required
  *manual_install*     (unknown)                 string matching :obj:`.RX_YES_NO`    required
  ==================== ========================= ==================================== ====================
  """
  def validate(self, apiobj, method, api, param, safe):
    """Validate request input data."""
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
    """Retrieve sites. The results aren't ordered in any particular way.

    :arg str match: optional regular expression to filter by *name*
    :returns: sequence of rows of sites; field order in the returned
              *desc.columns*."""
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
    """Update the information for sites identified by `site`. A site admin
    can update their own site's record, global admins the info for all the
    sites. When more than one argument is given, there must be equal number
    of arguments for all the parameters.  It is an error to attempt to
    update a non-existent `site`.

    :arg list site: site names to insert;
    :arg list tier: new values;
    :arg list country: new values;
    :arg list usage: new values;
    :arg list url: new values;
    :arg list logourl: new values;
    :arg list gocdbid: new values;
    :arg list devel_release: new values;
    :arg list manual_install: new values;
    :returns: a list with a dict in which *modified* gives number of objects
              ipdated in the database, which is always *len(site).*"""
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
    """Insert new sites. The caller needs to have global admin privileges.
    When more than one argument is given, there must equal number of
    arguments for all the parameters. For input validation requirements,
    see the field descriptions above.  It is an error to attempt to insert
    a `site` which already exists.

    :arg list site: site names to insert;
    :arg list tier: new values;
    :arg list country: new values;
    :arg list usage: new values;
    :arg list url: new values;
    :arg list logourl: new values;
    :arg list gocdbid: new values;
    :arg list devel_release: new values;
    :arg list manual_install: new values;
    :returns: a list with a dict in which *modified* gives number of objects
              inserted into the database, which is always *len(site).*"""
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
    """Delete site records. Only a global admin can delete site records.
    For input validation requirements, see the field descriptions above.
    It is an error to attempt to delete a non-existent `site`.

    :arg list site: names of sites to delete.
    :returns: a list with a dict in which *modified* gives number of objects
              deleted from the database, which is always *len(site).*"""
    return self.api.modify("""
      delete from site where name = :site
      """, site = site)

######################################################################
######################################################################
class SiteNames(RESTEntity):
  """REST entity for site name aliases.

  ==================== ========================= ==================================== ====================
  Contents             Meaning                   Value                                Constraints
  ==================== ========================= ==================================== ====================
  *type*               alias type                string matching :obj:`.RX_NAME_TYPE` required, unique
  *site*               site name                 string matching :obj:`.RX_SITE`      required, unique
  *alias*              name alias                string matching :obj:`.RX_NAME`      required, unique
  ==================== ========================= ==================================== ====================
  """
  def validate(self, apiobj, method, api, param, safe):
    """Validate request input data."""

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
    """Retrieve site name associations. The results aren't ordered in any
    particular way.

    :arg str match: optional regular expression to filter by *name*
    :returns: sequence of rows of site names; field order in the returned
              *desc.columns*."""

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
    """Insert new site names. Site admin can update their own site, global
    admin can update names for all the sites. When more than one argument is
    given, there must be an equal number of arguments for all the parameters.
    For input validation requirements, see the field descriptions above.
    It is an error to attempt to insert an existing name alias triplet.

    :arg list type: new values;
    :arg list site: new values;
    :arg list alias: new values;
    :returns: a list with a dict in which *modified* gives the number of objects
              inserted into the database, which is always *len(type).*"""

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
    """Delete site name associations. Site admin can update their own site,
    global admin can update names for all the sites. When more than one
    argument is given, there must be an equal number of arguments for all
    the parameters. For input validation requirements, see the field
    descriptions above. It is an error to attempt to delete a non-existent
    site name association.

    :arg list type: values to delete;
    :arg list site: values to delete;
    :arg list alias: values to delete;
    :returns: a list with a dict in which *modified* gives the number of objects
              deleted from the database, which is always *len(type).*"""
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

######################################################################
######################################################################
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

######################################################################
######################################################################
class SiteResources(RESTEntity):
  """REST entity for site CE, SE resources.

  ==================== ========================= ==================================== ====================
  Contents             Meaning                   Value                                Constraints
  ==================== ========================= ==================================== ====================
  *site*               site name                 string matching :obj:`.RX_SITE`      required, unique
  *type*               resource type             string matching :obj:`.RX_RES_TYPE`  required
  *fqdn*               fully qualified host name string matching :obj:`.RX_FQDN`      required
  *is_primary*         this is primary resource  string matching :obj:`.RX_YES_NO`    required
  ==================== ========================= ==================================== ====================
  """
  def validate(self, apiobj, method, api, param, safe):
    """Validate request input data."""
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
    """Retrieve site resources. The results aren't ordered in any particular way.

    :returns: sequence of rows of site resources; field order in the returned
              *desc.columns*."""

    return self.api.query(None, None, """
      select s.name, r.type, r.fqdn, r.is_primary
      from site s
      join resource_element r on r.site = s.id
    """)

  @restcall
  def put(self, site, type, fqdn, is_primary):
    """Insert new site resources. Site admin can update their own site, global
    admin can update resources for all the sites. When more than one argument
    is given, there must be an equal number of arguments for all the parameters.
    For input validation requirements, see the field descriptions above. It is
    an error to attemp to insert an existing site resource.

    :arg list site: new values;
    :arg list type: new values;
    :arg list fqdn: new values;
    :arg list is_primary: new values;
    :returns: a list with a dict in which *modified* gives the number of objects
              inserted into the database, which is always *len(site).*"""

    return self.api.modify("""
      insert into resource_element (id, site, fqdn, type, is_primary)
      select resource_element_sq.nextval, s.id, :fqdn, :type, :is_primary
      from site s where s.name = :site
      """, site=site, type=type, fqdn=fqdn, is_primary=is_primary)

  @restcall
  def delete(self, site, type, fqdn):
    """Delete site resource associations. Site admin can update their own site,
    global admin can update resources for all the sites. When more than one
    argument is given, there must be an equal number of arguments for all the
    parameters. For input validation requirements, see the field descriptions
    above. It is an error to attempt to delete a non-existent site resource.

    :arg list site: values to delete;
    :arg list type: values to delete;
    :arg list fqdn: values to delete;
    :returns: a list with a dict in which *modified* gives the number of objects
              deleted from the database, which is always *len(site).*"""

    return self.api.modify("""
      delete from resource_element
      where site = (select s.id from site s where s.name = :site)
        and fqdn = :fqdn
        and type = :type
      """, site=site, type=type, fqdn=fqdn)

######################################################################
######################################################################
class SiteAssociations(RESTEntity):
  """REST entity for site relationships.

  ==================== ========================= ==================================== ====================
  Contents             Meaning                   Value                                Constraints
  ==================== ========================= ==================================== ====================
  *parent*             parent site name          string matching :obj:`.RX_SITE`      required
  *child*              child site name           string matching :obj:`.RX_SITE`      required
  ==================== ========================= ==================================== ====================
  """
  def validate(self, apiobj, method, api, param, safe):
    """Validate request input data."""

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
    """Retrieve site parent-child associations. The results aren't ordered
    in any particular way.

    :returns: sequence of rows of associations; field order in the returned
              *desc.columns*."""

    return self.api.query(None, None, """
      select p.name parent_site, c.name child_site
      from site_association sa
      join site p on p.id = sa.parent_site
      join site c on c.id = sa.child_site
    """)

  @restcall
  def put(self, parent, child):
    """Insert new site associations. Parent site admin can update their own
    site, global admin can update associations for all the sites. When more
    than one argument is given, there must be an equal number of arguments
    for all the parameters. For input validation requirements, see the field
    descriptions above. It is an error to attempt to insert an existing site
    association pair.

    :arg list parent: new values;
    :arg list child: new values;
    :returns: a list with a dict in which *modified* gives the number of objects
              inserted into the database, which is always *len(parent).*"""

    return self.api.modify("""
      insert into site_association (parent_site, child_site)
      values ((select id from site where name = :parent),
              (select id from site where name = :child))
      """, parent=parent, child=child)

  @restcall
  def delete(self, parent, child):
    """Delete site associations. Parent site admin can update their own site,
    global admin can update associations for all the sites. When more than one
    argument is given, there must be an equal number of arguments for all the
    parameters. For input validation requirements, see the field descriptions
    above. It is an error to attempt to delete a non-existent association.

    :arg list parent: values to delete;
    :arg list child: values to delete;
    :returns: a list with a dict in which *modified* gives the number of objects
              deleted from the database, which is always *len(parent).*"""

    return self.api.modify("""
      delete from site_association
      where parent_site = (select id from site where name = :parent)
        and child_site = (select id from site where name = :child)
      """, parent=parent, child=child)
