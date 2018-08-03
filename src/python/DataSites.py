from WMCore.REST.Server import RESTEntity, restcall, rows
from SiteDB.SiteAuth import oldsite_authz_match
from WMCore.REST.Auth import authz_match
from WMCore.REST.Tools import tools
from WMCore.REST.Validation import *
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
  *site_name*          site name                 string matching :obj:`.RX_SITE`      required, unique
  *tier_level*         tier level                integer >= 0                         required
  *tier*               tier label                string matching :obj:`.RX_TIER`      required
  *country*            country                   string matching :obj:`.RX_COUNTRY`   required
  *usage*              grid flavour              string matching :obj:`.RX_USAGE`     required
  *url*                site web page             string matching :obj:`.RX_URL`       required
  *logo_url*           logo image location       string matching :obj:`.RX_URL`       required
  *devel_release*      (unknown)                 string matching :obj:`.RX_YES_NO`    required
  *manual_install*     (unknown)                 string matching :obj:`.RX_YES_NO`    required
  ==================== ========================= ==================================== ====================
  """
  def validate(self, apiobj, method, api, param, safe):
    """Validate request input data."""
    if method in ('GET', 'HEAD'):
      validate_rx('match', param, safe, optional = True)

    elif method in ('PUT', 'POST'):
      validate_strlist('site_name', param, safe, RX_SITE)
      validate_strlist('tier', param, safe, RX_TIER)
      validate_ustrlist('country', param, safe, RX_COUNTRY)
      validate_strlist('usage', param, safe, RX_USAGE)
      validate_strlist('url', param, safe, RX_URL)
      validate_strlist('logo_url', param, safe, RX_URL)
      validate_strlist('devel_release', param, safe, RX_YES_NO)
      validate_strlist('manual_install', param, safe, RX_YES_NO)
      validate_lengths(safe, 'site_name', 'tier', 'country', 'usage',
                       'url', 'logo_url', 'devel_release', 'manual_install')
      if method == 'PUT':
        validate_strlist('executive', param, safe, RX_USER)
        validate_lengths(safe, 'executive')

    elif method == 'DELETE':
      validate_strlist('site_name', param, safe, RX_SITE)

    # Delay POST authz until we have database connection for name remapping.
    if method in ('PUT'):
      authz_match(role=["Global Admin", "Operator"], group=["global","SiteDB"])
    elif method in ('DELETE'):
      authz_match(role=["Global Admin"], group=["global"])

  def _authz(self, sites):
    """Run late authorisation, remapping site names to canonical ones."""
    remap = {}
    for site in sites:
      oldsite_authz_match(self.api, remap,
                          role=["Global Admin", "Operator", "Site Executive", "Site Admin"],
                          group=["global","SiteDB"], site=[site])

  @restcall
  @tools.expires(secs=300)
  def get(self, match):
    """Retrieve sites. The results aren't ordered in any particular way.

    :arg str match: optional regular expression to filter by *name*
    :returns: sequence of rows of sites; field order in the returned
              *desc.columns*."""
    return self.api.query(match, itemgetter(0), """
      select s.id, s.name site_name, t.pos tier_level, t.name tier,
             to_nchar(s.country) country,
             s.usage, s.url, s.logourl logo_url,
             s.getdevlrelease devel_release, s.manualinstall manual_install
      from site s
      join tier t on t.id = s.tier
      """)

  @restcall
  def post(self, site_name, tier, country, usage, url, logo_url,
           devel_release, manual_install):
    """Update the information for sites identified by `site_name`. A site
    executive/admin can update their own site's record, operators and global
    admins the info for all the sites. When more than one argument is given,
    there must be equal number of arguments for all the parameters.  It is
    an error to attempt to update a non-existent `site`.

    :arg list site_name: site names to insert;
    :arg list tier: new values;
    :arg list country: new values;
    :arg list usage: new values;
    :arg list url: new values;
    :arg list logo_url: new values;
    :arg list devel_release: new values;
    :arg list manual_install: new values;
    :returns: a list with a dict in which *modified* gives number of objects
              updated in the database, which is always *len(site_name).*"""
    self._authz(site_name)
    return self.api.modify("""
      update site set
        tier = (select id from tier where name = :tier),
        country = :country,
        usage = :usage,
        url = :url,
        logourl = :logo_url,
        getdevlrelease = :devel_release,
        manualinstall = :manual_install
      where name = :site_name
      """, site_name = site_name, tier = tier, country = country,
      usage = usage, url = url, logo_url = logo_url,
      devel_release = devel_release, manual_install = manual_install)

  @restcall
  def put(self, site_name, tier, country, usage, url, logo_url,
          devel_release, manual_install, executive):
    """Insert new sites. The caller needs to have global admin privileges
    or be an operator.
    When more than one argument is given, there must equal number of
    arguments for all the parameters. For input validation requirements,
    see the field descriptions above.  It is an error to attempt to insert
    a `site_name` which already exists.

    :arg list site_name: site names to insert;
    :arg list tier: new values;
    :arg list country: new values;
    :arg list usage: new values;
    :arg list url: new values;
    :arg list logo_url: new values;
    :arg list devel_release: new values;
    :arg list manual_install: new values;
    :arg list executive: username of site executives;
    :returns: a list with a dict in which *modified* gives number of objects
              inserted into the database, which is always *len(site_name).*"""

    r = self.api.modify("""
      insert into site
      (id, name, tier, country, usage, url, logourl, getdevlrelease, manualinstall)
      values (site_sq.nextval, :site_name, (select id from tier where name = :tier),
              :country, :usage, :url, :logo_url, :devel_release, :manual_install)
      """, site_name = site_name, tier = tier, country = country,
      usage = usage, url = url, logo_url = logo_url,
      devel_release = devel_release, manual_install = manual_install)

    self.api.modify("""
      insert into site_responsibility (contact, role, site)
      values ((select id from contact where username = :username),
              (select id from role where title = 'Site Executive'),
              (select id from site where name = :site_name))
      """, username = executive, site_name = site_name)
    return r

  @restcall
  def delete(self, site_name):
    """Delete site records. Only a global admin can delete site records.
    For input validation requirements, see the field descriptions above.
    It is an error to attempt to delete a non-existent `site_name`.

    :arg list site_name: names of sites to delete.
    :returns: a list with a dict in which *modified* gives number of objects
              deleted from the database, which is always *len(site_name).*"""
    return self.api.modify("""
      delete from site where name = :site_name
      """, site_name = site_name)

######################################################################
######################################################################
class SiteNames(RESTEntity):
  """REST entity for site name aliases.

  ==================== ========================= ==================================== ====================
  Contents             Meaning                   Value                                Constraints
  ==================== ========================= ==================================== ====================
  *type*               alias type                string matching :obj:`.RX_NAME_TYPE` required, unique
  *site_name*          site name                 string matching :obj:`.RX_SITE`      required, unique
  *alias*              name alias                string matching :obj:`.RX_NAME`      required, unique
  ==================== ========================= ==================================== ====================
  """
  def validate(self, apiobj, method, api, param, safe):
    """Validate request input data."""

    if method in ('GET', 'HEAD'):
      validate_rx('match', param, safe, optional = True)

    elif method in ('PUT', 'DELETE'):
      validate_strlist('type', param, safe, RX_NAME_TYPE)
      validate_strlist('site_name', param, safe, RX_SITE)
      validate_strlist('alias', param, safe, RX_NAME)
      validate_lengths(safe, 'type', 'site_name', 'alias')
      authz_match(role=["Global Admin", "Operator"], group=["global","SiteDB"])

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
      union
      (select 'psn' type, s.name site_name, p.name alias
       from site s
       join psn_node p on p.site = s.id)
      """)

  @restcall
  def put(self, type, site_name, alias):
    """Insert new site names. Only global admins and SiteDB operators can
    update names for the sites. When more than one argument is
    given, there must be an equal number of arguments for all the parameters.
    For input validation requirements, see the field descriptions above.
    It is an error to attempt to insert an existing name alias triplet.

    :arg list type: new values;
    :arg list site_name: new values;
    :arg list alias: new values;
    :returns: a list with a dict in which *modified* gives the number of objects
              inserted into the database, which is always *len(type).*"""

    binds = self.api.bindmap(type = type, site_name = site_name, alias = alias)
    lcg = filter(lambda b: b['type'] == 'lcg', binds)
    cms = filter(lambda b: b['type'] == 'cms', binds)
    phedex = filter(lambda b: b['type'] == 'phedex', binds)
    psn = filter(lambda b: b['type'] == 'psn', binds)
    for b in binds: del b['type']
    updated = 0

    if cms:
      c, _ = self.api.executemany("""
        insert all
        into cms_name (id, name) values (cms_name_sq.nextval, alias)
        into site_cms_name_map (site_id, cms_name_id) values (site_id, cms_name_sq.nextval)
        select s.id site_id, :alias alias
        from site s where s.name = :site_name
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
        where s.name = :site_name
        """, lcg)
      self.api.rowstatus(c, 2*len(lcg))
      updated += c.rowcount / 2

    if phedex:
      c, _ = self.api.executemany("""
        insert into phedex_node (id, site, name)
        select phedex_node_sq.nextval, s.id, :alias
        from site s where s.name = :site_name
        """, phedex)
      self.api.rowstatus(c, len(phedex))
      updated += c.rowcount

    if psn:
      c, _ = self.api.executemany("""
        insert into psn_node (id, site, name)
        select psn_node_sq.nextval, s.id, :alias
        from site s where s.name = :site_name
        """, psn)
      self.api.rowstatus(c, len(psn))
      updated += c.rowcount

    result = rows([{ "modified": updated }])
    trace = request.db["handle"]["trace"]
    trace and cherrypy.log("%s commit" % trace)
    request.db["handle"]["connection"].commit()
    return result

  @restcall
  def delete(self, type, site_name, alias):
    """Delete site name associations. Only Global admins and SiteDB operators,
    can delete names for the sites. When more than one
    argument is given, there must be an equal number of arguments for all
    the parameters. For input validation requirements, see the field
    descriptions above. It is an error to attempt to delete a non-existent
    site name association.

    :arg list type: values to delete;
    :arg list site_name: values to delete;
    :arg list alias: values to delete;
    :returns: a list with a dict in which *modified* gives the number of objects
              deleted from the database, which is always *len(type).*"""

    binds = self.api.bindmap(type = type, site_name = site_name, alias = alias)
    lcg = filter(lambda b: b['type'] == 'lcg', binds)
    cms = filter(lambda b: b['type'] == 'cms', binds)
    phedex = filter(lambda b: b['type'] == 'phedex', binds)
    psn = filter(lambda b: b['type'] == 'psn', binds)
    for b in binds: del b['type']
    updated = 0

    if cms:
      c, _ = self.api.executemany("""
        delete from cms_name
        where id in (select cmap.cms_name_id
                     from site s
                     join site_cms_name_map cmap on cmap.site_id = s.id
                     where s.name = :site_name)
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
                     where s.name = :site_name)
           and name = :alias
        """, lcg)
      self.api.rowstatus(c, len(lcg))
      updated += c.rowcount

    if phedex:
      c, _ = self.api.executemany("""
        delete from phedex_node
        where site = (select s.id from site s where s.name = :site_name)
          and name = :alias
        """, phedex)
      self.api.rowstatus(c, len(phedex))
      updated += c.rowcount

    if psn:
      c, _ = self.api.executemany("""
        delete from psn_node
        where site = (select s.id from site s where s.name = :site_name)
          and name = :alias
        """, psn)
      self.api.rowstatus(c, len(psn))
      updated += c.rowcount

    result = rows([{ "modified": updated }])
    trace = request.db["handle"]["trace"]
    trace and cherrypy.log("%s commit" % trace)
    request.db["handle"]["connection"].commit()
    return result

