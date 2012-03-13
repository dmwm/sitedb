from SiteDB.RESTAuth import authz_match
import cherrypy

def oldsite_authz_match(api, sites, role=[], group=[], site=[], verbose=False):
  """Like authz_match, but translates site names from old to new via `api`.
  The caller must provide `sites`, an initially empty dictionary, used to
  cache site name translation lookups."""
  # Initialise cache if not yet done.
  if not sites:
    c, _ = api.execute("""select s.name site_name, c.name alias from site s
                          join site_cms_name_map cmap on cmap.site_id = s.id
                          join cms_name c on c.id = cmap.cms_name_id""")
    for old, canonical in c:
      if old not in sites:
        sites[old] = []
      sites[old].append(canonical)

  # Remap sites. Ignore sites which don't exist, rather than raising an error.
  # This is needed so that a global admin can perform the operations on site
  # objects even if cms name mapping is missing. This does not affect authz
  # decisions if someone other than global admin attempts an operation - one
  # cannot have privileges for a site that has no CMS name.
  remapped = sum((sites[s] for s in site if s in sites), [])

  # Now perform normal authz_match.
  return authz_match(role, group, remapped, verbose)
