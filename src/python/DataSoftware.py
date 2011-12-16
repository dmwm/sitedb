from SiteDB.RESTServer import RESTEntity, restcall, rows
from SiteDB.RESTAuth import authz_match
from SiteDB.RESTTools import tools
from SiteDB.RESTValidation import *
from SiteDB.Regexps import *

class Software(RESTEntity):
  """REST entity for site's pinned software releases.

  ==================== ========================= ==================================== ====================
  Contents             Meaning                   Value                                Constraints
  ==================== ========================= ==================================== ====================
  *site*               site name                 string matching :obj:`.RX_SITE`      required
  *ce*                 CE to pin on              string matching :obj:`.RX_FQDN`      required
  *release*            CMSSW release to pin      string matching :obj:`.RX_RELEASE`   required
  *arch*               architecture to pin on    string matching :obj:`.RX_ARCH`      required
  ==================== ========================= ==================================== ====================
  """
  def validate(self, apiobj, method, api, param, safe):
    """Validate request input data."""
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
    """Retrieve pinned software releases at sites. The results aren't ordered
    in any particular way.

    :returns: sequence of rows of pinned software releases; field order in
              the returned *desc.columns*."""

    return self.api.query(None, None, """
      select s.name site, r.fqdn ce, pr.release, pr.arch
      from site s
      join resource_element r on r.site = s.id
      join pinned_releases pr on pr.ce_id = r.id
      where r.type = 'CE'
    """)

  @restcall
  def put(self, site, ce, release, arch):
    """Add a software pin. Site admin can update their own site, global
    admin can update pins for all the sites. When more than on argument is
    given, there must be an equal number of arguments for all the parameters.
    For input validation requirements, see the field descriptions above. It
    is an error to attempt to insert an existing pin, or to pin software on
    a non-existent CE resource.

    :arg list site: new values;
    :arg list ce: new values;
    :arg list release: new values;
    :arg list arch: new values;
    :returns: a list with a dict in which *modified* gives the number of objects
              inserted into the database, which is always *len(site).*"""

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
    """Remove a software pin. Site admin can update their own site, global
    admin can update pins for all the sites. When more than one argument is
    given, there must be an equal number of arguments for all the parameters.
    For input validation requirements, see the field descriptions above. It
    is an error to attempt to remove a non-existent pin.

    :arg list site: values to delete;
    :arg list ce: values to delete;
    :arg list release: values to delete;
    :arg list arch: values to delete;
    :returns: a list with a dict in which *modified* gives the number of objects
              deleted from the database, which is always *len(site).*"""

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