######################################################################
######################################################################
class SiteResources(RESTEntity):
  """REST entity for site SE,gsiftp,xrootd,perfSONAR resources.

  ==================== ========================= ==================================== ====================
  Contents             Meaning                   Value                                Constraints
  ==================== ========================= ==================================== ====================
  *site_name*          site name                 string matching :obj:`.RX_SITE`      required, unique
  *type*               resource type             string matching :obj:`.RX_RES_TYPE`  required
  *fqdn*               fully qualified host name string matching :obj:`.RX_FQDN`      required
  *is_primary*         this is primary resource  string matching :obj:`.RX_YES_NO`    required
  ==================== ========================= ==================================== ====================
  """
  def validate(self, apiobj, method, api, param, safe):
    """Validate request input data."""
    if method in ('PUT', 'DELETE'):
      validate_strlist('site_name', param, safe, RX_SITE)
      validate_strlist('type', param, safe, RX_RES_TYPE)
      validate_strlist('fqdn', param, safe, RX_FQDN)
      validate_strlist('is_primary', param, safe, RX_YES_NO)
      validate_lengths(safe, 'site_name', 'type', 'fqdn', 'is_primary')

    # Delay authz until we have database connection for name remapping.

  def _authz(self, sites):
    """Run late authorisation, remapping site names to canonical ones."""
    remap = {}
    for site in sites:
      oldsite_authz_match(self.api, remap,
                          role=["Global Admin", "Site Executive", "Site Admin", "Operator"],
                          group=["global", "SiteDB"], site=[site])

  @restcall
  @tools.expires(secs=300)
  def get(self):
    """Retrieve site resources. The results aren't ordered in any particular way.

    :returns: sequence of rows of site resources; field order in the returned
              *desc.columns*."""

    return self.api.query(None, None, """
      select s.name site_name, r.type, r.fqdn, r.is_primary
      from site s
      join resource_element r on r.site = s.id where r.type IN ('SE', 'gsiftp', 'xrootd','perfSONAR')
    """)

  @restcall
  def put(self, site_name, type, fqdn, is_primary):
    """Insert new site resources. Site executive / admin can update their own
    site, global admin / operator can update resources for all the sites. When more than
    one argument is given, there must be an equal number of arguments for all
    the parameters. For input validation requirements, see the field
    descriptions above. It is an error to attemp to insert an existing site
    resource.

    :arg list site_name: new values;
    :arg list type: new values;
    :arg list fqdn: new values;
    :arg list is_primary: new values;
    :returns: a list with a dict in which *modified* gives the number of objects
              inserted into the database, which is always *len(site_name).*"""

    self._authz(site_name)

    # Update both the new and the old table to be compatible with v1.
    # The old one could be withdraw once v1 gets fully deprecated.
    binds = self.api.bindmap(site_name = site_name, type = type,
                             fqdn = fqdn, is_primary = is_primary)
    c, _ = self.api.executemany("""
      insert all
      into resource_element (id, site, fqdn, type, is_primary)
        values (resource_element_sq.nextval, site_id, :fqdn, :type, :is_primary)
      into resource_cms_name_map (resource_id, cms_name_id)
        values (resource_element_sq.nextval, cms_name_id)
      select s.id site_id, ss.cms_name_id cms_name_id
        from site s join site_cms_name_map ss on s.id = ss.site_id
        where s.name = :site_name
      """, binds)
    self.api.rowstatus(c, 2*len(binds))

    result = rows([{ "modified": c.rowcount / 2 }])
    trace = request.db["handle"]["trace"]
    trace and cherrypy.log("%s commit" % trace)
    request.db["handle"]["connection"].commit()
    return result

  @restcall
  def delete(self, site_name, type, fqdn, is_primary):
    """Delete site resource associations. Site executive / admin can update
    their own site, global admin / operator can update resources for all the
    sites. When more than one argument is given, there must be an equal number
    of arguments for all the parameters. For input validation requirements,
    see the field descriptions above. It is an error to attempt to delete
    a non-existent site resource.

    :arg list site_name: values to delete;
    :arg list type: values to delete;
    :arg list fqdn: values to delete;
    :arg list is_primary: value to delete;
    :returns: a list with a dict in which *modified* gives the number of objects
              deleted from the database, which is always *len(site_name).*"""

    self._authz(site_name)
    return self.api.modify("""
      delete from resource_element
      where site = (select s.id from site s where s.name = :site_name)
        and fqdn = :fqdn
        and type = :type
        and is_primary = :is_primary
        and rownum=1
      """, site_name=site_name, type=type, fqdn=fqdn, is_primary=is_primary)

######################################################################
######################################################################
class SiteAssociations(RESTEntity):
  """REST entity for site relationships.

  ==================== ========================= ==================================== ====================
  Contents             Meaning                   Value                                Constraints
  ==================== ========================= ==================================== ====================
  *parent_site*        parent site name          string matching :obj:`.RX_SITE`      required
  *child_site*         child site name           string matching :obj:`.RX_SITE`      required
  ==================== ========================= ==================================== ====================
  """
  def validate(self, apiobj, method, api, param, safe):
    """Validate request input data."""

    if method in ('PUT', 'DELETE'):
      validate_strlist('parent_site', param, safe, RX_SITE)
      validate_strlist('child_site',  param, safe, RX_SITE)
      validate_lengths(safe, 'parent_site', 'child_site')
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
  def put(self, parent_site, child_site):
    """Insert new site associations. Parent site executive can update their own
    site, global admin can update associations for all the sites. The parent
    site must be a higher tier level than the child: the children of a Tier-1
    site must be Tier-2 or lesser sites. When more than one argument is given,
    there must be an equal number of arguments for all the parameters. For
    input validation requirements, see the field descriptions above. It is an
    error to attempt to insert an existing site association pair.

    :arg list parent_site: new values;
    :arg list child_site: new values;
    :returns: a list with a dict in which *modified* gives the number of objects
              inserted into the database, which is always *len(parent_site).*"""

    self._authz(parent_site)
    return self.api.modify("""
      insert into site_association (parent_site, child_site)
      select p.id, c.id from site p, site c, tier pt, tier ct
      where p.name = :parent_site and pt.id = p.tier
        and c.name = :child_site and ct.id = c.tier
        and ct.pos > pt.pos
      """, parent_site=parent_site, child_site=child_site)

  @restcall
  def delete(self, parent_site, child_site):
    """Delete site associations. Parent site executive can update their own site,
    global admin can update associations for all the sites. When more than one
    argument is given, there must be an equal number of arguments for all the
    parameters. For input validation requirements, see the field descriptions
    above. It is an error to attempt to delete a non-existent association.

    :arg list parent_site: values to delete;
    :arg list child_site: values to delete;
    :returns: a list with a dict in which *modified* gives the number of objects
              deleted from the database, which is always *len(parent_site).*"""

    self._authz(parent_site)
    return self.api.modify("""
      delete from site_association
      where parent_site = (select id from site where name = :parent_site)
        and child_site = (select id from site where name = :child_site)
      """, parent_site=parent_site, child_site=child_site)
